"""Page-addressed source reading and reusable original-page images."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf

from .content_review import file_digest


def selected_pages(spec: str | None, count: int) -> list[int]:
    if not spec:
        return list(range(1, count + 1))
    selected: set[int] = set()
    for part in spec.split(","):
        limits = part.strip().split("-")
        if len(limits) not in {1, 2}:
            raise ValueError("pages must contain one-based numbers or inclusive ranges")
        first, last = int(limits[0]), int(limits[-1])
        if not 1 <= first <= last <= count:
            raise ValueError(f"pages must be between 1 and {count}")
        selected.update(range(first, last + 1))
    return sorted(selected)


def read_pdf(path: Path, *, pages: str | None = None) -> dict[str, Any]:
    open_document: Any = pymupdf.open
    with open_document(path) as document:
        if document.needs_pass:
            raise ValueError("PDF requires a password")
        selected = selected_pages(pages, len(document))
        return {
            "path": str(path.resolve()),
            "sha256": file_digest(path),
            "page_count": len(document),
            "pages": [
                {"page": page, "text": document[page - 1].get_text("text")} for page in selected
            ],
        }


def render_pdf_pages(
    path: Path,
    output: Path,
    *,
    pages: str,
    dpi: int = 144,
) -> dict[str, Any]:
    if not 72 <= dpi <= 600:
        raise ValueError("dpi must be between 72 and 600")
    digest = file_digest(path)
    images: list[dict[str, Any]] = []
    open_document: Any = pymupdf.open
    with open_document(path) as document:
        if document.needs_pass:
            raise ValueError("PDF requires a password")
        selected = selected_pages(pages, len(document))
        output.mkdir(parents=True, exist_ok=True)
        for page in selected:
            target = output / f"{digest[:16]}-p{page}-{dpi}.png"
            reused = target.is_file()
            if not reused:
                document[page - 1].get_pixmap(dpi=dpi).save(target)
            images.append({"page": page, "path": str(target.resolve()), "reused": reused})
    return {"source_sha256": digest, "images": images}
