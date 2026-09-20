from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ai_paper_analysis import markdown_audit
from ai_paper_analysis.markdown_audit import audit_markdown

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("sections", [[1, 2, 2, 3], [2, 1, 3], [1, 2, 3, 4]])
def test_category_sections_reject_duplicates_reordering_and_extras(
    tmp_path: Path, sections: list[int]
) -> None:
    report = tmp_path / "sections.md"
    report.write_text(
        "# Category\n\n" + "\n\n".join(f"## {number}. Section\n\nText." for number in sections),
        encoding="utf-8",
    )
    audit = audit_markdown(report, report_kind="category", full_render=False)
    assert not audit.valid
    assert any("exactly once" in error for error in audit.errors)


def test_portable_paper_report_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markdown_audit, "_full_renderer_errors", lambda path: [])
    monkeypatch.setattr(markdown_audit, "_mermaid_syntax_audit", lambda blocks, **kwargs: ([], []))
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


@pytest.mark.parametrize(
    "fragment",
    [
        "(K)",
        "(N,K)",
        "(N-1,K)",
        "(K^2)",
        "(p_i)",
        "(x/2)",
        r"(p\ge0.5)",
        "([-1,1])",
        "(N(0,1))",
    ],
)
def test_probable_lost_inline_math_delimiters_fail(tmp_path: Path, fragment: str) -> None:
    report = tmp_path / "bare-math.md"
    report.write_text(
        f"# Bare Math\n\n| Item | Value |\n| --- | --- |\n| parameter | {fragment} |\n",
        encoding="utf-8",
    )

    audit = audit_markdown(report)

    assert not audit.valid
    assert any("probable bare mathematics" in error for error in audit.errors)


def test_math_audit_preserves_ordinary_parentheses_and_code(tmp_path: Path) -> None:
    report = tmp_path / "ordinary-parentheses.md"
    report.write_text(
        "# Ordinary Parentheses\n\n"
        "The random setting (Figure 1) uses $K$ variables and links to "
        "[a draft](https://example.com/paper_(draft)).[^x_1]\n\n"
        "| Item | Value |\n"
        "| --- | --- |\n"
        "| panel | (a) |\n"
        "| array shape | `(N,K)` |\n\n"
        "[^x_1]: Synthetic source note.\n",
        encoding="utf-8",
    )

    audit = audit_markdown(report)

    assert audit.valid, audit.errors


def test_long_lr_chain_requires_tb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        markdown_audit,
        "_mermaid_check_records",
        lambda blocks: [
            {
                "line": 3,
                "valid": True,
                "layout": {
                    "current": "LR",
                    "recommended": "TB",
                    "changed": True,
                    "direction_offset": 10,
                    "sizes": {
                        "TB": {"width": 54, "height": 694},
                        "LR": {"width": 582, "height": 70},
                    },
                },
            }
        ],
    )
    report = tmp_path / "graph.md"
    report.write_text(
        "# Graph\n\n```mermaid\nflowchart LR\n"
        "    A --> B\n    B --> C\n    C --> D\n    D --> E\n    E --> F\n    F --> G\n```\n",
        encoding="utf-8",
    )
    audit = audit_markdown(report)
    assert not audit.valid
    assert any("direction should be TB" in error for error in audit.errors)


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
