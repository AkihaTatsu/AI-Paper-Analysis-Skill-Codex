"""Lightweight report-format and relationship audits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .markdown_audit import audit_markdown


@dataclass(frozen=True)
class PaperReportAudit:
    valid: bool
    format_status: str
    content_status: str
    errors: tuple[str, ...]
    markdown: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CategoryReportAudit:
    valid: bool
    format_status: str
    relationship_valid: bool
    errors: tuple[str, ...]
    markdown: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def audit_paper_report(report_path: Path) -> PaperReportAudit:
    """Audit report structure without claiming factual verification."""

    markdown = audit_markdown(report_path, report_kind="paper")
    report_text = report_path.read_text(encoding="utf-8").lower()
    return PaperReportAudit(
        valid=markdown.valid,
        format_status="structure-valid" if markdown.valid else "failed",
        content_status="partial" if "partial" in report_text else "complete",
        errors=markdown.errors,
        markdown=markdown.to_dict(),
    )


def audit_category_report(report_path: Path, relationship_ledger: Path) -> CategoryReportAudit:
    """Audit category-report structure and relationship evidence separately."""

    from .ledger import read_records, validate_record

    markdown = audit_markdown(report_path, report_kind="category")
    errors = list(markdown.errors)
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
    )
