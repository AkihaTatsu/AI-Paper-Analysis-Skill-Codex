"""Shared, versioned tool environments for installed Skills and the wheel CLI."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .capabilities import capability_closure, list_tools

RUNTIME_API_VERSION = "1"
RENDERER_API_VERSION = "1"
LOCK_TIMEOUT_SECONDS = 300
STALE_LOCK_SECONDS = 900


class ToolBootstrapError(RuntimeError):
    """Raised when a shared tool environment cannot be prepared safely."""


def cache_root() -> Path:
    """Return the cross-platform cache root, with one explicit override."""

    if configured := os.environ.get("APA_CACHE_DIR"):
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return (base / "ai-paper-analysis").resolve()


@contextmanager
def _directory_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    while True:
        try:
            path.mkdir()
            break
        except FileExistsError:
            try:
                stale = time.time() - path.stat().st_mtime > STALE_LOCK_SECONDS
            except FileNotFoundError:
                continue
            if stale:
                shutil.rmtree(path, ignore_errors=True)
                continue
            if time.monotonic() >= deadline:
                raise ToolBootstrapError(
                    f"Timed out waiting for shared tool lock: {path}"
                ) from None
            time.sleep(0.1)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _run(command: list[str], *, environment: dict[str, str]) -> None:
    process = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        timeout=900,
    )
    if process.returncode:
        detail = " ".join((process.stderr or process.stdout).split())[:1000]
        raise ToolBootstrapError(detail or f"Tool command failed: {command[0]}")


def _capture(command: list[str], *, environment: dict[str, str] | None = None) -> str:
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, env=environment, timeout=180
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ToolBootstrapError(str(error)) from error
    if result.returncode:
        raise ToolBootstrapError(" ".join((result.stderr or result.stdout).split())[-1500:])
    return result.stdout.strip()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def _manifest_matches(path: Path, *, kind: str, api_version: str) -> bool:
    try:
        payload = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False
    return bool(payload == {"kind": kind, "api_version": api_version})


def _write_manifest(path: Path, *, kind: str, api_version: str) -> None:
    (path / "manifest.json").write_text(
        json.dumps({"kind": kind, "api_version": api_version}, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _prune_versions(parent: Path, current: Path) -> None:
    versions = sorted(
        (
            path
            for path in parent.glob("v*")
            if path.is_dir() and (path / "manifest.json").is_file()
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    ordered = [current, *(path for path in versions if path != current)]
    keep = set(ordered[:2])
    for obsolete in versions:
        if obsolete not in keep:
            shutil.rmtree(obsolete)


def _environment_python(environment: Path) -> Path:
    candidate = (
        environment / "Scripts" / "python.exe"
        if os.name == "nt"
        else environment / "bin" / "python"
    )
    if not candidate.is_file():
        raise ToolBootstrapError(f"Shared Python environment is incomplete: {candidate}")
    return candidate


def prepare_skill_runtime(skill_root: Path) -> Path:
    """Create or reuse the suite-wide locked Python environment."""

    parent = cache_root() / "runtime"
    destination = parent / f"v{RUNTIME_API_VERSION}"
    if _manifest_matches(destination, kind="runtime", api_version=RUNTIME_API_VERSION):
        return _environment_python(destination / "environment")
    uv = shutil.which("uv")
    if uv is None:
        raise ToolBootstrapError("uv is required to initialize the shared Skill runtime")
    with _directory_lock(parent / ".bootstrap.lock"):
        if not _manifest_matches(destination, kind="runtime", api_version=RUNTIME_API_VERSION):
            parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".runtime-", dir=parent))
            try:
                environment_path = temporary / "environment"
                environment = os.environ.copy()
                environment["UV_PROJECT_ENVIRONMENT"] = str(environment_path)
                _run(
                    [
                        uv,
                        "sync",
                        "--project",
                        str(skill_root),
                        "--frozen",
                        "--no-extra",
                        "ocr",
                        "--quiet",
                    ],
                    environment=environment,
                )
                _write_manifest(temporary, kind="runtime", api_version=RUNTIME_API_VERSION)
                if destination.exists():
                    shutil.rmtree(destination)
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
            _prune_versions(parent, destination)
    return _environment_python(destination / "environment")


def renderer_source() -> Path:
    """Locate the locked renderer material in a Skill, wheel, or checkout."""

    if configured := os.environ.get("APA_RENDERER_SOURCE"):
        source = Path(configured).resolve()
        if (source / "package-lock.json").is_file():
            return source
    module = Path(__file__).resolve()
    candidates = [module.parent / "_data" / "renderer"]
    for ancestor in module.parents:
        candidates.extend(
            (
                ancestor / "references" / "renderer",
                ancestor,
            )
        )
    for candidate in candidates:
        if (candidate / "package-lock.json").is_file() and (
            candidate / "scripts" / "render_report.mjs"
        ).is_file():
            return candidate
    raise ToolBootstrapError("Could not locate the locked report-renderer resources")


def _system_browser() -> str | None:
    if (configured := os.environ.get("PUPPETEER_EXECUTABLE_PATH")) and Path(configured).is_file():
        return configured
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        if executable := shutil.which(name):
            return executable
    for candidate in (
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def _copy_renderer_source(source: Path, destination: Path) -> None:
    for name in ("package.json", "package-lock.json", ".markdownlint-cli2.yaml"):
        shutil.copy2(source / name, destination / name)
    scripts = destination / "scripts"
    scripts.mkdir()
    for name in ("check_mermaid.mjs", "render_report.mjs"):
        shutil.copy2(source / "scripts" / name, scripts / name)


def _refresh_renderer_program(source: Path, destination: Path) -> None:
    """Refresh compatible scripts and lint configuration without reinstalling tools."""

    relative_paths = (
        Path(".markdownlint-cli2.yaml"),
        Path("scripts/check_mermaid.mjs"),
        Path("scripts/render_report.mjs"),
    )
    for relative in relative_paths:
        origin = source / relative
        target = destination / relative
        if target.is_file() and origin.read_bytes() == target.read_bytes():
            continue
        temporary = target.with_name(f".{target.name}.{os.getpid()}.updating")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def _require_node() -> str:
    node = shutil.which("node")
    if node is None:
        raise ToolBootstrapError("Node.js >=22.12 is required for report tools")
    raw = _capture([node, "--version"]).lstrip("v")
    try:
        version = tuple(int(part) for part in raw.split(".")[:2])
    except ValueError as error:
        raise ToolBootstrapError(f"Could not parse Node.js version: {raw}") from error
    if version < (22, 12):
        raise ToolBootstrapError(f"Node.js >=22.12 is required; found {raw}")
    return node


def _npm_command(*arguments: str) -> list[str]:
    npm = shutil.which("npm")
    if npm is None:
        raise ToolBootstrapError("npm is required to initialize report tools")
    if Path(npm).suffix.lower() == ".cmd":
        cli = Path(npm).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
        if cli.is_file():
            return [_require_node(), str(cli), *arguments]
    return [npm, *arguments]


def _linked_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)
    return destination


def _browser_executable(renderer: Path, environment: dict[str, str]) -> str:
    # Let Puppeteer resolve its pinned browser's platform-specific installation path.
    script = (
        "const p = require(process.argv[1]);"
        "process.stdout.write(p.executablePath({headless:'shell'}));"
    )
    executable = _capture(
        [_require_node(), "-e", script, str(renderer / "node_modules" / "puppeteer")],
        environment=environment,
    )
    if not Path(executable).is_file():
        raise ToolBootstrapError(f"Report browser is incomplete: {executable}")
    return executable


def _renderer_dependencies_ready(root: Path) -> bool:
    if not (root / "node_modules").is_dir():
        return False
    locked = _read_json(root / "package-lock.json").get("packages", {})
    for name, package in locked.items():
        if not name or package.get("link") or not package.get("version"):
            continue
        if _read_json(root / name / "package.json").get("version") != package["version"]:
            return False
    return True


def prepare_renderer(
    source: Path | None = None,
    *,
    require_browser: bool = True,
    cache_dir: Path | None = None,
) -> dict[str, str]:
    """Prepare immutable renderer programs and shared, locked Node dependencies."""

    source = (source or renderer_source()).resolve()
    _require_node()
    root = (cache_dir or cache_root()) / "renderer"
    dependency_id = hashlib.sha256((source / "package-lock.json").read_bytes()).hexdigest()[:20]
    names = (
        "package.json",
        "package-lock.json",
        ".markdownlint-cli2.yaml",
        "scripts/check_mermaid.mjs",
        "scripts/render_report.mjs",
    )
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode())
        digest.update((source / name).read_bytes())
    dependency_root = root / "dependencies" / dependency_id
    destination = root / "programs" / digest.hexdigest()[:20]
    environment = os.environ.copy()
    browser_cache = root / "browsers" / dependency_id
    environment["PUPPETEER_CACHE_DIR"] = str(browser_cache)
    with _directory_lock(root / ".bootstrap.lock"):
        if not (dependency_root / "manifest.json").is_file() or not _renderer_dependencies_ready(
            dependency_root
        ):
            dependency_root.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".dependencies-", dir=dependency_root.parent))
            try:
                for name in ("package.json", "package-lock.json"):
                    shutil.copy2(source / name, temporary / name)
                _run(
                    _npm_command(
                        "ci", "--ignore-scripts", "--include=dev", "--prefix", str(temporary)
                    ),
                    environment=environment,
                )
                _write_json(temporary / "manifest.json", {"dependency_id": dependency_id})
                if dependency_root.exists():
                    shutil.rmtree(dependency_root)
                os.replace(temporary, dependency_root)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        if not (destination / "manifest.json").is_file() or not _renderer_dependencies_ready(
            destination
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".program-", dir=destination.parent))
            try:
                _copy_renderer_source(source, temporary)
                if (dependency_root / "node_modules").is_dir():
                    shutil.copytree(
                        dependency_root / "node_modules",
                        temporary / "node_modules",
                        symlinks=True,
                        copy_function=_linked_copy,
                    )
                _write_json(temporary / "manifest.json", {"dependency_id": dependency_id})
                if destination.exists():
                    shutil.rmtree(destination)
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        _refresh_renderer_program(source, destination)
    browser = _system_browser()
    if require_browser and browser is None:
        with _directory_lock(root / ".browser.lock"):
            try:
                browser = _browser_executable(destination, environment)
            except ToolBootstrapError:
                _run(
                    _npm_command(
                        "exec",
                        "--prefix",
                        str(dependency_root),
                        "--",
                        "puppeteer",
                        "browsers",
                        "install",
                        "chrome-headless-shell",
                    ),
                    environment=environment,
                )
                browser = _browser_executable(destination, environment)
    updates = {
        "APA_RENDERER_ROOT": str(destination),
        "PUPPETEER_CACHE_DIR": str(browser_cache),
    }
    if browser is not None:
        updates["PUPPETEER_EXECUTABLE_PATH"] = str(Path(browser).resolve())
    return updates


def reexecute_skill(
    *,
    skill_root: Path,
    entrypoint: Path,
    skill_name: str,
    commands: tuple[str, ...],
    renderer_commands: tuple[str, ...],
) -> None:
    """Bootstrap shared tools and re-execute one capability-scoped Skill CLI."""

    python = prepare_skill_runtime(skill_root)
    environment = os.environ.copy()
    environment.update(
        {
            "APA_BOOTSTRAPPED": "1",
            "APA_CONTRACTS_DIR": str(skill_root / "references" / "contracts"),
            "APA_SKILL_COMMANDS": ",".join(commands),
            "APA_SKILL_NAME": skill_name,
            "APA_PYTHON": str(python),
        }
    )
    requested = sys.argv[1] if len(sys.argv) > 1 else ""
    if requested in renderer_commands:
        environment["APA_RENDERER_SOURCE"] = str(skill_root / "references" / "renderer")
        environment.update(
            prepare_renderer(
                skill_root / "references" / "renderer",
                require_browser=requested != "fix-mermaid-direction",
            )
        )
    executable_directory = python.parent
    environment["PATH"] = os.pathsep.join((str(executable_directory), environment.get("PATH", "")))
    os.execve(
        python,
        [str(python), str(entrypoint), *sys.argv[1:]],
        environment,
    )


def source_root() -> Path:
    """Locate a checkout or the immutable shared source bundle."""

    if configured := os.environ.get("APA_CODE_ROOT"):
        candidate = Path(configured).resolve()
        if (candidate / "uv.lock").is_file():
            return candidate
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "uv.lock").is_file() and (candidate / "src" / "ai_paper_analysis").is_dir():
            return candidate
    raise ToolBootstrapError("Run the repository installer to prepare the shared CLI source bundle")


def _source_files(source: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for name in ("src/ai_paper_analysis", "contracts", "templates", "roles"):
        base = source / name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                files[path.relative_to(source).as_posix()] = path
    for name in ("pyproject.toml", "uv.lock", "VERSION", "README.md", "LICENSE"):
        if (source / name).is_file():
            files[name] = source / name
    renderer = source / "renderer" if (source / "renderer").is_dir() else source
    for name in (
        "package.json",
        "package-lock.json",
        ".markdownlint-cli2.yaml",
        "scripts/check_mermaid.mjs",
        "scripts/render_report.mjs",
    ):
        if (renderer / name).is_file():
            files[f"renderer/{name}"] = renderer / name
    return files


def _deploy_code(source: Path, cache: Path) -> Path:
    files = _source_files(source)
    digest = hashlib.sha256()
    hashes: dict[str, str] = {}
    for name, path in sorted(files.items()):
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(name.encode())
        digest.update(hashes[name].encode())
    destination = cache / "code" / digest.hexdigest()[:24]
    existing = _read_json(destination / "manifest.json").get("files", {})
    if existing and all(
        (destination / name).is_file()
        and hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected
        for name, expected in existing.items()
    ):
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".code-", dir=destination.parent))
    try:
        for name, path in files.items():
            target = temporary / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        entrypoint = temporary / "apa.py"
        entrypoint.write_text(
            '"""Shared CLI entrypoint; contains no Skill-specific dispatch."""\n'
            "import os\nimport sys\nfrom pathlib import Path\n"
            "root = Path(__file__).resolve().parent\n"
            'sys.path.insert(0, str(root / "src"))\n'
            'os.environ.setdefault("APA_CODE_ROOT", str(root))\n'
            'os.environ.pop("APA_SKILL_COMMANDS", None)\n'
            "from ai_paper_analysis.cli import app\napp()\n",
            encoding="utf-8",
        )
        hashes["apa.py"] = hashlib.sha256(entrypoint.read_bytes()).hexdigest()
        _write_json(temporary / "manifest.json", {"files": hashes})
        if destination.exists():
            # Repair only damaged files of this same content version. Other code
            # versions and healthy files remain available to running processes.
            for origin in sorted(temporary.rglob("*")):
                if not origin.is_file():
                    continue
                target = destination / origin.relative_to(temporary)
                if target.is_file() and target.read_bytes() == origin.read_bytes():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(origin, target)
        else:
            os.replace(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return destination


def _runtime_environment(record: dict[str, Any]) -> dict[str, str]:
    code = Path(record["code_root"])
    python = Path(record["python"])
    updates = {
        "APA_CACHE_DIR": str(record["cache_dir"]),
        "APA_CODE_ROOT": str(code),
        "APA_CONTRACTS_DIR": str(code / "contracts"),
        "APA_ROLES_DIR": str(code / "roles"),
        "APA_RENDERER_SOURCE": str(code / "renderer"),
        "APA_PYTHON": str(python),
        "APA_BOOTSTRAPPED": "1",
        "APA_TOOL_VERSIONS": json.dumps(record.get("versions", {}), sort_keys=True),
        "PYTHONPATH": str(code / "src"),
        "PATH": os.pathsep.join((str(python.parent), os.environ.get("PATH", ""))),
    }
    updates.update(record.get("renderer_environment", {}))
    return updates


def _doctor_record(record: dict[str, Any], requested: tuple[str, ...]) -> dict[str, Any]:
    errors: list[str] = []
    versions = dict(record.get("versions", {}))
    code = Path(record.get("code_root", ""))
    python = Path(record.get("python", ""))
    if not python.is_file():
        errors.append(f"Shared Python is missing: {python}")
    hashes = _read_json(code / "manifest.json").get("files", {})
    if not hashes:
        errors.append(f"Shared code manifest is missing: {code}")
    for name, expected in hashes.items():
        target = code / name
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            errors.append(f"Shared code resource is missing or modified: {target}")
    absent = set(requested) - set(record.get("capabilities", []))
    errors.extend(f"Capability is not installed: {name}" for name in sorted(absent))
    if not errors:
        registry = list_tools(source_root=code)
        modules = sorted(
            {module for name in requested for module in registry["capabilities"][name]["imports"]}
        )
        environment = os.environ.copy()
        environment.update(_runtime_environment(record))
        environment.pop("APA_SKILL_COMMANDS", None)
        try:
            versions["python"] = _capture([str(python), "--version"], environment=environment)
            _capture(
                [
                    str(python),
                    "-c",
                    "import importlib,sys; [importlib.import_module(n) for n in sys.argv[1:]]",
                    *modules,
                ],
                environment=environment,
            )
            if any(registry["capabilities"][name].get("renderer") for name in requested):
                _require_node()
                versions["node"] = _capture([_require_node(), "--version"])
                browser = environment.get("PUPPETEER_EXECUTABLE_PATH", "")
                if not browser or not Path(browser).is_file():
                    raise ToolBootstrapError("The configured report browser is missing")
                versions["browser"] = _capture([browser, "--version"], environment=environment)
                renderer = Path(environment["APA_RENDERER_ROOT"])
                script = renderer / "scripts" / "check_mermaid.mjs"
                if not script.is_file() or not (renderer / "node_modules").is_dir():
                    raise ToolBootstrapError("The shared report renderer is incomplete")
                # Importing the official parser checks Node modules without producing artifacts.
                _capture(
                    [
                        _require_node(),
                        "--input-type=module",
                        "-e",
                        f"await import({json.dumps(script.as_uri())})",
                    ],
                    environment=environment,
                )
        except (ToolBootstrapError, KeyError) as error:
            errors.append(str(error))
    return {
        **record,
        "valid": not errors,
        "capabilities": list(requested),
        "errors": errors,
        "versions": versions,
    }


def doctor_tools(
    capabilities: Iterable[str] | None = None, *, cache_dir: Path | None = None
) -> dict[str, Any]:
    """Check installed capabilities and resources without installing or upgrading them."""

    cache = (cache_dir or cache_root()).expanduser().resolve()
    record = _read_json(cache / "active.json")
    if not record:
        return {
            "valid": False,
            "capabilities": [],
            "errors": [f"Tools are not installed in {cache}"],
        }
    try:
        registry = list_tools(source_root=Path(record["code_root"]))
    except (OSError, ValueError, KeyError) as error:
        return {**record, "valid": False, "errors": [str(error)]}
    requested = capability_closure(
        capabilities if capabilities is not None else record["capabilities"], registry=registry
    )
    return _doctor_record(record, requested)


def _render_probe(record: dict[str, Any]) -> None:
    """Verify the complete newly prepared report toolchain using disposable content."""

    environment = os.environ.copy()
    environment.update(_runtime_environment(record))
    renderer = Path(environment["APA_RENDERER_ROOT"]) / "scripts" / "render_report.mjs"
    with tempfile.TemporaryDirectory(prefix="apa-tool-check-") as temporary:
        report = Path(temporary) / "check.md"
        report.write_text(
            "# Tool check\n\nA formula $x^2$.\n\n$$\nx^2 = 1\n$$\n\n"
            "```mermaid\nflowchart TB\nA --> B\n```\n",
            encoding="utf-8",
        )
        payload = json.loads(
            _capture([_require_node(), str(renderer), str(report)], environment=environment)
        )
        if payload.get("valid") is not True:
            raise ToolBootstrapError("The report renderer did not pass its installation self-check")


def ensure_tools(
    capabilities: Iterable[str],
    *,
    source_root: Path | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Install only missing compatible capabilities, then verify the complete union.

    Source and dependency versions are immutable and retained. Adding a capability
    uses pinned requirements with an additive install, so it cannot uninstall a
    dependency used by a previously installed Skill.
    """

    source = (source_root or globals()["source_root"]()).expanduser().resolve()
    cache = (cache_dir or cache_root()).expanduser().resolve()
    registry = list_tools(source_root=source)
    requested = capability_closure(capabilities, registry=registry)
    lock_digest = hashlib.sha256((source / "uv.lock").read_bytes()).hexdigest()[:20]
    tag = (
        f"{sys.implementation.name}-{sys.version_info.major}.{sys.version_info.minor}"
        f"-{sys.platform}-{platform.machine()}"
    )
    runtime = cache / "runtimes" / f"v{registry['api_version']}-{lock_digest}-{tag}"
    with _directory_lock(cache / ".tools.lock"):
        code = _deploy_code(source, cache)
        previous = _read_json(runtime / "manifest.json")
        installed = set(previous.get("capabilities", []))
        complete = capability_closure(installed | set(requested), registry=registry)
        missing = set(complete) - installed
        environment_path = runtime / "environment"
        candidate = environment_path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not candidate.is_file():
            missing = set(complete)
        record: dict[str, Any] = {
            "schema_version": "1.0.0",
            "api_version": registry["api_version"],
            "lock_digest": lock_digest,
            "cache_dir": str(cache),
            "code_root": str(code),
            "runtime_root": str(runtime),
            "python": str(candidate),
            "entrypoint": str(code / "apa.py"),
            "capabilities": list(complete),
            "renderer_environment": previous.get("renderer_environment", {}),
            "versions": previous.get("versions", {}),
        }
        if not missing and not _doctor_record(record, complete)["valid"]:
            missing = set(complete)
        if missing:
            uv = shutil.which("uv")
            if uv is None:
                raise ToolBootstrapError("uv is required to install or repair shared CLI tools")
            runtime.mkdir(parents=True, exist_ok=True)
            environment = os.environ.copy()
            if not candidate.is_file():
                _run(
                    [uv, "venv", "--python", sys.executable, str(environment_path)],
                    environment=environment,
                )
            extras = sorted(
                {extra for name in complete for extra in registry["capabilities"][name]["extras"]}
            )
            export = [
                uv,
                "export",
                "--project",
                str(code),
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--no-header",
                "--no-annotate",
            ]
            for extra in extras:
                export.extend(("--extra", extra))
            requirements = runtime / "requirements.txt"
            requirements.write_text(
                _capture(export, environment=environment) + "\n", encoding="utf-8"
            )
            _run(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    str(candidate),
                    "--require-hashes",
                    "--no-deps",
                    "--requirements",
                    str(requirements),
                ],
                environment=environment,
            )
        if any(registry["capabilities"][name].get("renderer") for name in complete):
            record["renderer_environment"] = prepare_renderer(code / "renderer", cache_dir=cache)
        record["environment"] = _runtime_environment(record)
        result = _doctor_record(record, complete)
        if not result["valid"]:
            raise ToolBootstrapError("Tool self-check failed: " + "; ".join(result["errors"]))
        record["versions"] = result.get("versions", {})
        record["environment"] = _runtime_environment(record)
        if "reports" in complete and (
            missing
            or previous.get("code_root") != str(code)
            or previous.get("versions") != record["versions"]
        ):
            _render_probe(record)
        _write_json(runtime / "manifest.json", record)
        _write_json(cache / "active.json", record)
        return {
            **result,
            **record,
            "installed": sorted(missing),
            "reused": sorted(set(complete) - missing),
        }
