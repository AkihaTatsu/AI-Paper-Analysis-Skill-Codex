"""Dependency-free loading and closure of the public tool capability registry."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def registry_path(source_root: Path | None = None) -> Path:
    if source_root is not None:
        return source_root / "contracts" / "tool-capabilities.json"
    if configured := os.environ.get("APA_CONTRACTS_DIR"):
        candidate = Path(configured) / "tool-capabilities.json"
        if candidate.is_file():
            return candidate
    module = Path(__file__).resolve()
    candidates = [module.parent / "_data" / "contracts" / "tool-capabilities.json"]
    candidates.extend(parent / "contracts" / "tool-capabilities.json" for parent in module.parents)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate the shared tool capability registry")


def list_tools(*, source_root: Path | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(registry_path(source_root).read_text(encoding="utf-8"))
    return payload


def capability_closure(
    requested: Iterable[str], *, registry: dict[str, Any] | None = None
) -> tuple[str, ...]:
    definitions = (registry or list_tools())["capabilities"]
    complete: set[str] = set()
    pending: set[str] = set()

    def include(name: str) -> None:
        if name not in definitions:
            raise ValueError(f"Unknown tool capability: {name}")
        if name in pending:
            raise ValueError(f"Cyclic tool capability dependency: {name}")
        if name in complete:
            return
        pending.add(name)
        for dependency in definitions[name]["requires"]:
            include(dependency)
        pending.remove(name)
        complete.add(name)

    for name in requested:
        include(name)
    return tuple(name for name in definitions if name in complete)


def skill_capabilities(
    names: Iterable[str], *, registry: dict[str, Any] | None = None
) -> tuple[str, ...]:
    registry = registry or list_tools()
    requested: set[str] = set()
    for name in names:
        full = name if name.startswith("ai-paper-analysis") else f"ai-paper-analysis-{name}"
        if full not in registry["skills"]:
            raise ValueError(f"Unknown Skill: {name}")
        requested.update(registry["skills"][full])
        for role in registry.get("skill_roles", {}).get(full, []):
            requested.update(registry["roles"][role])
    return capability_closure(requested, registry=registry)
