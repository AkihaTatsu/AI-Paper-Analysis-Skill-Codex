from __future__ import annotations

from pathlib import Path

import pytest

from ai_paper_analysis.artifacts import record_artifact_state
from ai_paper_analysis.content_review import (
    CHECKS,
    create_content_review,
    load_artifact_review,
    validate_content_review,
)
from ai_paper_analysis.contracts import validate_instance


def assessment(status: str = "complete") -> dict:
    return {
        "reviewer": "fixture reviewer",
        "reviewed_sections": list(range(1, 8)),
        "checks": dict.fromkeys(CHECKS, True),
        "content_status": status,
        "limitations": []
        if status == "complete"
        else ["One inaccessible original is explicitly excluded"],
    }


def test_review_bound_to_report_sources_and_publication_location(tmp_path: Path) -> None:
    report, source = tmp_path / "candidate.md", tmp_path / "source.pdf"
    report.write_text("draft with partial derivatives", encoding="utf-8")
    source.write_bytes(b"source fixture")
    formal = tmp_path / "papers" / "formal.md"
    review = create_content_review(report, assessment(), (source,), publication_path=formal)
    assert validate_content_review(report, review, publication_path=formal) == ("complete", [])
    assert validate_content_review(report, review)[0] == "unreviewed"
    source.write_bytes(b"modified source")
    assert "source changed" in " ".join(
        validate_content_review(report, review, publication_path=formal)[1]
    )
    source.write_bytes(b"source fixture")
    report.write_text("modified draft", encoding="utf-8")
    assert "report changed" in " ".join(
        validate_content_review(report, review, publication_path=formal)[1]
    )


def test_partial_review_is_explicit_and_complete_requires_all_checks(tmp_path: Path) -> None:
    report = tmp_path / "paper.md"
    source = tmp_path / "paper.pdf"
    report.write_text("partial derivative is ordinary mathematical terminology")
    source.write_bytes(b"source")
    assert validate_content_review(report, None) == ("unreviewed", [])
    review = create_content_review(report, assessment("partial"), (source,))
    assert validate_content_review(report, review)[0] == "partial"
    partial = assessment("partial")
    partial["checks"]["coverage"] = False
    assert create_content_review(report, partial, (source,))["content_status"] == "partial"
    partial["checks"]["source_fidelity"] = False
    with pytest.raises(ValueError, match="coverage only"):
        create_content_review(report, partial, (source,))
    invalid = assessment()
    invalid["checks"]["terminology"] = False
    with pytest.raises(ValueError, match="every semantic check"):
        create_content_review(report, invalid, (source,))
    incomplete = assessment()
    incomplete["reviewed_sections"] = [1, 2, 3]
    with pytest.raises(ValueError, match="every numbered section"):
        create_content_review(report, incomplete, (source,))


def test_compact_state_accepts_legacy_but_only_reuses_bound_review(tmp_path: Path) -> None:
    import json

    report, source = tmp_path / "paper.md", tmp_path / "paper.pdf"
    report.write_text("reviewed report")
    source.write_bytes(b"original")
    review = create_content_review(report, assessment(), (source,))
    state = record_artifact_state(
        tmp_path,
        report,
        artifact_kind="paper-report",
        run_id="fixture",
        sources=(source,),
        content_review=review,
    )
    payload = json.loads(state.read_text())
    assert validate_instance(payload, "artifact-state.schema.json") == []
    assert load_artifact_review(tmp_path, report) == review
    payload.pop("content_review")
    payload["schema_version"] = "1.0.0"
    assert validate_instance(payload, "artifact-state.schema.json") == []
    state.write_text(json.dumps(payload))
    assert load_artifact_review(tmp_path, report) is None


def test_review_policy_changes_invalidate_attestation(tmp_path: Path, monkeypatch) -> None:
    from ai_paper_analysis import content_review

    report, source = tmp_path / "report.md", tmp_path / "source.pdf"
    report.write_text("report")
    source.write_bytes(b"source")
    review = create_content_review(report, assessment(), (source,))
    monkeypatch.setattr(content_review, "policy_digest", lambda *args: "0" * 64)
    assert "policy changed" in " ".join(validate_content_review(report, review)[1])


@pytest.mark.parametrize(
    "report_kind,legacy_hash",
    [
        ("paper", "4596d133742a0d7d4fe4a8571bd39ce8b589240948e81837412fc315e9940a10"),
        ("category", "c0a55e05beac6bf18af8188bc7751000c6b577981be6733107e19bf9c3800c91"),
    ],
)
def test_pre_style_semantic_receipt_requires_review(tmp_path, report_kind, legacy_hash):
    report, source = tmp_path / "report.md", tmp_path / "source.pdf"
    report.write_text("report")
    source.write_bytes(b"source")
    completed = assessment()
    if report_kind == "category":
        completed["reviewed_sections"] = [1, 2, 3]
    review = create_content_review(report, completed, (source,), report_kind=report_kind)
    review["policy_sha256"] = legacy_hash
    status, errors = validate_content_review(report, review, report_kind=report_kind)
    assert status == "unreviewed"
    assert errors == ["content review is stale: review policy changed"]


@pytest.mark.parametrize("report_kind", ["paper", "category"])
def test_style_change_invalidates_bound_review(tmp_path, monkeypatch, report_kind):
    import shutil

    from ai_paper_analysis import content_review

    repository = Path(__file__).parents[1]
    shutil.copytree(repository / "roles", tmp_path / "roles")
    shutil.copytree(repository / "contracts", tmp_path / "contracts")
    monkeypatch.setattr(content_review, "contract_directory", lambda: tmp_path / "contracts")
    report, source = tmp_path / "report.md", tmp_path / "source.pdf"
    report.write_text("report")
    source.write_bytes(b"source")
    completed = assessment()
    if report_kind == "category":
        completed["reviewed_sections"] = [1, 2, 3]
    review = create_content_review(report, completed, (source,), report_kind=report_kind)
    assert validate_content_review(report, review, report_kind=report_kind) == ("complete", [])
    (tmp_path / "roles" / "report-style.md").write_text("Changed readability requirements")
    status, errors = validate_content_review(report, review, report_kind=report_kind)
    assert status == "unreviewed"
    assert errors == ["content review is stale: review policy changed"]


def test_policy_digest_ignores_other_roles_but_tracks_content_rules(tmp_path: Path, monkeypatch):
    import shutil

    from ai_paper_analysis import content_review

    repository = Path(__file__).parents[1]
    shutil.copytree(repository / "roles", tmp_path / "roles")
    shutil.copytree(repository / "contracts", tmp_path / "contracts")
    monkeypatch.setattr(content_review, "contract_directory", lambda: tmp_path / "contracts")
    before = content_review.policy_digest("paper")
    (tmp_path / "roles" / "intake.md").write_text("Different questions")
    (tmp_path / "roles" / "category-content.md").write_text("Different category policy")
    (tmp_path / "roles" / "paper-writer.md").write_text("Different workflow")
    (tmp_path / "roles" / "report-lifecycle.md").write_text("Different lifecycle")
    (tmp_path / "roles" / "semantic-review.md").write_text("Different review routing")
    (tmp_path / "contracts" / "report-review.schema.json").write_text("Different schema mechanics")
    assert content_review.policy_digest("paper") == before
    (tmp_path / "roles" / "paper-content.md").write_text("New paper requirement")
    assert content_review.policy_digest("paper") != before


def test_missing_report_invalidates_review_without_raising(tmp_path):
    report, source = tmp_path / "report.md", tmp_path / "source.pdf"
    report.write_text("report")
    source.write_bytes(b"source")
    review = create_content_review(report, assessment(), (source,))
    report.unlink()
    assert validate_content_review(report, review)[0] == "unreviewed"


@pytest.mark.parametrize(
    "field,value",
    [("schema_version", "unknown"), ("status", "candidate"), ("kind", "category-report")],
)
def test_invalid_state_wrapper_does_not_supply_paper_review(tmp_path, field, value):
    import json

    report, source = tmp_path / "report.md", tmp_path / "source.pdf"
    report.write_text("report")
    source.write_bytes(b"source")
    review = create_content_review(report, assessment(), (source,))
    state = record_artifact_state(
        tmp_path, report, artifact_kind="paper-report", run_id="fixture", content_review=review
    )
    payload = json.loads(state.read_text())
    (payload["artifact"] if field == "kind" else payload)[field] = value
    state.write_text(json.dumps(payload))
    assert load_artifact_review(tmp_path, report) is None


def test_old_state_update_preserves_only_current_valid_review(tmp_path):
    report, source = tmp_path / "report.md", tmp_path / "source.pdf"
    report.write_text("report")
    source.write_bytes(b"source")
    review = create_content_review(report, assessment(), (source,))
    record_artifact_state(
        tmp_path, report, artifact_kind="paper-report", run_id="first", content_review=review
    )
    record_artifact_state(tmp_path, report, artifact_kind="paper-report", run_id="second")
    assert load_artifact_review(tmp_path, report) == review
    report.write_text("changed report")
    record_artifact_state(tmp_path, report, artifact_kind="paper-report", run_id="third")
    assert load_artifact_review(tmp_path, report) is None
