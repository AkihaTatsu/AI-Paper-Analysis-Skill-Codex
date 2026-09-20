#!/usr/bin/env python3
"""Generate capability-scoped standalone Skills and the complete plugin mirror."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "ai-paper-analysis",
    "ai-paper-analysis-finder",
    "ai-paper-analysis-interpreter",
    "ai-paper-analysis-comparator",
)
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
# Instruction packages select shared capabilities; executable code has one owner.
CONTRACTS = {
    skill: {p.name for p in (ROOT / "contracts").glob("*") if p.is_file()} for skill in SKILLS
}
TEMPLATES = {skill: {"paper-report.md", "category-report.md"} for skill in SKILLS}

IGNORED_TREE_PARTS = {".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}


def _materialized_files(root: Path) -> set[Path]:
    if not root.is_dir():
        return set()
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not (set(path.relative_to(root).parts) & IGNORED_TREE_PARTS)
    }


def _write_if_changed(path: Path, content: str, *, check: bool, errors: list[str]) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return
    if check:
        errors.append(f"generated file is stale or missing: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _sync_files(
    source: Path,
    destination: Path,
    names: set[str],
    *,
    check: bool,
    errors: list[str],
) -> None:
    expected = {Path(name) for name in names}
    observed = _materialized_files(destination)
    for relative in sorted(expected):
        source_path = source / relative
        destination_path = destination / relative
        if destination_path.is_file() and filecmp.cmp(source_path, destination_path, shallow=False):
            continue
        if check:
            errors.append(f"materialized file differs: {destination_path.relative_to(ROOT)}")
        else:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
    for relative in sorted(observed - expected, reverse=True):
        stale = destination / relative
        if check:
            errors.append(f"stale materialized file: {stale.relative_to(ROOT)}")
        else:
            stale.unlink()
    if not check and destination.is_dir():
        for directory in sorted(
            (path for path in destination.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()


def _copy_tree(source: Path, destination: Path, *, check: bool, errors: list[str]) -> None:
    names = {path.as_posix() for path in _materialized_files(source)}
    _sync_files(source, destination, names, check=check, errors=errors)


def _skill_pyproject(skill: str) -> str:
    return f'''[project]
name = "{skill}"
version = "{VERSION}"
description = "Instruction package using the shared AI Paper Analysis tools"
requires-python = ">=3.11"
dependencies = []

[tool.uv]
package = false
'''


def _launcher(skill: str) -> str:
    return f'''#!/usr/bin/env python3
"""Shared-tool launcher for {skill}; no sibling Skill is required."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

skill_root = Path(__file__).resolve().parents[1]
if configured := os.environ.get("APA_CACHE_DIR"):
    cache = Path(configured).expanduser()
elif os.name == "nt":
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    cache = base / "ai-paper-analysis"
elif sys.platform == "darwin":
    cache = Path.home() / "Library" / "Caches" / "ai-paper-analysis"
else:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ai-paper-analysis"
pointer = skill_root / ".apa-runtime.json"
if not pointer.is_file():
    pointer = cache / "active.json"
try:
    record = json.loads(pointer.read_text(encoding="utf-8"))
    python, entrypoint = record["python"], record["entrypoint"]
    if not Path(python).is_file() or not Path(entrypoint).is_file():
        raise ValueError("Shared runtime is missing")
except (OSError, ValueError, KeyError, TypeError):
    print("Run the repository installer: python scripts/install.py"
          " --skill {skill}", file=sys.stderr)
    raise SystemExit(1) from None

environment = os.environ.copy()
environment.pop("APA_SKILL_COMMANDS", None)
environment.update(record["environment"])
os.execve(python, [python, entrypoint, *sys.argv[1:]], environment)
'''


def _remove_one_off_skill_scripts(skill_root: Path, *, check: bool, errors: list[str]) -> None:
    scripts = skill_root / "scripts"
    if not scripts.is_dir():
        return
    for path in scripts.iterdir():
        if path.is_file() and path.name != "apa.py":
            if check:
                errors.append(
                    f"one-off Skill script must not be packaged: {path.relative_to(ROOT)}"
                )
            else:
                path.unlink()


def synchronize(*, check: bool) -> list[str]:
    errors: list[str] = []
    runtime_source = ROOT / "src" / "ai_paper_analysis"
    contracts_source = ROOT / "contracts"
    templates_source = ROOT / "templates"
    for skill in SKILLS:
        skill_root = ROOT / "skills" / skill
        _sync_files(
            runtime_source,
            skill_root / "scripts" / "_vendor" / "ai_paper_analysis",
            set(),
            check=check,
            errors=errors,
        )
        _sync_files(
            contracts_source,
            skill_root / "references" / "contracts",
            CONTRACTS[skill],
            check=check,
            errors=errors,
        )
        _sync_files(
            templates_source,
            skill_root / "references" / "templates",
            TEMPLATES[skill],
            check=check,
            errors=errors,
        )
        # Remove obsolete per-Skill renderer copies; tools own these resources.
        _sync_files(ROOT, skill_root / "references" / "renderer", set(), check=check, errors=errors)
        _copy_tree(ROOT / "roles", skill_root / "references" / "roles", check=check, errors=errors)
        _write_if_changed(
            skill_root / "scripts" / "apa.py", _launcher(skill), check=check, errors=errors
        )
        _remove_one_off_skill_scripts(skill_root, check=check, errors=errors)
        _write_if_changed(
            skill_root / "pyproject.toml", _skill_pyproject(skill), check=check, errors=errors
        )
    _copy_tree(
        ROOT / "skills",
        ROOT / "plugins" / "ai-paper-analysis" / "skills",
        check=check,
        errors=errors,
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without writing files")
    arguments = parser.parse_args()
    errors = synchronize(check=arguments.check)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(
        "Materialized files are synchronized." if arguments.check else "Materialized files updated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
