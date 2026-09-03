"""Schema discovery and validation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


def contract_directory() -> Path:
    """Find contracts in a source checkout or a self-contained Skill."""

    if configured := os.environ.get("APA_CONTRACTS_DIR"):
        path = Path(configured).expanduser().resolve()
        if path.is_dir():
            return path
        raise FileNotFoundError(f"APA_CONTRACTS_DIR is not a directory: {path}")

    source = Path(__file__).resolve()
    packaged = source.parent / "_data" / "contracts"
    if (packaged / "run-spec.schema.json").is_file():
        return packaged
    for ancestor in source.parents:
        for candidate in (ancestor / "contracts", ancestor / "references" / "contracts"):
            if (candidate / "run-spec.schema.json").is_file():
                return candidate
    raise FileNotFoundError("Could not locate the AI Paper Analysis contracts directory")


def load_json(name: str, *, directory: Path | None = None) -> Any:
    """Load a contract JSON file."""

    path = (directory or contract_directory()) / name
    return json.loads(path.read_text(encoding="utf-8"))


def validate_instance(instance: object, schema_name: str) -> list[str]:
    """Return sorted human-readable validation errors."""

    schema = load_json(schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    messages: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{location}: {error.message}")
    return messages
