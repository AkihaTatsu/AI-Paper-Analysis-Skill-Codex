from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_paper_analysis.artifacts import (
    ArtifactConflictError,
    archive_and_promote,
    atomic_publish,
    ensure_target_layout,
    new_run_id,
    record_artifact_state,
    safe_relative_path,
)
from ai_paper_analysis.contracts import validate_instance
from ai_paper_analysis.identifiers import normalize_arxiv_id, normalize_doi, stable_paper_id


def test_stable_bibliographic_identity() -> None:
    assert normalize_doi("https://doi.org/10.1000/Example. ") == "10.1000/example"
    assert normalize_arxiv_id("https://arxiv.org/pdf/2501.12345v3.pdf") == "2501.12345"
    paper_id = stable_paper_id(doi="10.1000/example", arxiv_id="2501.12345")
    assert paper_id == "doi:10.1000/example"


def test_run_layout_and_safe_paths(tmp_path: Path) -> None:
    run_id = new_run_id(datetime(2026, 8, 28, 1, 2, 3, tzinfo=UTC))
    assert run_id.startswith("20260828T010203Z-")
    layout = ensure_target_layout(tmp_path, run_id)
    assert layout["papers"].is_dir()
    assert layout["candidates"].is_dir()
    assert layout["state"].is_dir()
    assert not (layout["run_root"] / "staging").exists()
    assert not (layout["run_root"] / "revision").exists()
    assert not (tmp_path / ".ai-paper-analysis" / "tools").exists()
    assert (
        safe_relative_path(tmp_path, "papers/example.pdf")
        == (tmp_path / "papers/example.pdf").resolve()
    )
    with pytest.raises(ValueError):
        safe_relative_path(tmp_path, "../escape.pdf")


def test_atomic_publish_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"first")
    destination = tmp_path / "output" / "artifact.bin"

    result = atomic_publish(source, destination)

    assert result.destination == destination.resolve()
    assert destination.read_bytes() == b"first"
    with pytest.raises(ArtifactConflictError):
        atomic_publish(source, destination)


def test_archive_and_promote_preserves_both_versions(tmp_path: Path) -> None:
    current = tmp_path / "papers" / "report.md"
    current.parent.mkdir()
    current.write_text("old report\n", encoding="utf-8")
    candidate = tmp_path / "revision.md"
    candidate.write_text("approved report\n", encoding="utf-8")

    result = archive_and_promote(current, candidate, tmp_path / "archive")

    assert result.destination == current.resolve()
    assert current.read_text(encoding="utf-8") == "approved report\n"
    archived = list((tmp_path / "archive" / "report").glob("*.md"))
    assert len(archived) == 1
    assert archived[0].read_text(encoding="utf-8") == "old report\n"


def test_archive_and_promote_keeps_only_latest_replaced_report(tmp_path: Path) -> None:
    current = tmp_path / "papers" / "report.md"
    current.parent.mkdir()
    current.write_text("version one\n", encoding="utf-8")
    candidate = tmp_path / "candidate.md"
    candidate.write_text("version two\n", encoding="utf-8")
    archive = tmp_path / "archive"

    archive_and_promote(current, candidate, archive)
    candidate.write_text("version three\n", encoding="utf-8")
    archive_and_promote(current, candidate, archive)

    archived = list((archive / "report").glob("*.md"))
    assert len(archived) == 1
    assert archived[0].read_text(encoding="utf-8") == "version two\n"


def test_failed_promotion_does_not_change_current_or_archive(tmp_path: Path) -> None:
    current = tmp_path / "papers" / "report.md"
    current.parent.mkdir()
    current.write_text("current\n", encoding="utf-8")
    archive = tmp_path / "archive"

    with pytest.raises(FileNotFoundError):
        archive_and_promote(current, tmp_path / "missing.md", archive)

    assert current.read_text(encoding="utf-8") == "current\n"
    assert not archive.exists()


def test_record_artifact_state_is_compact_and_path_only(tmp_path: Path) -> None:
    report = tmp_path / "papers" / "paper.md"
    source = tmp_path / "papers" / "paper.pdf"
    report.parent.mkdir()
    report.write_text("report\n", encoding="utf-8")
    source.write_bytes(b"pdf")

    state_path = record_artifact_state(
        tmp_path,
        report,
        artifact_kind="paper-report",
        run_id="20260831T010203Z-abcdef12",
        sources=(source,),
        now=datetime(2026, 8, 31, 1, 2, 3, tzinfo=UTC),
    )

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert validate_instance(payload, "artifact-state.schema.json") == []
    assert state_path.name == "paper.paper-report.json"
    assert payload["artifact"] == {"kind": "paper-report", "path": "papers/paper.md"}
    assert payload["sources"] == [{"path": "papers/paper.pdf"}]


def test_record_artifact_state_rejects_sources_outside_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    report = target / "papers" / "paper.md"
    outside = tmp_path / "outside.pdf"
    report.parent.mkdir(parents=True)
    report.write_text("report\n", encoding="utf-8")
    outside.write_bytes(b"pdf")

    with pytest.raises(ValueError, match="inside the target root"):
        record_artifact_state(
            target,
            report,
            artifact_kind="paper-report",
            run_id="20260831T010203Z-abcdef12",
            sources=(outside,),
        )
