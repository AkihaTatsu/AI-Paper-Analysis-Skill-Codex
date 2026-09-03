"""Paper identity normalization and portable filename helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_doi(value: str | None) -> str:
    """Normalize a DOI to its identifier without resolver prefixes."""

    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi:\s*", "", normalized)
    return normalized.rstrip(" .")


def normalize_arxiv_id(value: str | None) -> str:
    """Normalize an arXiv identifier and remove a version suffix."""

    if not value:
        return ""
    normalized = value.strip()
    normalized = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", normalized)
    normalized = normalized.removesuffix(".pdf")
    return re.sub(r"v\d+$", "", normalized, flags=re.IGNORECASE)


def stable_paper_id(
    *,
    doi: str | None = None,
    arxiv_id: str | None = None,
    native_id: str | None = None,
) -> str:
    """Build a paper ID from a bibliographic or provider identifier."""

    if normalized_doi := normalize_doi(doi):
        return f"doi:{normalized_doi}"
    if normalized_arxiv := normalize_arxiv_id(arxiv_id):
        return f"arxiv:{normalized_arxiv}"
    if native_id and native_id.strip():
        return f"native:{native_id.strip()}"
    raise ValueError("A DOI, arXiv ID, or native source ID is required")


def ascii_slug(value: str, max_length: int = 72) -> str:
    """Create a portable, readable ASCII slug."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    slug = re.sub(r"-+", "-", slug)
    return slug[:max_length].rstrip("-") or "paper"


def artifact_stem(*, year: int | str, first_author: str, title: str, paper_id: str) -> str:
    """Build the paired PDF/Markdown stem with its one-time identifier suffix."""

    year_text = str(year) if re.fullmatch(r"\d{4}", str(year)) else "undated"
    author = ascii_slug(first_author, max_length=32)
    title_slug = ascii_slug(title)
    identifier_suffix = hashlib.sha256(paper_id.encode("utf-8")).hexdigest()[:10]
    return f"{year_text}_{author}_{title_slug}_{identifier_suffix}"
