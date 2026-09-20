"""Lightweight report-format and relationship audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .content_review import validate_content_review
from .markdown_audit import AuditContext, audit_markdown


@dataclass(frozen=True)
class PaperReportAudit:
    valid: bool
    format_status: str
    content_status: str
    errors: tuple[str, ...]
    markdown: dict[str, object]

    @property
    def publication_ready(self) -> bool:
        return self.valid and self.content_status in {"complete", "partial"}

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CategoryReportAudit:
    valid: bool
    format_status: str
    relationship_valid: bool
    errors: tuple[str, ...]
    markdown: dict[str, object]
    content_status: str = "unreviewed"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def audit_paper_report(
    report_path: Path,
    *,
    content_review: dict[str, Any] | None = None,
    publication_path: Path | None = None,
    context: AuditContext | None = None,
) -> PaperReportAudit:
    """Audit report structure without claiming factual verification."""

    markdown = audit_markdown(
        report_path, report_kind="paper", context=context, publication_path=publication_path
    )
    status, review_errors = validate_content_review(
        report_path,
        content_review,
        publication_path=publication_path,
    )
    return PaperReportAudit(
        valid=markdown.valid and not review_errors,
        format_status="structure-valid" if markdown.valid else "failed",
        content_status=status,
        errors=(*markdown.errors, *review_errors),
        markdown=markdown.to_dict(),
    )


def audit_category_report(
    report_path: Path,
    relationship_ledger: Path,
    *,
    content_review: dict[str, Any] | None = None,
    publication_path: Path | None = None,
    context: AuditContext | None = None,
) -> CategoryReportAudit:
    """Audit category-report structure and relationship evidence separately."""

    from .ledger import read_records, validate_record

    markdown = audit_markdown(
        report_path, report_kind="category", context=context, publication_path=publication_path
    )
    errors = list(markdown.errors)
    status, review_errors = validate_content_review(
        report_path,
        content_review,
        publication_path=publication_path,
        report_kind="category",
    )
    errors.extend(review_errors)
    relationship_errors: list[str] = []
    relationships = list(read_records(relationship_ledger))
    for index, record in enumerate(relationships, start=1):
        relationship_errors.extend(
            f"relationship record {index}: {error}"
            for error in validate_record(record, "relationship")
        )
    errors.extend(relationship_errors)
    return CategoryReportAudit(
        valid=not errors,
        format_status="structure-valid" if markdown.valid else "failed",
        relationship_valid=not relationship_errors,
        errors=tuple(errors),
        markdown=markdown.to_dict(),
        content_status=status,
    )
