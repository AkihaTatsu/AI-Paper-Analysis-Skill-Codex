from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import markdown
import pytest
from markdown_it import MarkdownIt
from typer.testing import CliRunner

from ai_paper_analysis import cli, markdown_audit, report_prepare
from ai_paper_analysis.evidence_cache import record_evidence_cache
from ai_paper_analysis.markdown_audit import AuditContext, audit_markdown
from ai_paper_analysis.report_prepare import prepare_report


def _evidence_packet(tmp_path: Path) -> Path:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    stored = record_evidence_cache(
        tmp_path,
        source,
        "paper",
        "report-preparation-tests",
        {
            "source": {"label": "Paper"},
            "coverage": {
                "complete": True,
                "page_count": 1,
                "page_ranges": [[1, 1]],
                "unreadable_pages": [],
            },
            "locators": [
                {"id": "apa-method-p1", "locator": "p. 1, Methods", "page": 1},
                {"id": "apa-result-p1", "locator": "p. 1, Results", "page": 1},
            ],
            "facts": [
                {
                    "kind": "method",
                    "summary": "The method has one stage.",
                    "locator_ids": ["apa-method-p1"],
                },
                {
                    "kind": "result",
                    "summary": "The result reports one value.",
                    "locator_ids": ["apa-result-p1"],
                },
            ],
            "formulas": [],
            "limitations": [],
        },
    )
    return Path(stored["path"])


def _paper_report(section_lines: dict[int, str]) -> str:
    sections = "".join(
        f"\n## {number}. Section {number}\n\n{section_lines.get(number, 'Content.')}\n"
        for number in range(1, 8)
    )
    return "# Report\n" + sections


@pytest.mark.parametrize("render", [False, True])
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("kind,count", [("paper", 7), ("category", 3)])
def test_cli_prepare_renders_prepared_bytes_with_optional_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, render: bool, dry_run: bool,
    kind: str, count: int,
) -> None:
    report = tmp_path / "candidate.md"
    sections = "".join(f"\n## {i}. Section\n" for i in range(1, count + 1))
    original = "# Report\nA line.\nA continuation.\n" + sections
    report.write_text(original)
    observed: list[str] = []
    monkeypatch.setattr(
        markdown_audit,
        "_full_renderer_errors",
        lambda path: observed.append(path.read_text()) or [],
    )
    command = ["prepare-report", str(report), "--report-kind", kind]
    if render:
        command.append("--render")
    if dry_run:
        command.append("--dry-run")
    result = CliRunner().invoke(cli.app, command)
    assert result.exit_code == 0, result.exception
    payload = json.loads(result.stdout)
    prepared = "# Report\n\nA line. A continuation.\n" + sections
    assert observed == ([prepared] if render else [])
    assert report.read_text() == (original if dry_run else prepared)
    assert payload["written"] is (not dry_run)
    stage = next(item for item in payload["stages"] if item["name"] == "renderer")
    assert stage["status"] == ("passed" if render else "pending")


def test_cli_prepare_exposes_render_failure_before_semantic_review(tmp_path, monkeypatch) -> None:
    report = tmp_path / "candidate.md"
    report.write_text("# Report\n\n## 1. First\n\n## 2. Second\n\n## 3. Third\n")
    monkeypatch.setattr(markdown_audit, "_full_renderer_errors", lambda path: ["invalid formula"])
    result = CliRunner().invoke(
        cli.app, ["prepare-report", str(report), "--report-kind", "category", "--render"]
    )
    payload = json.loads(result.stdout)
    assert result.exit_code == 1 and payload["valid"] is False
    assert any("invalid formula" in item["message"] for item in payload["remaining"])
    stages = {stage["name"]: stage["status"] for stage in payload["stages"]}
    assert stages["renderer"] == "failed" and stages["semantic-review"] == "skipped"


def test_safe_fixes_dry_run_idempotence_and_unicode_path(tmp_path: Path) -> None:
    report = tmp_path / "含 空格 报告.md"
    original = "# Report\r\nText with one space. \r\nA soft continuation.\r\n\r\n\r\n"
    report.write_bytes(original.encode("utf-8"))
    preview = prepare_report(report, report_kind="generic", dry_run=True)
    assert preview.valid and preview.changed and not preview.written
    assert report.read_bytes() == original.encode("utf-8")
    result = prepare_report(report, report_kind="generic")
    assert result.valid and result.written
    assert report.read_text() == "# Report\n\nText with one space. A soft continuation.\n"
    second = prepare_report(report, report_kind="generic")
    assert second.valid and not second.changed and second.fixes == ()
    assert all(stage.elapsed_seconds >= 0 for stage in result.stages)
    assert result.stages[-1].status == "skipped"


def test_bare_urls_are_autolinked_without_touching_links_definitions_or_code(
    tmp_path: Path,
) -> None:
    report = tmp_path / "urls.md"
    report.write_text(
        "# URLs\n\n"
        "| Kind | Value |\n| --- | --- |\n"
        "| Bare | https://example.test/paper |\n"
        "| Link | [paper](https://example.test/linked) |\n\n"
        "`https://example.test/code`\n\n"
        "[source]: https://example.test/reference\n"
    )
    result = prepare_report(report, report_kind="generic")
    assert result.valid
    text = report.read_text()
    assert "[https://example.test/paper](https://example.test/paper)" in text
    assert "[paper](https://example.test/linked)" in text
    assert "`https://example.test/code`" in text
    assert "[source]: https://example.test/reference" in text


def test_code_containers_hardbreaks_math_and_paragraph_boundaries_are_preserved(
    tmp_path: Path,
) -> None:
    report = tmp_path / "protected.md"
    protected = (
        "A hard break.  \nRemains separate.\n\n"
        "A `code\nspan` is preserved.\n\n"
        "> quoted\n> continuation  \n\n"
        "- listed\n  continuation\n\n"
        "~~~text\ncode   \n\n\nunchanged\n~~~\n\n"
        "$$\nx +\n y\n$$\n\n"
        "A first paragraph.\n\nA second paragraph.\n"
    )
    report.write_text("# Protected\n\n" + protected)
    prepare_report(report, report_kind="generic")
    assert report.read_text() == "# Protected\n\n" + protected


def test_explicit_math_pairs_only_and_no_bare_math_guessing(tmp_path: Path) -> None:
    report = tmp_path / "math.md"
    report.write_text(
        "# Math\n\nExplicit \\(x + y\\) becomes inline.\n\n"
        "\\[\nx + y = z\n\\]\n\n"
        "Code `\\(x\\)` stays.\n\nA bare (K) stays.\n\nAn unmatched \\(z stays.\n"
    )
    result = prepare_report(report, report_kind="generic")
    text = report.read_text()
    assert "$x + y$" in text and "$$\nx + y = z\n$$" in text
    assert "`\\(x\\)`" in text and "A bare (K)" in text and "unmatched \\(z" in text
    assert not result.valid
    assert any("bare mathematics" in item.message for item in result.remaining)


def test_legal_tex_row_spacing_is_not_mistaken_for_display_delimiter(tmp_path: Path) -> None:
    report = tmp_path / "row-spacing.md"
    report.write_text("# Math\n\n$$\n\\begin{aligned}a&=b\\\\[2pt]c&=d\\end{aligned}\n$$\n")
    result = prepare_report(report, report_kind="generic")
    assert result.valid, result.remaining


def test_prepare_normalizes_mermaid_html_line_breaks(tmp_path: Path, monkeypatch) -> None:
    report = tmp_path / "diagram.md"
    report.write_text("# Graph\n\n```mermaid\nflowchart LR\n A[one<br/>two] --> B\n```\n")

    def checker(blocks):
        return [
            {
                "line": line,
                "valid": True,
                "message": "",
                "parser_line": None,
                "layout": {
                    "estimated": True,
                    "current": "LR",
                    "recommended": "LR",
                    "changed": False,
                    "direction_offset": code.index("LR"),
                    "direction_length": 2,
                    "sizes": {
                        "TB": {"width": 100, "height": 200},
                        "LR": {"width": 200, "height": 100},
                    },
                    "node_count": 2,
                    "has_subgraph": False,
                },
            }
            for line, code in blocks
        ]

    monkeypatch.setattr(markdown_audit, "_mermaid_check_records", checker)
    result = prepare_report(report, report_kind="generic")
    assert result.valid
    assert "one two" in report.read_text()
    assert any(fix["code"] == "mermaid-label-line-break" for fix in result.fixes)


def test_prepare_quotes_mermaid_labels_with_parentheses_and_pipes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "diagram.md"
    report.write_text(
        "# Graph\n\n```mermaid\nflowchart LR\n A[ELBO (Eq. 3)] --> B{train | stop}\n```\n"
    )
    monkeypatch.setattr(
        markdown_audit,
        "_mermaid_check_records",
        lambda blocks: [
            {
                "line": line,
                "valid": True,
                "message": "",
                "parser_line": None,
                "layout": {
                    "estimated": True,
                    "current": "LR",
                    "recommended": "LR",
                    "changed": False,
                    "direction_offset": code.index("LR"),
                    "direction_length": 2,
                    "sizes": {
                        "TB": {"width": 100, "height": 200},
                        "LR": {"width": 200, "height": 100},
                    },
                    "node_count": 2,
                    "has_subgraph": False,
                },
            }
            for line, code in blocks
        ],
    )
    result = prepare_report(report, report_kind="generic")
    assert result.valid
    assert 'A["ELBO (Eq. 3)"]' in report.read_text()
    assert 'B{"train | stop"}' in report.read_text()
    assert sum(
        fix.get("count", 0)
        for fix in result.fixes
        if fix["code"] == "mermaid-label-quotes"
    ) == 2


def test_prepare_repairs_table_footnote_ordered_list_and_accidental_spaces(tmp_path: Path) -> None:
    report = tmp_path / "deterministic.md"
    (tmp_path / "paper.pdf").write_bytes(b"pdf")
    report.write_text(
        "# Report\n\n| A | B |\n| --- | --- |\n| one | two |[^source]\n\n"
        "1. first \n\n2. second\t\n\n[^source]: paper.pdf\n"
    )
    result = prepare_report(report, report_kind="generic")
    assert result.valid
    text = report.read_text()
    assert "| one | two [^source] |" in text
    assert "1. first\n2. second\n" in text
    codes = {fix["code"] for fix in result.fixes}
    assert {"table-trailing-footnote", "ordered-list-spacing", "trailing-whitespace"} <= codes


def test_prepare_reports_resolved_literal_that_remains(tmp_path: Path) -> None:
    report = tmp_path / "literal.md"
    report.write_text("# Report\n\nRemove this stale sentence.\n")
    result = prepare_report(
        report,
        report_kind="generic",
        forbidden_literals=("stale sentence", "already gone"),
    )
    assert not result.valid
    assert [item.code for item in result.remaining] == ["review.residual-literal"]


def test_coverage_matrix_requires_known_references_in_the_mapped_section(
    tmp_path: Path,
) -> None:
    evidence = _evidence_packet(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(
        _paper_report(
            {
                2: "Method claim.[^apa-method-p1]",
                6: "Result claim.[^apa-result-p1]",
            }
        )
    )
    matrix = tmp_path / "coverage.json"
    matrix.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_kind": "paper",
                "rows": [
                    {
                        "id": "method",
                        "object_kind": "module",
                        "report_section": 2,
                        "report_anchor": "Method claim.",
                        "required_locator_ids": ["apa-method-p1"],
                    },
                    {
                        "id": "result",
                        "object_kind": "experiment",
                        "report_section": 6,
                        "report_anchor": "Result claim.",
                        "required_locator_ids": ["apa-result-p1"],
                    },
                ],
            }
        )
    )
    result = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        coverage_matrix=matrix,
    )
    assert result.valid
    assert next(stage for stage in result.stages if stage.name == "coverage").status == "passed"

    report.write_text(
        _paper_report(
            {
                2: "Result claim.[^apa-result-p1]",
                7: "[^apa-method-p1]: A definition cannot satisfy coverage.",
            }
        )
    )
    result = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        coverage_matrix=matrix,
    )
    assert not result.valid
    assert {item.code for item in result.remaining} >= {
        "coverage.missing-anchor",
        "coverage.wrong-anchor-section",
    }


def test_coverage_anchor_requires_evidence_in_the_same_passage(tmp_path: Path) -> None:
    evidence = _evidence_packet(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(
        _paper_report(
            {2: "Method claim without its marker.\n\nAnother claim.[^apa-method-p1]"}
        )
    )
    matrix = tmp_path / "coverage.json"
    matrix.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_kind": "paper",
                "rows": [
                    {
                        "id": "method",
                        "object_kind": "module",
                        "report_section": 2,
                        "report_anchor": "Method claim without its marker.",
                        "required_locator_ids": ["apa-method-p1"],
                    }
                ],
            }
        )
    )
    result = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        coverage_matrix=matrix,
    )
    assert not result.valid
    assert "coverage.missing-near-reference" in {item.code for item in result.remaining}


def test_review_issue_file_checks_literals_and_section_bound_evidence(tmp_path: Path) -> None:
    evidence = _evidence_packet(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(
        _paper_report({5: "Old claim.[^apa-result-p1]", 6: "Result explanation."})
    )
    issues = tmp_path / "issues.json"
    issues.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_kind": "paper",
                "baseline_sha256": "0" * 64,
                "issues": [
                    {
                        "id": "REV-1",
                        "classification": "semantic",
                        "report_locator": "Section 6 result explanation",
                        "source_locator": "p. 1, Results",
                        "impact": "The explanation uses stale wording and lacks its citation.",
                        "repair_condition": "Replace the wording and cite the result in section 6.",
                        "obsolete_literals": ["Old claim"],
                        "required_evidence": [
                            {"locator_id": "apa-result-p1", "report_section": 6}
                        ],
                    }
                ],
            }
        )
    )
    failed = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        review_issues=issues,
    )
    assert not failed.valid
    assert {item.code for item in failed.remaining} >= {
        "review.residual-literal",
        "review.wrong-section",
    }

    report.write_text(
        _paper_report({5: "Updated context.", 6: "Result explanation.[^apa-result-p1]"})
    )
    passed = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        review_issues=issues,
    )
    assert passed.valid
    assert next(
        stage for stage in passed.stages if stage.name == "review-residual"
    ).status == "passed"


def test_review_issue_exact_patch_is_guarded_applied_and_idempotent(tmp_path: Path) -> None:
    evidence = _evidence_packet(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(_paper_report({6: "Old result."}))
    baseline = hashlib.sha256(report.read_bytes()).hexdigest()
    issues = tmp_path / "issues.json"
    issues.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_kind": "paper",
                "baseline_sha256": baseline,
                "issues": [
                    {
                        "id": "REV-1",
                        "classification": "semantic",
                        "report_locator": "Section 6 result",
                        "source_locator": "p. 1, Results",
                        "impact": "The result is stale.",
                        "repair_condition": "Use the supported result.",
                        "obsolete_literals": [],
                        "required_evidence": [
                            {"locator_id": "apa-result-p1", "report_section": 6}
                        ],
                        "automatic_patch": {
                            "old_text": "Old result.",
                            "new_text": "Supported result.[^apa-result-p1]",
                        },
                    }
                ],
            }
        )
    )
    first = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        review_issues=issues,
    )
    assert first.valid and first.written
    assert "Supported result.[^apa-result-p1]" in report.read_text()
    assert any(item["code"] == "review-automatic-patch" for item in first.fixes)
    second = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        review_issues=issues,
    )
    assert second.valid
    assert any(
        item["code"] == "review-automatic-patch-already-applied" for item in second.fixes
    )

    report.write_text("Preface.\n" + _paper_report({6: "Old result."}))
    mismatch = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        review_issues=issues,
        dry_run=True,
    )
    assert not mismatch.valid
    assert "review.patch-baseline-mismatch" in {item.code for item in mismatch.remaining}


def test_review_patches_follow_generated_footnotes_and_rebind_changed_anchors(
    tmp_path: Path,
) -> None:
    evidence = _evidence_packet(tmp_path)
    report = tmp_path / "report.md"
    report.write_text(
        _paper_report(
            {
                1: "| Object | Meaning | Evidence |\n| --- | --- | --- |\n"
                "| Term old | Initial wording | [^apa-result-p1] |",
                2: "Intro.",
            }
        )
    )
    prepared = prepare_report(report, report_kind="paper", evidence_paths=(evidence,))
    assert prepared.valid
    baseline = hashlib.sha256(report.read_bytes()).hexdigest()
    old_footnote = "[^apa-result-p1]: [Paper][apa-source-"
    generated = next(
        line for line in report.read_text().splitlines() if line.startswith(old_footnote)
    )
    matrix = tmp_path / "coverage.json"
    matrix.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_kind": "paper",
                "rows": [
                    {
                        "id": "term",
                        "object_kind": "term",
                        "report_section": 1,
                        "report_anchor": "Term old",
                        "required_locator_ids": ["apa-result-p1"],
                    }
                ],
            }
        )
    )
    issues = tmp_path / "issues.json"
    issues.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "report_kind": "paper",
                "baseline_sha256": baseline,
                "issues": [
                    {
                        "id": "REV-anchor",
                        "classification": "semantic",
                        "report_locator": "Section 1 table",
                        "source_locator": "p. 1, Results",
                        "impact": "The term is imprecise.",
                        "repair_condition": "Rename it.",
                        "obsolete_literals": ["Term old"],
                        "required_evidence": [],
                        "automatic_patch": {
                            "old_text": "| Term old | Initial wording | [^apa-result-p1] |",
                            "new_text": "| Term new | Precise wording | [^apa-result-p1] |",
                        },
                    },
                    {
                        "id": "REV-append",
                        "classification": "semantic",
                        "report_locator": "Section 2 introduction",
                        "source_locator": "p. 1, Results",
                        "impact": "The introduction needs an explanation.",
                        "repair_condition": "Append the explanation.",
                        "obsolete_literals": [],
                        "required_evidence": [],
                        "automatic_patch": {
                            "old_text": "Intro.",
                            "new_text": "Intro.\n\nPlain explanation.",
                        },
                    },
                    {
                        "id": "REV-footnote",
                        "classification": "deterministic",
                        "report_locator": "Generated result footnote",
                        "source_locator": "p. 1, Results",
                        "impact": "The locator needs more detail.",
                        "repair_condition": "Add the exact locator.",
                        "obsolete_literals": [],
                        "required_evidence": [],
                        "automatic_patch": {
                            "old_text": generated,
                            "new_text": generated[:-1] + "; exact locator.",
                        },
                    },
                ],
            }
        )
    )

    first = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        coverage_matrix=matrix,
        review_issues=issues,
    )
    assert first.valid
    text = report.read_text()
    assert "Term new" in text and "Plain explanation." in text
    assert generated[:-1] + "; exact locator." in text
    assert not any(item.code == "review.residual-literal" for item in first.remaining)

    second = prepare_report(
        report,
        report_kind="paper",
        evidence_paths=(evidence,),
        coverage_matrix=matrix,
        review_issues=issues,
    )
    assert second.valid and not second.changed


def test_basic_failures_still_collect_mermaid_but_do_not_launch_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "incomplete.md"
    report.write_text("# Draft\n\n```mermaid\nflowchart LR\n A --> B\n```\n")

    checked: list[object] = []

    def mermaid(blocks):
        checked.extend(blocks)
        return [{
            "line": 3,
            "valid": True,
            "message": "",
            "parser_line": None,
            "layout": {
                "estimated": True,
                "current": "LR",
                "recommended": "LR",
                "changed": False,
                "direction_offset": 10,
                "direction_length": 2,
                "sizes": {
                    "TB": {"width": 100, "height": 200},
                    "LR": {"width": 200, "height": 100},
                },
                "node_count": 2,
                "has_subgraph": False,
            },
        }]

    def forbidden(*args, **kwargs):
        pytest.fail("Basic failure must not invoke the full renderer")

    monkeypatch.setattr(markdown_audit, "_mermaid_check_records", mermaid)
    monkeypatch.setattr(markdown_audit, "_full_renderer_errors", forbidden)
    result = prepare_report(report)
    assert not result.valid
    statuses = {stage.name: stage.status for stage in result.stages}
    assert statuses["basic"] == "failed" and checked
    assert statuses["mermaid"] == "passed" and statuses["renderer"] == "skipped"


def test_publication_path_resolves_encoded_space_link_and_reference_link(tmp_path: Path) -> None:
    source = tmp_path / "draft" / "draft.md"
    source.parent.mkdir()
    final = tmp_path / "published" / "report.md"
    final.parent.mkdir()
    (final.parent / "论文 文档.pdf").write_bytes(b"pdf")
    source.write_text(
        "# Report\n\n[Source][paper] and [inline](<论文 文档.pdf>).\n\n"
        "[paper]: %E8%AE%BA%E6%96%87%20%E6%96%87%E6%A1%A3.pdf\n"
    )
    assert prepare_report(source, report_kind="generic", publication_path=final).valid
    assert not audit_markdown(source).valid


def test_concurrent_edit_cannot_be_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "report.md"
    report.write_text("# Before\nNeeds spacing.\n")
    original_audit = report_prepare.audit_markdown

    def edited_during_audit(*args, **kwargs):
        result = original_audit(*args, **kwargs)
        report.write_text("# Newer content\n")
        return result

    monkeypatch.setattr(report_prepare, "audit_markdown", edited_during_audit)
    with pytest.raises(ValueError, match="changed during analysis"):
        prepare_report(report, report_kind="generic")
    assert report.read_text() == "# Newer content\n"
    assert not list(tmp_path.glob(".*.updating"))


def test_renderer_context_reuses_bytes_and_invalidates_on_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "category.md"
    report.write_text("# Category\n\n## 1. First\n\n## 2. Second\n\n## 3. Third\n")
    calls: list[Path] = []
    monkeypatch.setattr(
        markdown_audit, "_full_renderer_errors", lambda path: calls.append(path) or []
    )
    fingerprint = ["tools-v1"]
    monkeypatch.setattr(markdown_audit, "_tool_fingerprint", lambda: fingerprint[0])
    context = AuditContext()
    assert prepare_report(report, report_kind="category", context=context, render=True).valid
    assert audit_markdown(report, report_kind="category", context=context).valid
    assert len(calls) == 1
    report.write_text(report.read_text() + "\nMore prose.\n")
    assert audit_markdown(report, report_kind="category", context=context).valid
    assert len(calls) == 2
    fingerprint[0] = "tools-v2"
    assert audit_markdown(report, report_kind="category", context=context).valid
    assert len(calls) == 3


def test_replace_failure_preserves_original_and_removes_temporary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "locked.md"
    original = b"# Locked\nNeeds spacing.\n"
    report.write_bytes(original)

    def denied(*args, **kwargs):
        raise PermissionError("destination is in use")

    monkeypatch.setattr(markdown_audit.os, "replace", denied)
    with pytest.raises(PermissionError):
        prepare_report(report, report_kind="generic")
    assert report.read_bytes() == original
    assert not list(tmp_path.glob(".*.updating"))


def test_prepare_defers_renderer_until_explicit_final_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "category.md"
    report.write_text("# Category\n\n## 1. First\n\n## 2. Second\n\n## 3. Third\n")
    calls: list[Path] = []
    monkeypatch.setattr(
        markdown_audit, "_full_renderer_errors", lambda path: calls.append(path) or []
    )
    result = prepare_report(report, report_kind="category")
    assert result.valid and calls == []
    assert next(stage for stage in result.stages if stage.name == "renderer").status == "pending"
    assert audit_markdown(report, report_kind="category").valid
    assert calls == [report]


def test_table_math_pipes_restore_cells_with_explicit_single_bars_and_are_idempotent(
    tmp_path: Path,
) -> None:
    report = tmp_path / "公式 表.md"
    expressions = [
        r"$C\in\mathbb R^{|S|}$、$C^\top$",
        r"$|\mathcal{TS}(G_\theta)|$、$M_2$",
        r"$|G_\theta|$",
    ]
    original = "# Formula table\n\n| Symbol | Meaning |\n| --- | --- |\n" + "".join(
        f"| {expression} | Meaning {index} |\n" for index, expression in enumerate(expressions)
    )
    report.write_text(original)
    preview = prepare_report(report, report_kind="generic", dry_run=True)
    assert preview.valid and preview.changed and not preview.written
    assert report.read_text() == original
    assert [fix["count"] for fix in preview.fixes] == [2, 2, 2]
    prepared = prepare_report(report, report_kind="generic")
    assert prepared.valid and prepared.written
    expected = original
    for expression in expressions:
        expected = expected.replace(expression, expression.replace("|", r"\vert{}"))
    assert report.read_text() == expected

    # Real GFM table tokenization must deliver both complete cells, passing the
    # explicit single-bar command to the math parser without macro-name joining.
    tokens = MarkdownIt("commonmark").enable("table").parse(expected)
    cells = [token.content for token in tokens if token.type == "inline"]
    assert cells == [
        "Formula table",
        "Symbol",
        "Meaning",
        expressions[0].replace("|", r"\vert{}"),
        "Meaning 0",
        expressions[1].replace("|", r"\vert{}"),
        "Meaning 1",
        expressions[2].replace("|", r"\vert{}"),
        "Meaning 2",
    ]
    assert sum(token.type == "td_open" for token in tokens) == 6
    second = prepare_report(report, report_kind="generic")
    assert second.valid and not second.changed and second.fixes == ()


@pytest.mark.parametrize(
    "protected",
    [
        "Ordinary $|x|$ prose.\n",
        "| $|x|$ | not a table without a separator row |\n",
        "```md\n| Symbol | Meaning |\n| --- | --- |\n| $|x|$ | code |\n```\n",
        "    | Symbol | Meaning |\n    | --- | --- |\n    | $|x|$ | code |\n",
        "> | Symbol | Meaning |\n> | --- | --- |\n> | $|x|$ | quote |\n",
        "- | Symbol | Meaning |\n  | --- | --- |\n  | $|x|$ | list |\n",
        "$$\n| Symbol | Meaning |\n| --- | --- |\n| $|x|$ | display |\n$$\n",
        "| Symbol | Meaning |\n| --- | --- |\n| `$|x|$` | code |\n",
        "| Symbol | Meaning |\n| --- | --- |\n| `` `$|x|$` `` | code |\n",
        "| Symbol | Meaning |\n| --- | --- |\n| \\$|x|\\$ | escaped dollars |\n",
        "| Symbol | Meaning |\n| --- | --- |\n| $\\vert{}x\\vert{}$ | single bars |\n",
        "| Symbol | Meaning |\n| --- | --- |\n| $\\Vert{}x\\Vert{}$ | double bars |\n",
        "| Symbol | Meaning |\n| --- | --- |\n| $$x$$ | no damaged separators |\n",
    ],
)
def test_table_math_pipe_repair_preserves_non_target_content(protected: str) -> None:
    result, fixes, diagnostics = report_prepare._safe_table_math_pipes(protected)
    assert result == protected
    assert fixes == diagnostics == []


def test_table_math_pipe_repair_skips_code_spans_but_repairs_other_math() -> None:
    original = (
        "Symbol | Meaning\n--- | ---\n"
        r"`code $x$` and $\$a|b$ | explanation"
        "\n"
    )
    result, fixes, diagnostics = report_prepare._safe_table_math_pipes(original)
    assert result == original.replace(r"a|b", r"a\vert{}b")
    assert fixes == [{"code": "table-inline-math-pipes", "line": 3, "count": 1}]
    assert diagnostics == []


@pytest.mark.parametrize(
    "row",
    [
        r"| $x|y | unmatched |",
        r"| $x|y$ and $z | unmatched |",
        r"| $$|x|$$ | double dollars |",
        r"| $ |x| $ | spaces at delimiters |",
        r"| $a|b$ | extra | cell |",
        r"| $a|b$ |",
        r"| [link]($a|b$) | destination |",
        r"| $a`code`|b$ | overlapping syntax |",
        r"| $\|x\|$ | escaped pipe meaning needs review |",
        r"| $\text{a|b}$ | a text separator is not a math bar |",
        r"| $\begin{array}{c|c}a&b\end{array}$ | array column syntax |",
    ],
)
def test_ambiguous_table_math_pipes_are_diagnosed_without_guessing(row: str) -> None:
    original = "| Symbol | Meaning |\n| --- | --- |\n" + row + "\n"
    result, fixes, diagnostics = report_prepare._safe_table_math_pipes(original)
    assert result == original and fixes == []
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "table.math-pipe-ambiguous"
    assert diagnostics[0].line == 3


def test_prepare_exposes_ambiguous_pipe_diagnostic_as_remaining_failure(tmp_path: Path) -> None:
    report = tmp_path / "ambiguous.md"
    original = "# Ambiguous\n\n| Symbol | Meaning |\n| --- | --- |\n| $a|b$ |\n"
    report.write_text(original)
    result = prepare_report(report, report_kind="generic")
    assert not result.valid and not result.changed and not result.written
    assert report.read_text() == original
    assert next(stage for stage in result.stages if stage.name == "prepare").status == "failed"
    assert any(item.code == "table.math-pipe-ambiguous" for item in result.remaining)


def test_prepare_keeps_existing_escaped_pipe_and_requires_intent_review(tmp_path: Path) -> None:
    report = tmp_path / "existing-norm.md"
    original = "# Norm\n\n| Symbol | Meaning |\n| --- | --- |\n| $\\|x\\|$ | norm |\n"
    report.write_text(original)
    result = prepare_report(report, report_kind="generic")
    assert not result.valid and not result.changed
    assert report.read_text() == original
    assert any("renderer-dependent" in item.message for item in result.remaining)


def test_unpaired_middle_bar_is_repaired_only_in_unpaired_display_math() -> None:
    original = (
        "$$\nA \\middle| B\n$$\n\n"
        "$$\n\\left(A \\middle| B\\right)\n$$\n\n"
        "```tex\n$$\nA \\middle| B\n$$\n```\n"
    )
    repaired, fixes = report_prepare._safe_unpaired_middle_bars(original)
    assert repaired == original.replace(r"A \middle| B", r"A \vert{} B", 1)
    assert fixes == [{"code": "unpaired-middle-bar", "line": 1, "count": 1}]


def _python_math_table(source: str) -> tuple[list[str], list[int]]:
    html = markdown.markdown(
        source,
        extensions=["tables", "pymdownx.arithmatex"],
        extension_configs={"pymdownx.arithmatex": {"generic": True}},
    )
    root = ET.fromstring("<root>" + html + "</root>")
    expressions = [
        "".join(span.itertext())[2:-2]
        for span in root.iter("span")
        if span.get("class") == "arithmatex"
    ]
    columns = [len(row.findall("td")) for row in root.findall("./table/tbody/tr")]
    return expressions, columns


def _math_pipe_render_fixture() -> tuple[str, list[str], list[str]]:
    original_tex = [
        r"C\in\mathbb R^{|S|}",
        r"C^\top",
        r"|\mathcal{TS}(G_\theta)|",
        r"M_2",
        r"|G_\theta|",
    ]
    source = (
        "| Symbol | Meaning |\n| --- | --- |\n"
        f"| ${original_tex[0]}$、${original_tex[1]}$ | vector |\n"
        f"| ${original_tex[2]}$、${original_tex[3]}$ | closure |\n"
        f"| ${original_tex[4]}$ | edges |\n"
    )
    prepared, fixes, diagnostics = report_prepare._safe_table_math_pipes(source)
    assert len(fixes) == 3 and not diagnostics
    return prepared, original_tex, [tex.replace("|", r"\vert{}") for tex in original_tex]


def test_python_arithmatex_table_path_preserves_explicit_single_bars() -> None:
    prepared, _, expected_tex = _math_pipe_render_fixture()
    expressions, columns = _python_math_table(prepared)
    assert columns == [2, 2, 2]
    assert expressions == expected_tex
    assert all(r"\|" not in tex for tex in expressions)
    # The previous Markdown-only escape survives arithmatex as a TeX norm.
    unsafe = prepared.replace(r"\vert{}", r"\|")
    unsafe_math, _ = _python_math_table(unsafe)
    assert unsafe_math != expected_tex and any(r"\|" in tex for tex in unsafe_math)


def test_both_real_markdown_math_paths_render_the_original_single_bar_semantics() -> None:
    renderer_root = Path(os.environ.get("APA_RENDERER_ROOT", Path(__file__).parents[1]))
    if not (renderer_root / "node_modules" / "markdown-it-texmath").exists():
        pytest.skip("Requires existing renderer dependencies; run in the report-rendering job")
    node = shutil.which("node")
    assert node is not None, "Configured renderer dependencies require Node"
    prepared, original_tex, expected_tex = _math_pipe_render_fixture()
    python_math, columns = _python_math_table(prepared)
    assert python_math == expected_tex and columns == [2, 2, 2]
    script = r"""
const fs = require('node:fs');
const {createRequire} = require('node:module');
const {join} = require('node:path');
const load = createRequire(join(process.argv[1], 'package.json'));
const katex = load('katex');
const md = load('markdown-it')().use(load('markdown-it-texmath'), {
  engine: katex, delimiters: 'dollars', katexOptions: {throwOnError: true}
});
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const tokens = md.parse(input.source, {});
const math = tokens.flatMap(token => (token.children || [])
  .filter(child => child.type === 'math_inline').map(child => child.content));
md.renderer.render(tokens, md.options, {});
function canonicalMathML(tex) {
  return katex.renderToString(tex, {output: 'mathml', throwOnError: true})
    .replace(/<annotation\b[^>]*>[\s\S]*?<\/annotation>/g, '')
    .replace(/<mrow><\/mrow>/g, '');
}
process.stdout.write(JSON.stringify({
  math, cells: tokens.filter(token => token.type === 'td_open').length,
  original: input.original.map(canonicalMathML),
  javascript: math.map(canonicalMathML),
  python: input.python.map(canonicalMathML)
}));
"""
    completed = subprocess.run(
        [node, "-e", script, str(renderer_root)],
        input=json.dumps({"source": prepared, "original": original_tex, "python": python_math}),
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    result = json.loads(completed.stdout)
    assert result["cells"] == 6 and result["math"] == expected_tex
    assert result["original"] == result["javascript"] == result["python"]
    assert any("∣" in mathml for mathml in result["original"])
    assert all("∥" not in mathml for mathml in result["javascript"] + result["python"])
