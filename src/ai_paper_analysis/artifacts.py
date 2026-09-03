"""Safe run-directory and atomic publication operations."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ARTIFACT_KINDS = frozenset(
    {"paper-pdf", "paper-report", "classification", "taxonomy", "category-report"}
)


class ArtifactConflictError(RuntimeError):
    """Raised when publication would overwrite an existing artifact."""


@dataclass(frozen=True)
class PublishResult:
    destination: Path


def new_run_id(now: datetime | None = None) -> str:
    """Return a sortable run ID."""

    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _validate_run_id(run_id: str) -> None:
    if not run_id or "/" in run_id or "\\" in run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be one explicit directory name")


def ensure_target_layout(target_root: Path, run_id: str) -> dict[str, Path]:
    """Create the minimal persistent artifact layout and return its paths."""

    _validate_run_id(run_id)
    target_root = target_root.resolve()
    papers = target_root / "papers"
    category_reports = target_root / "category-reports"
    run_root = target_root / ".ai-paper-analysis" / "runs" / run_id
    candidates = run_root / "candidates"
    state = target_root / ".ai-paper-analysis" / "state"
    archive = target_root / ".ai-paper-analysis" / "archive"
    for path in (papers, category_reports, candidates, state, archive):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "target_root": target_root,
        "papers": papers,
        "category_reports": category_reports,
        "run_root": run_root,
        "candidates": candidates,
        "state": state,
        "archive": archive,
    }


def safe_relative_path(root: Path, relative: str) -> Path:
    """Resolve a relative artifact path without permitting traversal."""

    candidate = (root.resolve() / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"Artifact path escapes target root: {relative}")
    return candidate


def atomic_publish(source: Path, destination: Path) -> PublishResult:
    """Publish a validated file without overwriting an existing destination."""

    source = source.resolve(strict=True)
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ArtifactConflictError(f"Destination already exists: {destination}")

    return _atomic_replace(source, destination)


def _atomic_replace(source: Path, destination: Path) -> PublishResult:
    """Copy and atomically replace one destination on its own filesystem."""

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".publishing", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as target, source.open("rb") as origin:
            shutil.copyfileobj(origin, target, length=1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, destination)
        directory_flag = getattr(os, "O_DIRECTORY", None)
        if directory_flag is not None:
            directory_descriptor = os.open(destination.parent, directory_flag)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)
    return PublishResult(destination=destination)


def archive_and_promote(
    current: Path,
    candidate: Path,
    archive_root: Path,
    *,
    archive_retention: int = 1,
) -> PublishResult:
    """Archive a current report and promote an explicitly approved revision."""

    if archive_retention < 1:
        raise ValueError("archive_retention must be at least one")
    candidate = candidate.resolve(strict=True)
    if not current.exists():
        return atomic_publish(candidate, current)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    archive_path = archive_root / current.stem / f"{stamp}{current.suffix}"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_publish(current, archive_path)
    result = _atomic_replace(candidate, current.resolve())
    prior_archives = sorted(
        (path for path in archive_path.parent.glob(f"*{current.suffix}") if path != archive_path),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    for obsolete in prior_archives[max(archive_retention - 1, 0) :]:
        obsolete.unlink()
    return result


def _relative_existing_file(target_root: Path, path: Path, *, label: str) -> tuple[Path, str]:
    root = target_root.resolve()
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"{label} must be a file: {resolved}")
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must be inside the target root: {resolved}")
    return resolved, resolved.relative_to(root).as_posix()


def record_artifact_state(
    target_root: Path,
    artifact: Path,
    *,
    artifact_kind: str,
    run_id: str,
    sources: tuple[Path, ...] = (),
    now: datetime | None = None,
) -> Path:
    """Write one compact state record for a published formal artifact."""

    if artifact_kind not in ARTIFACT_KINDS:
        choices = ", ".join(sorted(ARTIFACT_KINDS))
        raise ValueError(f"artifact_kind must be one of: {choices}")
    _validate_run_id(run_id)

    root = target_root.resolve()
    artifact_path, artifact_relative = _relative_existing_file(root, artifact, label="artifact")
    source_records: set[str] = set()
    for source in sources:
        _, source_relative = _relative_existing_file(root, source, label="source")
        source_records.add(source_relative)

    payload = {
        "schema_version": "1.0.0",
        "artifact": {
            "kind": artifact_kind,
            "path": artifact_relative,
        },
        "sources": [{"path": path} for path in sorted(source_records)],
        "last_run_id": run_id,
        "status": "published",
        "updated_at": (now or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
    }
    state_name = f"{artifact_path.stem}.{artifact_kind}.json"
    state_path = root / ".ai-paper-analysis" / "state" / state_name
    write_json_atomic(state_path, payload)
    return state_path


def write_json_atomic(path: Path, payload: object) -> None:
    """Write UTF-8 JSON atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".writing", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
