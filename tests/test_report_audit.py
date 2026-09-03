from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_paper_analysis import cli, markdown_audit
from ai_paper_analysis.cli import app
from ai_paper_analysis.report_audit import audit_category_report, audit_paper_report

FIXTURES = Path(__file__).parent / "fixtures"
TEMPLATES = Path(__file__).parents[1] / "templates"


def _disable_external_renderers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markdown_audit, "_full_renderer_errors", lambda path: [])
    monkeypatch.setattr(markdown_audit, "_mermaid_syntax_audit", lambda blocks: ([], []))


def test_paper_report_audit_reports_structure_not_factual_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_external_renderers(monkeypatch)
    audit = audit_paper_report(FIXTURES / "portable-report.md")

    assert audit.valid, audit.errors
    assert audit.format_status == "structure-valid"
    assert audit.content_status == "complete"


def test_paper_report_cli_accepts_report_only(monkeypatch: pytest.MonkeyPatch) -> None:
    _disable_external_renderers(monkeypatch)
    monkeypatch.setattr(cli, "_ensure_renderer", lambda: None)
    result = CliRunner().invoke(
        app,
        ["audit-paper-report", str(FIXTURES / "portable-report.md")],
    )

    assert result.exit_code == 0, result.output
    assert '"format_status": "structure-valid"' in result.output
    assert '"content_status": "complete"' in result.output


def test_removed_content_ledger_arguments_are_rejected(tmp_path: Path) -> None:
    ledger = tmp_path / "claims.jsonl"
    ledger.write_text("", encoding="utf-8")
    result = CliRunner().invoke(
        app,
        ["audit-paper-report", str(FIXTURES / "portable-report.md"), str(ledger)],
    )
    assert result.exit_code != 0


def test_category_relationship_status_is_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _disable_external_renderers(monkeypatch)
    relationships = tmp_path / "relationships.jsonl"
    relationships.write_text(
        '{"schema_version":"1.0.0","subject_paper_id":"paper:a",'
        '"relation":"extends","object_paper_id":"paper:b",'
        '"source_kind":"paper","locator":"p. 3"}\n',
        encoding="utf-8",
    )

    audit = audit_category_report(TEMPLATES / "category-report.md", relationships)

    assert audit.valid, audit.errors
    assert audit.format_status == "structure-valid"
    assert audit.relationship_valid is True
