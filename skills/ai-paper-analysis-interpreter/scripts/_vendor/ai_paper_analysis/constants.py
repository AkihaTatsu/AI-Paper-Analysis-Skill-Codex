"""Stable public constants shared by the Skills and validators."""

from __future__ import annotations

SCHEMA_VERSION = "1.0.0"

CLASSIFICATION_COLUMNS = (
    "schema_version",
    "paper_id",
    "title",
    "authors_json",
    "publication_year",
    "venue",
    "doi",
    "arxiv_id",
    "canonical_url",
    "pdf_url",
    "local_pdf_path",
    "report_path",
    "code_repository_url",
    "code_commit",
    "taxonomy_id",
    "taxonomy_version",
    "category_id",
    "category_name",
    "subcategory_id",
    "subcategory_name",
    "classification_reason",
    "evidence_locator",
    "verification_status",
    "review_status",
    "notes",
)

RELATIONSHIPS = (
    "depends_on",
    "extends",
    "improves_on",
    "generalizes",
    "specializes",
    "adapts_to",
    "combines_with",
    "simplifies",
    "evaluates",
    "reproduces",
    "contrasts_with",
    "surveys",
)

VERIFICATION_STATUSES = ("verified", "partial", "failed", "conflict")
REVIEW_STATUSES = ("proposed", "confirmed", "rejected")

DEFAULT_NETWORK = {
    "per_host_concurrency": 2,
    "timeout_seconds": 60,
    "max_retries": 3,
    "max_pdf_mib": 200,
}
