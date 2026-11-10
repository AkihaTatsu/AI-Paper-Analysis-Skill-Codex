from pathlib import Path

import pymupdf
import pytest

from ai_paper_analysis.pdf_read import read_pdf, render_pdf_pages, selected_pages


def test_page_selection_is_explicit_and_validated() -> None:
    assert selected_pages("3,1-2,2", 3) == [1, 2, 3]
    for invalid in ("0", "4", "3-1", "1-2-3"):
        with pytest.raises(ValueError):
            selected_pages(invalid, 3)


def test_original_page_reading_and_reused_renders(tmp_path: Path) -> None:
    pdf = tmp_path / "source with spaces.pdf"
    with pymupdf.open() as document:
        for text in ("First page", "Second page"):
            document.new_page().insert_text((72, 72), text)
        document.save(pdf)
    result = read_pdf(pdf, pages="2")
    assert result["page_count"] == 2
    assert result["pages"][0]["page"] == 2
    assert "Second page" in result["pages"][0]["text"]
    first = render_pdf_pages(pdf, tmp_path / "pages", pages="1")
    second = render_pdf_pages(pdf, tmp_path / "pages", pages="1")
    assert first["images"][0]["reused"] is False
    assert second["images"][0]["reused"] is True
    assert Path(second["images"][0]["path"]).is_file()
