from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_paper_analysis import cli, evidence_cache
from ai_paper_analysis.evidence_cache import lookup_evidence_cache, record_evidence_cache
from ai_paper_analysis.report_prepare import prepare_report


def packet(label: str = "Original paper") -> dict:
    return {
        "source": {"label": label},
        "coverage": {
            "complete": True,
            "page_count": 3,
            "page_ranges": [[1, 2]],
            "unreadable_pages": [3],
        },
        "locators": [{"id": "apa-method-p2", "locator": "p. 2, Methods", "page": 2}],
        "facts": [
            {
                "kind": "method",
                "summary": "The method uses a sparse intervention signal.",
                "locator_ids": ["apa-method-p2"],
            }
        ],
        "formulas": [
            {"id": "objective", "locator_id": "apa-method-p2", "visual_verified": True}
        ],
        "limitations": ["Page 3 was unreadable."],
    }


def test_project_cache_hit_miss_invalidation_and_concise_payload(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf-v1")
    assert lookup_evidence_cache(tmp_path, source, "paper", "all-pages")["reason"] == "missing"
    stored = record_evidence_cache(tmp_path, source, "paper", "all-pages", packet())
    assert Path(stored["path"]).parent == tmp_path / ".ai-paper-analysis" / "evidence-cache"
    assert lookup_evidence_cache(tmp_path, source, "paper", "all-pages")["hit"] is True
    serialized = Path(stored["path"]).read_text()
    assert "pdf-v1" not in serialized and "full_text" not in serialized
    source.write_bytes(b"pdf-v2")
    changed = lookup_evidence_cache(tmp_path, source, "paper", "all-pages")
    assert changed["hit"] is False and changed["cache_key"] != stored["cache_key"]


def test_cache_rejects_incomplete_unknown_and_copied_text(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    incomplete = packet()
    incomplete["coverage"]["page_ranges"] = [[1, 1]]
    with pytest.raises(ValueError, match="must cover"):
        record_evidence_cache(tmp_path, source, "paper", "all", incomplete)
    unknown = packet()
    unknown["facts"][0]["locator_ids"] = ["apa-unknown"]
    with pytest.raises(ValueError, match="unknown locator"):
        record_evidence_cache(tmp_path, source, "paper", "all", unknown)
    copied = packet()
    copied["full_text"] = "copied page"
    with pytest.raises(ValueError, match="not cacheable"):
        record_evidence_cache(tmp_path, source, "paper", "all", copied)


@pytest.mark.parametrize(
    "locator",
    [
        "formal method or main result",
        "method/assumptions",
        "exact theorem locator remains unresolved",
        "paper generally",
    ],
)
def test_cache_rejects_placeholder_locators(tmp_path: Path, locator: str) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    evidence = packet()
    evidence["locators"][0]["locator"] = locator
    with pytest.raises(ValueError, match="precise section"):
        record_evidence_cache(tmp_path, source, "paper", "all", evidence)


def test_cache_rejects_missing_out_of_range_or_unreadable_locator_page(tmp_path: Path) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    cases = [(None, "'page' is a required property"), (4, "exceeds"), (3, "unreadable")]
    for page, pattern in cases:
        evidence = packet()
        if page is None:
            del evidence["locators"][0]["page"]
        else:
            evidence["locators"][0]["page"] = page
        with pytest.raises(ValueError, match=pattern):
            record_evidence_cache(tmp_path, source, "paper", "all", evidence)


@pytest.mark.parametrize(
    "locator",
    [
        "pp. 2-3, Sections 2-3",
        "p. 2, Definitions 1-2",
        "p. 2, Assumptions 1-2",
        "p. 2, Condition 1",
        "p. 2, Appendix B.3",
        "p. 2, Corollary 1",
    ],
)
def test_cache_accepts_precise_plural_and_condition_anchors(
    tmp_path: Path, locator: str
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    evidence = packet()
    evidence["locators"][0]["locator"] = locator
    recorded = record_evidence_cache(tmp_path, source, "paper", "all", evidence)
    assert Path(recorded["path"]).is_file()


def test_cache_policy_change_and_corruption_are_misses(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    stored = record_evidence_cache(tmp_path, source, "paper", "all", packet())
    Path(stored["path"]).write_text("not json")
    assert lookup_evidence_cache(tmp_path, source, "paper", "all")["reason"] == "corrupt"
    Path(stored["path"]).write_text(json.dumps(stored["record"]))
    monkeypatch.setattr(evidence_cache, "evidence_policy_digest", lambda: "0" * 64)
    assert lookup_evidence_cache(tmp_path, source, "paper", "all")["hit"] is False


def test_cli_cache_round_trip(tmp_path: Path) -> None:
    source, draft = tmp_path / "paper.pdf", tmp_path / "evidence.json"
    source.write_bytes(b"pdf")
    draft.write_text(json.dumps(packet()))
    runner = CliRunner()
    recorded = runner.invoke(
        cli.app,
        ["record-evidence-cache", str(tmp_path), str(source), "paper", "all", str(draft)],
    )
    assert recorded.exit_code == 0, recorded.output
    found = runner.invoke(
        cli.app, ["lookup-evidence-cache", str(tmp_path), str(source), "paper", "all"]
    )
    assert found.exit_code == 0 and json.loads(found.stdout)["hit"] is True


def test_cache_record_fails_when_immediate_read_back_is_not_a_hit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    monkeypatch.setattr(
        evidence_cache,
        "lookup_evidence_cache",
        lambda *args, **kwargs: {"hit": False, "reason": "corrupt"},
    )
    with pytest.raises(ValueError, match="read-back validation: corrupt"):
        record_evidence_cache(tmp_path, source, "paper", "all", packet())


def test_prepare_generates_managed_footnotes_and_preserves_manual_ones(tmp_path: Path) -> None:
    source = tmp_path / "paper with spaces.pdf"
    source.write_bytes(b"pdf")
    stored = record_evidence_cache(tmp_path, source, "paper", "all", packet())
    report = tmp_path / "reports" / "candidate.md"
    report.parent.mkdir()
    report.write_text(
        "# Report\n\nA claim.[^apa-method-p2] Manual.[^manual]\n\n"
        "[^manual]: Kept by the author.\n\n[^apa-method-p2]: stale generated text.\n"
    )
    result = prepare_report(
        report,
        report_kind="generic",
        evidence_paths=(Path(stored["path"]),),
        publication_path=report,
    )
    assert result.valid
    text = report.read_text()
    assert text.count("[^apa-method-p2]:") == 1
    assert "[^manual]: Kept by the author." in text
    assert "[Original paper][apa-source-" in text
    assert "<../paper with spaces.pdf>" in text


def test_prepare_blocks_unknown_managed_locator_without_removing_existing_text(
    tmp_path: Path,
) -> None:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    stored = record_evidence_cache(tmp_path, source, "paper", "all", packet())
    report = tmp_path / "candidate.md"
    original = "# Report\n\nUnknown.[^apa-not-recorded]\n\n[^apa-not-recorded]: old text.\n"
    report.write_text(original)
    result = prepare_report(report, report_kind="generic", evidence_paths=(Path(stored["path"]),))
    assert not result.valid
    assert any(item.code == "evidence.unknown-locator" for item in result.remaining)
    assert "[^apa-not-recorded]: old text." in report.read_text()
