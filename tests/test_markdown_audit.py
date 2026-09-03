from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai_paper_analysis import markdown_audit
from ai_paper_analysis.markdown_audit import audit_markdown

FIXTURES = Path(__file__).parent / "fixtures"


def test_portable_paper_report_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markdown_audit, "_full_renderer_errors", lambda path: [])
    monkeypatch.setattr(markdown_audit, "_mermaid_syntax_audit", lambda blocks: ([], []))
    audit = audit_markdown(FIXTURES / "portable-report.md", report_kind="paper")
    assert audit.valid, audit.errors
    assert audit.display_formula_count == 1
    assert audit.mermaid_count == 1


def test_unbalanced_math_and_raw_html_fail(tmp_path: Path) -> None:
    report = tmp_path / "bad.md"
    report.write_text(
        "# Bad\n\nA broken $formula and <span>raw HTML</span>.\n",
        encoding="utf-8",
    )
    audit = audit_markdown(report)
    assert not audit.valid
    assert any("unbalanced" in error for error in audit.errors)
    assert any("raw HTML" in error for error in audit.errors)


def test_complex_lr_graph_requires_tb(tmp_path: Path) -> None:
    report = tmp_path / "graph.md"
    report.write_text(
        "# Graph\n\n```mermaid\nflowchart LR\n"
        "    A --> B\n    B --> C\n    C --> D\n    D --> E\n    E --> F\n    F --> G\n```\n",
        encoding="utf-8",
    )
    audit = audit_markdown(report)
    assert not audit.valid
    assert any("too complex" in error for error in audit.errors)


def test_official_mermaid_syntax_error_is_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "invalid-mermaid.md"
    report.write_text(
        "# Graph\n\n```mermaid\nflowchart TB\n    A -- B\n```\n",
        encoding="utf-8",
    )
    parser_output = {
        "results": [
            {
                "line": 3,
                "valid": False,
                "message": "Parse error on line 3",
                "parser_line": 3,
            }
        ]
    }
    monkeypatch.setattr(markdown_audit.shutil, "which", lambda executable: "/usr/bin/node")
    monkeypatch.setattr(
        markdown_audit.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(parser_output),
            stderr="",
        ),
    )

    audit = audit_markdown(report)

    assert not audit.valid
    assert any("invalid Mermaid syntax" in error for error in audit.errors)


def test_unavailable_mermaid_parser_is_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "valid-mermaid.md"
    report.write_text(
        "# Graph\n\n```mermaid\nflowchart TB\n    A --> B\n```\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(markdown_audit.shutil, "which", lambda executable: None)

    audit = audit_markdown(report)

    assert not audit.valid
    assert any("syntax check unavailable" in error for error in audit.errors)
