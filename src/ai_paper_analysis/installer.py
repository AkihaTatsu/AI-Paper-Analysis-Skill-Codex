"""One explicit installer for standalone Skills and the official Codex plugin path."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .capabilities import list_tools, skill_capabilities
from .tooling import (
    ToolBootstrapError,
    _capture,
    _directory_lock,
    _read_json,
    _write_json,
    ensure_tools,
    source_root,
)

PLUGIN_ID = "ai-paper-analysis@ai-paper-analysis"


def _codex_environment(home: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(home)
    return environment


def _codex_json(home: Path, *arguments: str) -> dict[str, Any]:
    codex = shutil.which("codex")
    if codex is None:
        raise ToolBootstrapError("The Codex CLI is required for plugin installation")
    raw = _capture([codex, "plugin", *arguments, "--json"], environment=_codex_environment(home))
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ToolBootstrapError("The Codex CLI returned an unexpected plugin response")
    return result


def _installed_plugin(home: Path) -> bool:
    if shutil.which("codex") is None:
        if (home / "plugins" / "cache" / "ai-paper-analysis").is_dir():
            raise ToolBootstrapError(
                "Install the Codex CLI to check the existing plugin "
                "before adding a standalone Skill"
            )
        return False
    listing = _codex_json(home, "list", "--marketplace", "ai-paper-analysis")
    return any(
        item.get("pluginId") == PLUGIN_ID and item.get("enabled", True)
        for item in listing.get("installed", [])
    )


def _managed_skill(path: Path) -> bool:
    if _read_json(path / ".apa-install.json").get("managed_by") == "ai-paper-analysis":
        return True
    launcher = path / "scripts" / "apa.py"
    if not launcher.is_file():
        return False
    text = launcher.read_text(encoding="utf-8")
    return f"Generated capability-scoped entrypoint for {path.name}." in text


def _archive_skill(path: Path, home: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    archive = home / ".apa-backups" / f"{stamp}-{path.name}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, archive)
    return archive


def _copy_skill(source: Path, destination: Path, tools: dict[str, Any], home: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".apa-install-", dir=destination.parent))
    backup: Path | None = None
    try:
        shutil.copytree(
            source,
            temporary,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                "_vendor", "node_modules", ".venv", "__pycache__", ".apa-runtime.json"
            ),
        )
        _write_json(temporary / ".apa-runtime.json", tools)
        _write_json(temporary / ".apa-install.json", {"managed_by": "ai-paper-analysis"})
        if destination.exists():
            backup = _archive_skill(destination, home)
        try:
            os.replace(temporary, destination)
        except OSError:
            if backup is not None:
                os.replace(backup, destination)
            raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def install(
    *,
    skills: Iterable[str] = (),
    plugin: bool = False,
    destination: Path | None = None,
    cache_dir: Path | None = None,
    source: Path | None = None,
) -> dict[str, Any]:
    """Prepare and verify tools before publishing a Skill or invoking plugin add.

    destination is a Codex home, not a Skill directory. For plugins it is passed
    to the official CLI as CODEX_HOME; no synthetic plugin installation is made.
    """

    source = (source or source_root()).expanduser().resolve()
    home = (
        (destination or Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")))
        .expanduser()
        .resolve()
    )
    registry = list_tools(source_root=source)
    names = tuple(
        dict.fromkeys(
            name if name.startswith("ai-paper-analysis") else f"ai-paper-analysis-{name}"
            for name in skills
        )
    )
    if plugin:
        names = tuple(registry["skills"])
    if not names:
        raise ValueError("Specify at least one --skill or --plugin")
    home.mkdir(parents=True, exist_ok=True)
    with _directory_lock(home / ".apa-install.lock"):
        existing_plugin = _installed_plugin(home)
        if existing_plugin:
            names = tuple(registry["skills"])
        required = skill_capabilities(names, registry=registry)
        candidates = tuple(home / "skills" / name for name in names)
        conflicts = [str(path) for path in candidates if path.exists() and not _managed_skill(path)]
        if conflicts:
            raise ToolBootstrapError(
                "Existing unmanaged Skill would conflict: " + ", ".join(conflicts)
            )
        tools = ensure_tools(required, source_root=source, cache_dir=cache_dir)
        # If the full plugin already provides this Skill, keep a single invocation surface.
        use_plugin = plugin or existing_plugin
        installed_paths: list[str] = []
        if use_plugin:
            marketplaces = _codex_json(home, "marketplace", "list").get("marketplaces", [])
            matches = [item for item in marketplaces if item.get("name") == "ai-paper-analysis"]
            if matches and Path(matches[0]["root"]).resolve() != source:
                raise ToolBootstrapError(
                    "The ai-paper-analysis marketplace points to a different checkout: "
                    + str(matches[0]["root"])
                )
            if not matches:
                _codex_json(home, "marketplace", "add", str(source))
            added = _codex_json(home, "add", PLUGIN_ID)
            plugin_root = Path(added["installedPath"])
            if not plugin_root.is_dir():
                raise ToolBootstrapError(
                    f"Codex reported a missing plugin installation: {plugin_root}"
                )
            for skill in registry["skills"]:
                installed = plugin_root / "skills" / skill
                if not (installed / "SKILL.md").is_file():
                    raise ToolBootstrapError(f"Codex plugin is missing a Skill: {installed}")
                _write_json(installed / ".apa-runtime.json", tools)
                installed_paths.append(str(installed))
            # Successful plugin registration precedes archiving superseded standalone copies.
            for name in registry["skills"]:
                standalone = home / "skills" / name
                if standalone.exists():
                    if not _managed_skill(standalone):
                        raise ToolBootstrapError(
                            f"Existing unmanaged Skill would conflict: {standalone}"
                        )
                    _archive_skill(standalone, home)
        else:
            for name in names:
                target = home / "skills" / name
                _copy_skill(source / "skills" / name, target, tools, home)
                installed_paths.append(str(target))
        return {
            "valid": True,
            "mode": "plugin" if use_plugin else "standalone",
            "destination": str(home),
            "skills": installed_paths,
            "tools": tools,
        }


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill", action="append", default=[], help="Skill name; repeat to install several"
    )
    parser.add_argument(
        "--plugin",
        action="store_true",
        help="Install the complete plugin using the official Codex CLI",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        help="Codex home; also passed as CODEX_HOME for plugin operations",
    )
    parser.add_argument("--cache-dir", type=Path, help="Isolated shared tool cache")
    parser.add_argument(
        "--source", type=Path, help="Repository checkout containing the locked tool sources"
    )
    args = parser.parse_args(arguments)
    try:
        result = install(
            skills=args.skill,
            plugin=args.plugin,
            destination=args.destination,
            cache_dir=args.cache_dir,
            source=args.source,
        )
    except (OSError, ValueError, ToolBootstrapError) as error:
        print(json.dumps({"valid": False, "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
