"""Append-only JSONL evidence ledgers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .contracts import validate_instance

LEDGER_SCHEMAS = {
    "relationship": "relationship-record.schema.json",
}


def validate_record(record: dict[str, Any], kind: str) -> list[str]:
    """Validate one supported ledger record."""

    try:
        schema = LEDGER_SCHEMAS[kind]
    except KeyError as error:
        raise ValueError(f"Unsupported ledger kind: {kind}") from error
    return validate_instance(record, schema)


def append_record(path: Path, record: dict[str, Any], kind: str) -> None:
    """Append one validated record and fsync the ledger."""

    errors = validate_record(record, kind)
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"Invalid {kind} record: {joined}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_records(path: Path) -> Iterable[dict[str, Any]]:
    """Yield JSON objects from a ledger and report malformed line numbers."""

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"Ledger record at {path}:{line_number} is not an object")
            yield record
