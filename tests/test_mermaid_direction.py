from __future__ import annotations

import re

import pytest
from typer.testing import CliRunner

from ai_paper_analysis import cli, markdown_audit
from ai_paper_analysis.markdown_audit import fix_mermaid_direction


def records_for(blocks):
    """Controlled checker responses to exercise source editing independently of layout."""
    records = []
    for line, code in blocks:
        record = {"line": line, "valid": True, "message": "", "parser_line": None}
        if "sequenceDiagram" in code:
            record["layout"] = {"skipped": "Not a flowchart"}
        elif "BROKEN" in code:
            record["layout_error"] = "Unsupported fixture"
        else:
            match = re.search(r"(?:flowchart|graph)[ \t]+(TB|TD|LR)\b", code)
            declaration = re.search(r"(?:flowchart|graph)", code)
            assert declaration
            current = match[1] if match else None
            record["layout"] = {
                "estimated": True,
                "current": current,
                "recommended": "LR",
                "changed": current != "LR",
                "direction_offset": len(
                    code[: match.start(1) if match else declaration.end()].encode("utf-16-le")
                )
                // 2,
                "direction_length": len(current or ""),
                "sizes": {"TB": {"width": 500, "height": 100}, "LR": {"width": 100, "height": 500}},
                "node_count": 10,
                "has_subgraph": False,
            }
        records.append(record)
    return records


@pytest.fixture(autouse=True)
def controlled_checker(monkeypatch):
    monkeypatch.setattr(markdown_audit, "_mermaid_check_records", records_for)


@pytest.mark.parametrize(
    "prefix,opening,closing",
    [
        ("", "```mermaid", "```"),
        ("   ", "   ~~~~mermaid", "   ~~~~"),
        ("> ", "> ```mermaid", "> ```"),
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_fix_preserves_source_and_is_idempotent(tmp_path, prefix, opening, closing, newline):
    report = tmp_path / "report.md"
    text = newline.join(
        [
            "# Graph",
            "",
            "Text mentioning flowchart TB stays unchanged.",
            "",
            opening,
            f"{prefix}%% \U0001f50e comment",
            f"{prefix}flowchart TD;",
            f'{prefix} A["flowchart TB"] -->|extends| B',
            f"{prefix} subgraph S",
            f"{prefix} direction TB",
            f"{prefix} C --> D",
            f"{prefix} end",
            closing,
            "",
            "```sequence",
            "flowchart TB",
            "```",
            "",
            "```mermaid",
            "sequenceDiagram",
            " A->>B: Hello",
            "```",
            "",
        ]
    )
    report.write_bytes(text.encode())
    report.chmod(0o640)
    mode = report.stat().st_mode
    preview = fix_mermaid_direction(report, dry_run=True)
    assert preview["changed"] and not preview["written"]
    assert report.read_bytes() == text.encode()
    result = fix_mermaid_direction(report)
    assert result["written"]
    assert report.read_bytes() == text.replace("flowchart TD;", "flowchart LR;").encode()
    assert report.stat().st_mode == mode
    assert not fix_mermaid_direction(report)["changed"]
    assert not list(tmp_path.glob("*.updating"))


def test_multiple_blocks_and_atomic_failure(tmp_path):
    report = tmp_path / "report.md"
    source = "# Graph\n\n```mermaid\nflowchart TB\n A --> B\n```\n"
    report.write_text(source + "\n~~~mermaid\nflowchart TB\n BROKEN\n~~~\n")
    original = report.read_bytes()
    with pytest.raises(ValueError, match="Unsupported fixture"):
        fix_mermaid_direction(report)
    assert report.read_bytes() == original
    report.write_text(source + "\n" + source.split("\n\n", 1)[1])
    result = fix_mermaid_direction(report)
    assert sum(record["layout"]["changed"] for record in result["results"]) == 2
    assert "flowchart TB" not in report.read_text()


def test_unclosed_fence_does_not_write(tmp_path):
    report = tmp_path / "report.md"
    original = b"# Graph\n\n```mermaid\nflowchart TB\n A --> B\n"
    report.write_bytes(original)
    with pytest.raises(ValueError, match="unclosed"):
        fix_mermaid_direction(report)
    assert report.read_bytes() == original


def test_no_diagrams_no_write(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("# Plain\n")
    assert fix_mermaid_direction(report)["results"] == []
    assert not fix_mermaid_direction(report)["written"]


def test_missing_direction_is_inserted_from_same_layout_simulation(tmp_path):
    report = tmp_path / "implicit.md"
    report.write_text("# Graph\n\n```mermaid\nflowchart\n A --> B\n```\n")
    result = fix_mermaid_direction(report)
    assert result["written"]
    assert "flowchart LR\n" in report.read_text()


def test_concurrent_edit_is_preserved(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text("# Graph\n\n```mermaid\nflowchart TB\n A --> B\n```\n")

    def checker(blocks):
        report.write_text("# Newer content\n")
        return records_for(blocks)

    monkeypatch.setattr(markdown_audit, "_mermaid_check_records", checker)
    with pytest.raises(ValueError, match="changed during analysis"):
        fix_mermaid_direction(report)
    assert report.read_text() == "# Newer content\n"


def test_read_only_audit_reports_dimensions_and_recommendation(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("# Graph\n\n```mermaid\nflowchart TB\n A --> B\n```\n")
    before = report.read_bytes()
    audit = markdown_audit.audit_markdown(report)
    assert any("direction should be LR" in error and "500 x 100" in error for error in audit.errors)
    assert report.read_bytes() == before
    fix_mermaid_direction(report)
    assert markdown_audit.audit_markdown(report).valid


def test_cli_dry_run_and_failure(tmp_path, monkeypatch):
    requested = []
    monkeypatch.setattr(
        cli, "_ensure_renderer", lambda **kwargs: requested.append(kwargs["require_browser"])
    )
    report = tmp_path / "report.md"
    report.write_text("# Graph\n\n```mermaid\nflowchart TB\n A --> B\n```\n")
    runner = CliRunner()
    preview = runner.invoke(cli.app, ["fix-mermaid-direction", str(report), "--dry-run"])
    assert preview.exit_code == 0, preview.output
    assert '"dry_run": true' in preview.output
    assert requested == [False]
    assert "flowchart TB" in report.read_text()
    result = runner.invoke(cli.app, ["fix-mermaid-direction", str(report)])
    assert result.exit_code == 0, result.output
    assert "flowchart LR" in report.read_text()
    missing = runner.invoke(cli.app, ["fix-mermaid-direction", str(tmp_path / "missing.md")])
    assert missing.exit_code == 1
    assert '"kind": "mermaid-direction"' in missing.output
