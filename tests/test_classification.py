from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from ai_paper_analysis import markdown_audit
from ai_paper_analysis.classification import validate_classification, write_classification
from ai_paper_analysis.constants import CLASSIFICATION_COLUMNS

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def disable_external_renderers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(markdown_audit, "_full_renderer_errors", lambda path: [])
    monkeypatch.setattr(markdown_audit, "_mermaid_syntax_audit", lambda blocks: ([], []))


def taxonomy() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "taxonomy_id": "fixture-taxonomy",
        "taxonomy_version": "1.0.0",
        "title": "Fixture Taxonomy",
        "description": "Synthetic exclusive taxonomy.",
        "categories": [
            {
                "category_id": "method",
                "name": "Method Papers",
                "definition": "Papers centered on a method.",
                "include_when": ["The method is the main contribution."],
                "exclude_when": ["The method is only a baseline."],
                "subcategories": [
                    {
                        "subcategory_id": "optimization",
                        "name": "Optimization Methods",
                        "definition": "Methods centered on optimization.",
                        "include_when": ["Optimization defines the method."],
                        "exclude_when": [],
                    }
                ],
            }
        ],
        "confirmed": True,
        "confirmed_at": "2026-08-28T01:02:03Z",
        "confirmation_summary": "Confirmed in the final assignment review.",
    }


def test_comparison_ready_classification(tmp_path: Path) -> None:
    papers = tmp_path / "papers"
    papers.mkdir()
    pdf = papers / "fixture.pdf"
    report = papers / "fixture.md"
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Fixture Paper\nDOI: 10.1000/fixture\n" + "Evidence text. " * 40,
    )
    document.save(pdf)
    document.close()
    report_text = (FIXTURES / "portable-report.md").read_text(encoding="utf-8")
    report_text = report_text.replace("# Portable Report", "# Fixture Paper")
    report_text = report_text.replace(
        "## 1. Overview\n",
        "## 1. Overview\n\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        "| Paper ID | doi:10.1000/fixture |\n"
        "| Category ID | method |\n"
        "| Subcategory ID | optimization |\n",
    )
    report.write_text(report_text, encoding="utf-8")
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(json.dumps(taxonomy()), encoding="utf-8")
    row = dict.fromkeys(CLASSIFICATION_COLUMNS, "")
    row.update(
        {
            "schema_version": "1.0.0",
            "paper_id": "doi:10.1000/fixture",
            "title": "Fixture Paper",
            "authors_json": json.dumps(["A. Researcher"]),
            "publication_year": "2026",
            "canonical_url": "https://doi.org/10.1000/fixture",
            "local_pdf_path": "papers/fixture.pdf",
            "report_path": "papers/fixture.md",
            "taxonomy_id": "fixture-taxonomy",
            "taxonomy_version": "1.0.0",
            "category_id": "method",
            "category_name": "Method Papers",
            "subcategory_id": "optimization",
            "subcategory_name": "Optimization Methods",
            "classification_reason": "The method is the main contribution.",
            "evidence_locator": "Paper p. 2, section 1",
            "verification_status": "verified",
            "review_status": "confirmed",
        }
    )
    csv_path = tmp_path / "classification.csv"
    write_classification(csv_path, [row])
    audit = validate_classification(
        csv_path,
        taxonomy_path,
        target_root=tmp_path,
        require_comparison_ready=True,
    )
    assert audit.valid, audit.errors
    assert audit.row_count == 1


def test_comparison_ready_rejects_fake_pdf_and_loose_report_ids(tmp_path: Path) -> None:
    papers = tmp_path / "papers"
    papers.mkdir()
    (papers / "fixture.pdf").write_bytes(b"synthetic-pdf-bytes")
    (papers / "fixture.md").write_text(
        "# Fixture\n\nCategory ID method Subcategory ID optimization\n",
        encoding="utf-8",
    )
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(json.dumps(taxonomy()), encoding="utf-8")
    row = dict.fromkeys(CLASSIFICATION_COLUMNS, "")
    row.update(
        {
            "schema_version": "1.0.0",
            "paper_id": "doi:10.1000/fixture",
            "title": "Fixture Paper",
            "authors_json": json.dumps(["A. Researcher"]),
            "publication_year": "2026",
            "local_pdf_path": "papers/fixture.pdf",
            "report_path": "papers/fixture.md",
            "taxonomy_id": "fixture-taxonomy",
            "taxonomy_version": "1.0.0",
            "category_id": "method",
            "category_name": "Method Papers",
            "subcategory_id": "optimization",
            "subcategory_name": "Optimization Methods",
            "classification_reason": "The method is the main contribution.",
            "evidence_locator": "Paper p. 2",
            "verification_status": "verified",
            "review_status": "confirmed",
        }
    )
    csv_path = tmp_path / "classification.csv"
    write_classification(csv_path, [row])
    audit = validate_classification(
        csv_path,
        taxonomy_path,
        target_root=tmp_path,
        require_comparison_ready=True,
    )
    assert not audit.valid
    assert any("PDF" in error for error in audit.errors)
    assert any("Basic Information" in error for error in audit.errors)
