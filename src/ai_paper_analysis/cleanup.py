"""Strictly scoped cleanup of one explicit run directory."""

from __future__ import annotations

from pathlib import Path


def _explicit_run_directory(target_root: Path, run_id: str) -> Path:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be one explicit directory name")
    root = target_root.resolve()
    run_root = (root / ".ai-paper-analysis" / "runs").resolve()
    directory = (run_root / run_id).resolve()
    if directory.parent != run_root:
        raise ValueError("Cleanup target is not one direct run directory")
    return directory


def cleanup_run(target_root: Path, run_id: str) -> int:
    """Delete exactly one validated direct child of the run directory."""

    directory = _explicit_run_directory(target_root, run_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"Run directory does not exist: {directory}")
    paths = sorted(directory.rglob("*"), key=lambda path: len(path.parts), reverse=True)
    deleted = 0
    for path in paths:
        if path.is_file() or path.is_symlink():
            path.unlink()
            deleted += 1
        elif path.is_dir():
            path.rmdir()
    directory.rmdir()
    return deleted
