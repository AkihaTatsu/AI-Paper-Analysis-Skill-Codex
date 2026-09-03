#!/usr/bin/env python3
"""Validate version, language, manifests, Skills, schemas, and generated copies."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "ai-paper-analysis",
    "ai-paper-analysis-finder",
    "ai-paper-analysis-interpreter",
    "ai-paper-analysis-comparator",
)
IGNORED_PARTS = {".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _validate_versions(errors: list[str]) -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        _error(errors, "VERSION is not strict semantic versioning")
    plugin = json.loads(
        (ROOT / "plugins/ai-paper-analysis/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    if plugin.get("version") != version:
        _error(errors, "Plugin version does not match VERSION")
    if plugin.get("author", {}).get("name") != "AkihaTatsu":
        _error(errors, "Plugin author must be AkihaTatsu")
    if "email" in plugin.get("author", {}):
        _error(errors, "Plugin manifest must not publish an author email")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if pyproject.get("project", {}).get("dynamic") != ["version"]:
        _error(errors, "Root Python package version must be dynamic")
    if pyproject.get("tool", {}).get("hatch", {}).get("version", {}).get("path") != "VERSION":
        _error(errors, "Root Python package must read its version from VERSION")
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    if package.get("version") != version:
        _error(errors, "package.json version does not match VERSION")
    if package_lock.get("version") != version:
        _error(errors, "package-lock.json version does not match VERSION")
    if package_lock.get("packages", {}).get("", {}).get("version") != version:
        _error(errors, "package-lock root version does not match VERSION")
    for skill in SKILLS:
        pyproject = (ROOT / "skills" / skill / "pyproject.toml").read_text(encoding="utf-8")
        if f'version = "{version}"' not in pyproject:
            _error(errors, f"{skill} version does not match VERSION")


def _validate_marketplace(errors: list[str]) -> None:
    marketplace = json.loads(
        (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
    )
    if marketplace.get("name") != "ai-paper-analysis":
        _error(errors, "Marketplace name must be ai-paper-analysis")
    matches = [
        entry
        for entry in marketplace.get("plugins", [])
        if entry.get("name") == "ai-paper-analysis"
    ]
    if len(matches) != 1:
        _error(errors, "Marketplace must contain exactly one ai-paper-analysis entry")
        return
    entry = matches[0]
    if entry.get("source", {}).get("path") != "./plugins/ai-paper-analysis":
        _error(errors, "Marketplace plugin path is incorrect")
    if entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_USE"}:
        _error(errors, "Marketplace policy is incorrect")
    if entry.get("category") != "Research":
        _error(errors, "Marketplace category must be Research")


def _validate_skill(skill: str, errors: list[str]) -> None:
    root = ROOT / "skills" / skill
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    if "[TODO:" in text:
        _error(errors, f"{skill} contains a scaffold placeholder")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        _error(errors, f"{skill} has invalid YAML front matter")
        return
    frontmatter = yaml.safe_load(match.group(1))
    if frontmatter.get("name") != skill:
        _error(errors, f"{skill} frontmatter name does not match its folder")
    description = frontmatter.get("description", "")
    if not isinstance(description, str) or not description.strip():
        _error(errors, f"{skill} has no description")
    metadata = yaml.safe_load((root / "agents/openai.yaml").read_text(encoding="utf-8"))
    expected_implicit = skill == "ai-paper-analysis"
    if metadata.get("policy", {}).get("allow_implicit_invocation") is not expected_implicit:
        _error(errors, f"{skill} invocation policy is incorrect")
    default_prompt = metadata.get("interface", {}).get("default_prompt", "")
    if f"${skill}" not in default_prompt:
        _error(errors, f"{skill} default prompt must name ${skill}")


def _validate_schemas(errors: list[str]) -> None:
    for path in sorted((ROOT / "contracts").glob("*.schema.json")):
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exception:
            _error(errors, f"Invalid schema {path.name}: {exception}")
    provider_registry = json.loads(
        (ROOT / "contracts/provider-registry.json").read_text(encoding="utf-8")
    )
    identifiers = [provider["id"] for provider in provider_registry.get("providers", [])]
    if len(identifiers) != len(set(identifiers)):
        _error(errors, "Provider IDs are not unique")


def _validate_release_hygiene(errors: list[str]) -> None:
    for obsolete in ("NOTICE", "SECURITY.md"):
        if (ROOT / obsolete).exists():
            _error(errors, f"Obsolete release document is still present: {obsolete}")
    for obsolete in (
        "claim-record.schema.json",
        "formula-record.schema.json",
        "analogy-record.schema.json",
    ):
        if (ROOT / "contracts" / obsolete).exists():
            _error(errors, f"Obsolete encoded report audit is still present: {obsolete}")


def _validate_english_repository(errors: list[str]) -> None:
    cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
    roots = [
        ROOT / "README.md",
        ROOT / "skills",
        ROOT / "src",
        ROOT / "contracts",
        ROOT / "templates",
    ]
    for root in roots:
        paths = (
            [root]
            if root.is_file()
            else [
                path
                for path in root.rglob("*")
                if path.is_file() and not (set(path.relative_to(root).parts) & IGNORED_PARTS)
            ]
        )
        for path in paths:
            if path.suffix not in {".md", ".py", ".json", ".yaml", ".toml"}:
                continue
            if cjk.search(path.read_text(encoding="utf-8")):
                relative = path.relative_to(ROOT)
                _error(errors, f"Maintained repository content is not English-only: {relative}")


def main() -> int:
    errors: list[str] = []
    _validate_versions(errors)
    _validate_marketplace(errors)
    for skill in SKILLS:
        _validate_skill(skill, errors)
    _validate_schemas(errors)
    _validate_release_hygiene(errors)
    _validate_english_repository(errors)
    sync = subprocess.run(
        [sys.executable, str(ROOT / "scripts/sync_materialized.py"), "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if sync.returncode:
        _error(errors, sync.stderr.strip() or "Materialized-file check failed")
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
