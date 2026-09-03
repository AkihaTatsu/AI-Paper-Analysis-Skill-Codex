"""Bounded PDF download, structural preflight, and identity checks."""

from __future__ import annotations

import re
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlparse

import httpx
import pymupdf
from pypdf import PdfReader

from .identifiers import normalize_doi


class PdfValidationError(ValueError):
    """Raised when a staged file is not a publishable PDF."""


@dataclass(frozen=True)
class PdfAudit:
    path: str
    size_bytes: int
    page_count: int
    encrypted: bool
    text_characters: int
    scanned_or_text_sparse: bool
    title_similarity: float | None
    doi_found: bool | None
    identity_status: str
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible audit."""

        return asdict(self)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def title_similarity(expected: str, observed_text: str) -> float:
    """Return token recall for a title against extracted first-page text."""

    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return 0.0
    return len(expected_tokens & _tokens(observed_text)) / len(expected_tokens)


def _extract_text(path: Path, max_pages: int | None = None) -> tuple[int, str]:
    open_document: Any = pymupdf.open
    document = open_document(path)
    try:
        page_count = document.page_count
        limit = page_count if max_pages is None else min(page_count, max_pages)
        text = "\n".join(document.load_page(index).get_text("text") for index in range(limit))
        return page_count, text
    finally:
        document.close()


def validate_pdf(
    path: Path,
    *,
    expected_title: str | None = None,
    expected_doi: str | None = None,
    max_pdf_mib: int = 200,
    minimum_title_similarity: float = 0.65,
) -> PdfAudit:
    """Validate structure and identity without modifying the staged PDF."""

    path = path.resolve(strict=True)
    errors: list[str] = []
    warnings: list[str] = []
    size = path.stat().st_size
    if size == 0:
        errors.append("PDF is empty")
    if size > max_pdf_mib * 1024 * 1024:
        errors.append(f"PDF exceeds the {max_pdf_mib} MiB run limit")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            errors.append("File does not begin with the PDF magic header")

    encrypted = False
    page_count = 0
    extracted = ""
    try:
        reader = PdfReader(path, strict=False)
        encrypted = reader.is_encrypted
        if encrypted and reader.decrypt("") == 0:
            errors.append("PDF requires a password")
        else:
            page_count = len(reader.pages)
            if page_count < 1:
                errors.append("PDF contains no pages")
    except Exception as error:  # pypdf exposes several parser-specific exceptions
        errors.append(f"pypdf structural preflight failed: {error}")

    try:
        fitz_page_count, extracted = _extract_text(path)
        page_count = max(page_count, fitz_page_count)
    except Exception as error:  # PyMuPDF parser errors vary by document defect
        errors.append(f"PyMuPDF preflight failed: {error}")

    similarity: float | None = None
    first_page_text = ""
    if expected_title:
        with suppress(Exception):
            _, first_page_text = _extract_text(path, max_pages=2)
        similarity = title_similarity(expected_title, first_page_text)
        if first_page_text and similarity < minimum_title_similarity:
            errors.append(
                f"Expected title token recall {similarity:.2f} is below "
                f"{minimum_title_similarity:.2f}"
            )

    doi_found: bool | None = None
    if normalized_doi := normalize_doi(expected_doi):
        doi_found = normalized_doi in extracted.lower()

    identity_requested = bool(expected_title or normalized_doi)
    title_confirmed = similarity is not None and similarity >= minimum_title_similarity
    doi_confirmed = doi_found is True
    explicit_title_mismatch = (
        similarity is not None and bool(first_page_text) and not title_confirmed
    )
    if explicit_title_mismatch:
        identity_status = "failed"
    elif title_confirmed or doi_confirmed:
        identity_status = "confirmed"
    elif identity_requested:
        identity_status = "inconclusive"
        warnings.append(
            "PDF structure is valid, but title and DOI did not provide a positive identity signal; "
            "user confirmation is required before verified publication"
        )
    else:
        identity_status = "not_requested"

    text_characters = len(extracted.strip())
    sparse = page_count > 0 and text_characters < page_count * 80
    return PdfAudit(
        path=str(path),
        size_bytes=size,
        page_count=page_count,
        encrypted=encrypted,
        text_characters=text_characters,
        scanned_or_text_sparse=sparse,
        title_similarity=similarity,
        doi_found=doi_found,
        identity_status=identity_status,
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _stream_to_file(response: httpx.Response, handle: BinaryIO, max_bytes: int) -> None:
    total = 0
    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise PdfValidationError("Download exceeded the configured PDF size limit")
        handle.write(chunk)


def download_pdf(
    url: str,
    destination: Path,
    *,
    timeout_seconds: int = 60,
    max_retries: int = 3,
    max_pdf_mib: int = 200,
    headers: dict[str, str] | None = None,
) -> Path:
    """Download a public or explicitly authorized PDF with bounded retries."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("PDF URL must be an absolute HTTP(S) URL")
    destination.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = max_pdf_mib * 1024 * 1024
    request_headers = {"User-Agent": "ai-paper-analysis/0.1.0"}
    request_headers.update(headers or {})
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            with (
                httpx.Client(follow_redirects=True, timeout=timeout_seconds) as client,
                client.stream("GET", url, headers=request_headers) as response,
            ):
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise httpx.HTTPStatusError(
                        f"Rate limited; Retry-After={retry_after or 'unspecified'}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > max_bytes:
                    raise PdfValidationError("Declared content length exceeds the PDF size limit")
                content_type = response.headers.get("Content-Type", "").lower()
                if "html" in content_type:
                    raise PdfValidationError("Server returned HTML instead of a PDF")
                with destination.open("wb") as handle:
                    _stream_to_file(response, handle, max_bytes)
            with destination.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise PdfValidationError("Downloaded file is not a PDF")
            return destination
        except (httpx.HTTPError, OSError, PdfValidationError, ValueError) as error:
            destination.unlink(missing_ok=True)
            last_error = error
            if attempt >= max_retries:
                break
            time.sleep(min(2**attempt, 8))
    raise PdfValidationError(f"PDF download failed after {max_retries + 1} attempts: {last_error}")
