"""Strictly scoped system-temporary workspaces for disposable run artifacts."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

WORKSPACE_PREFIX = "ai-paper-analysis-"


def _root(temporary_root: Path | None) -> Path:
    return (temporary_root or Path(tempfile.gettempdir())).resolve()


def _validate_run_id(run_id: str) -> None:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be one explicit directory name")


def create_temporary_workspace(run_id: str, *, temporary_root: Path | None = None) -> Path:
    """Create one randomly named disposable workspace outside the target project."""

    _validate_run_id(run_id)
    root = _root(temporary_root)
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f"{WORKSPACE_PREFIX}{run_id}-", dir=root))


def remove_temporary_workspace(workspace: Path, *, temporary_root: Path | None = None) -> int:
    """Remove one recognized direct child of the configured temporary root."""

    root = _root(temporary_root)
    resolved = workspace.resolve(strict=True)
    if resolved.parent != root or not resolved.name.startswith(WORKSPACE_PREFIX):
        raise ValueError("refusing to remove an unrecognized temporary workspace")
    if not resolved.is_dir():
        raise ValueError("temporary workspace must be a directory")
    file_count = sum(1 for path in resolved.rglob("*") if path.is_file() or path.is_symlink())
    shutil.rmtree(resolved)
    return file_count
