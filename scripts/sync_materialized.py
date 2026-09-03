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
RUNTIME_DEPENDENCIES = (
    "httpx>=0.28,<1",
    "jsonschema>=4.23,<5",
    "markdown-it-py>=3.0,<5",
    "mkdocs>=1.6,<2",
    "mkdocs-material>=9.6,<10",
    "pymupdf>=1.25,<2",
    "pypdf>=5.1,<7",
    "pymdown-extensions>=11.0.1",
    "pyyaml>=6.0,<7",
    "typer>=0.15,<1",
)
COMMON_MODULES = {
    "__init__.py",
    "cli.py",
    "constants.py",
    "contracts.py",
    "tooling.py",
}
MODULES = {
    "ai-paper-analysis": COMMON_MODULES
    | {"artifacts.py", "cleanup.py", "run_spec.py", "temporary.py"},
    "ai-paper-analysis-finder": COMMON_MODULES
    | {
        "artifacts.py",
        "classification.py",
        "cleanup.py",
        "credentials.py",
        "identifiers.py",
        "pdf.py",
        "providers.py",
        "run_spec.py",
        "temporary.py",
    },
    "ai-paper-analysis-interpreter": COMMON_MODULES
    | {
        "artifacts.py",
        "cleanup.py",
        "identifiers.py",
        "markdown_audit.py",
        "pdf.py",
        "report_audit.py",
        "run_spec.py",
        "temporary.py",
    },
    "ai-paper-analysis-comparator": COMMON_MODULES
    | {
        "artifacts.py",
        "classification.py",
        "cleanup.py",
        "identifiers.py",
        "ledger.py",
        "markdown_audit.py",
        "pdf.py",
        "report_audit.py",
        "run_spec.py",
        "temporary.py",
    },
}
CONTRACTS = {
    "ai-paper-analysis": {
        "artifact-state.schema.json",
        "provider-registry.json",
        "run-spec.schema.json",
    },
    "ai-paper-analysis-finder": {
        "artifact-state.schema.json",
        "classification-row.schema.json",
        "provider-registry.json",
        "run-spec.schema.json",
        "taxonomy.schema.json",
    },
    "ai-paper-analysis-interpreter": {
        "artifact-state.schema.json",
        "markdown-profile.md",
        "provider-registry.json",
        "run-spec.schema.json",
    },
    "ai-paper-analysis-comparator": {
        "artifact-state.schema.json",
        "classification-row.schema.json",
        "markdown-profile.md",
        "provider-registry.json",
        "relationship-record.schema.json",
        "run-spec.schema.json",
        "taxonomy.schema.json",
    },
}
TEMPLATES = {
    "ai-paper-analysis": set(),
    "ai-paper-analysis-finder": set(),
    "ai-paper-analysis-interpreter": {"paper-report.md"},
    "ai-paper-analysis-comparator": {"category-report.md"},
}
RENDERER_SKILLS = {
    "ai-paper-analysis-interpreter",
    "ai-paper-analysis-comparator",
}
COMMANDS = {
    "ai-paper-analysis": (
        "validate-spec",
        "init-run",
        "create-temp",
        "cleanup-temp",
        "publish",
        "promote-revision",
        "record-state",
        "cleanup-run",
    ),
    "ai-paper-analysis-finder": (
        "providers",
        "validate-spec",
        "init-run",
        "discover",
        "create-temp",
        "cleanup-temp",
        "download-pdf",
        "validate-pdf",
        "artifact-name",
        "publish",
        "record-state",
        "validate-classification",
        "cleanup-run",
    ),
    "ai-paper-analysis-interpreter": (
        "validate-spec",
        "init-run",
        "create-temp",
        "cleanup-temp",
        "validate-pdf",
        "publish",
        "promote-revision",
        "record-state",
        "audit-markdown",
        "audit-paper-report",
        "cleanup-run",
    ),
    "ai-paper-analysis-comparator": (
        "validate-spec",
        "init-run",
        "create-temp",
        "cleanup-temp",
        "publish",
        "promote-revision",
        "record-state",
        "validate-classification",
        "audit-markdown",
        "audit-category-report",
        "cleanup-run",
    ),
}
RENDERER_COMMANDS = {
    "ai-paper-analysis": (),
    "ai-paper-analysis-finder": (),
    "ai-paper-analysis-interpreter": ("audit-markdown", "audit-paper-report"),
    "ai-paper-analysis-comparator": (
        "validate-classification",
        "audit-markdown",
        "audit-category-report",
    ),
}
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
    dependencies = "\n".join(f'  "{dependency}",' for dependency in RUNTIME_DEPENDENCIES)
    return f'''[project]
name = "{skill}"
version = "{VERSION}"
description = "Shared-cache runtime for the {skill} Codex Skill"
requires-python = ">=3.11"
dependencies = [
{dependencies}
]

[project.optional-dependencies]
ocr = ["ocrmypdf>=16.7,<18"]

[tool.uv]
package = false
'''


def _tuple_literal(values: tuple[str, ...]) -> str:
    if not values:
        return "()"
    joined = "".join(f'    "{value}",\n' for value in values)
    return f"(\n{joined})"


def _launcher(skill: str) -> str:
    commands = _tuple_literal(COMMANDS[skill])
    renderer_commands = _tuple_literal(RENDERER_COMMANDS[skill])
    return f'''#!/usr/bin/env python3
"""Generated capability-scoped entrypoint for {skill}."""

from __future__ import annotations

import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = Path(__file__).resolve()
sys.path.insert(0, str(SKILL_ROOT / "scripts" / "_vendor"))

COMMANDS = {commands}
RENDERER_COMMANDS = {renderer_commands}

if os.environ.get("APA_BOOTSTRAPPED") != "1":
    from ai_paper_analysis.tooling import reexecute_skill

    reexecute_skill(
        skill_root=SKILL_ROOT,
        entrypoint=ENTRYPOINT,
        skill_name="{skill}",
        commands=COMMANDS,
        renderer_commands=RENDERER_COMMANDS,
    )

os.environ.setdefault("APA_CONTRACTS_DIR", str(SKILL_ROOT / "references" / "contracts"))
os.environ.setdefault("APA_SKILL_COMMANDS", ",".join(COMMANDS))
os.environ.setdefault("APA_SKILL_NAME", "{skill}")

from ai_paper_analysis.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
'''


def _renderer_files() -> set[str]:
    return {
        "package.json",
        "package-lock.json",
        ".markdownlint-cli2.yaml",
        "scripts/check_mermaid.mjs",
        "scripts/render_report.mjs",
    }


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
            MODULES[skill],
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
        renderer_names = _renderer_files() if skill in RENDERER_SKILLS else set()
        _sync_files(
            ROOT,
            skill_root / "references" / "renderer",
            renderer_names,
            check=check,
            errors=errors,
        )
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
