from __future__ import annotations

from pathlib import Path

import fitz

from ai_paper_analysis.pdf import title_similarity, validate_pdf


def make_pdf(path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_valid_pdf_identity_and_sparse_detection(tmp_path: Path) -> None:
    path = tmp_path / "paper.pdf"
    title = "A Portable Research Fixture"
    make_pdf(path, f"{title}\nDOI: 10.1000/example\n" + "Evidence text. " * 40)
    audit = validate_pdf(path, expected_title=title, expected_doi="10.1000/example")
    assert audit.valid, audit.errors
    assert audit.page_count == 1
    assert audit.title_similarity is not None and audit.title_similarity >= 0.65
    assert audit.doi_found is True
    assert audit.identity_status == "confirmed"
    assert audit.scanned_or_text_sparse is False


def test_non_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "not-a-paper.pdf"
    path.write_text("<html>not a PDF</html>", encoding="utf-8")
    audit = validate_pdf(path)
    assert not audit.valid
    assert any("magic" in error for error in audit.errors)


def test_unreadable_identity_is_inconclusive_not_verified(tmp_path: Path) -> None:
    path = tmp_path / "sparse.pdf"
    make_pdf(path, "Scanned page")
    audit = validate_pdf(
        path,
        expected_title="A Different Expected Title",
        expected_doi="10.1000/missing",
    )
    assert not audit.valid

    path = tmp_path / "blank.pdf"
    make_pdf(path, "")
    audit = validate_pdf(
        path,
        expected_title="A Different Expected Title",
        expected_doi="10.1000/missing",
    )
    assert audit.valid, audit.errors
    assert audit.identity_status == "inconclusive"
    assert audit.warnings


def test_title_similarity_uses_expected_token_recall() -> None:
    assert title_similarity("A Small Useful Paper", "Useful Paper by Example") == 0.5
