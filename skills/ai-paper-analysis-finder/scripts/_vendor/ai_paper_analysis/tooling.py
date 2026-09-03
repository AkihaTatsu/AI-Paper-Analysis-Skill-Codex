"""Shared, versioned tool environments for installed Skills and the wheel CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

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
    )
    if process.returncode:
        detail = " ".join((process.stderr or process.stdout).split())[:1000]
        raise ToolBootstrapError(detail or f"Tool command failed: {command[0]}")


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
            shutil.copy2(origin, temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def prepare_renderer(source: Path | None = None) -> dict[str, str]:
    """Create or reuse the locked full report-rendering environment."""

    source = (source or renderer_source()).resolve()
    parent = cache_root() / "renderer"
    destination = parent / f"v{RENDERER_API_VERSION}"
    browser = _system_browser()
    if not _manifest_matches(destination, kind="renderer", api_version=RENDERER_API_VERSION):
        node = shutil.which("node")
        npm = shutil.which("npm")
        if node is None or npm is None:
            raise ToolBootstrapError(
                "Node.js and npm are required to initialize the report renderer"
            )
        with _directory_lock(parent / ".bootstrap.lock"):
            if not _manifest_matches(
                destination, kind="renderer", api_version=RENDERER_API_VERSION
            ):
                parent.mkdir(parents=True, exist_ok=True)
                temporary = Path(tempfile.mkdtemp(prefix=".renderer-", dir=parent))
                try:
                    _copy_renderer_source(source, temporary)
                    environment = os.environ.copy()
                    environment["PUPPETEER_CACHE_DIR"] = str(temporary / "browser")
                    _run(
                        [
                            npm,
                            "ci",
                            "--ignore-scripts",
                            "--include=dev",
                            "--prefix",
                            str(temporary),
                        ],
                        environment=environment,
                    )
                    if browser is None:
                        _run(
                            [
                                npm,
                                "exec",
                                "--prefix",
                                str(temporary),
                                "--",
                                "puppeteer",
                                "browsers",
                                "install",
                                "chrome-headless-shell",
                            ],
                            environment=environment,
                        )
                    _write_manifest(temporary, kind="renderer", api_version=RENDERER_API_VERSION)
                    if destination.exists():
                        shutil.rmtree(destination)
                    os.replace(temporary, destination)
                finally:
                    if temporary.exists():
                        shutil.rmtree(temporary)
                _prune_versions(parent, destination)
    with _directory_lock(parent / ".program.lock"):
        _refresh_renderer_program(source, destination)
    environment_updates = {
        "APA_RENDERER_ROOT": str(destination),
        "PUPPETEER_CACHE_DIR": str(destination / "browser"),
    }
    if browser is not None:
        environment_updates["PUPPETEER_EXECUTABLE_PATH"] = browser
    return environment_updates


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
        environment.update(prepare_renderer(skill_root / "references" / "renderer"))
    executable_directory = python.parent
    environment["PATH"] = os.pathsep.join((str(executable_directory), environment.get("PATH", "")))
    os.execve(
        python,
        [str(python), str(entrypoint), *sys.argv[1:]],
        environment,
    )
