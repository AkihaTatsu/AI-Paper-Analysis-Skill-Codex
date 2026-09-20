"""Classification CSV, taxonomy, and comparison-input validation."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .markdown_audit import AuditContext

from .constants import CLASSIFICATION_COLUMNS
from .contracts import validate_instance


@dataclass(frozen=True)
class ClassificationAudit:
    valid: bool
    row_count: int
    errors: tuple[str, ...]


def _taxonomy_index(
    taxonomy: dict[str, Any], errors: list[str]
) -> dict[str, tuple[str, dict[str, str]]]:
    index: dict[str, tuple[str, dict[str, str]]] = {}
    seen_subcategories: set[str] = set()
    for category in taxonomy.get("categories", []):
        category_id = category.get("category_id", "")
        if category_id in index:
            errors.append(f"taxonomy: duplicate category_id {category_id}")
            continue
        subcategories: dict[str, str] = {}
        for subcategory in category.get("subcategories", []):
            subcategory_id = subcategory.get("subcategory_id", "")
            if subcategory_id in seen_subcategories:
                errors.append(f"taxonomy: duplicate subcategory_id {subcategory_id}")
                continue
            seen_subcategories.add(subcategory_id)
            subcategories[subcategory_id] = str(subcategory.get("name", ""))
        index[category_id] = (str(category.get("name", "")), subcategories)
    return index


def _basic_information(path: Path) -> dict[str, str]:
    """Read exact key/value rows from the report's Basic Information table."""

    from markdown_it import MarkdownIt

    tokens = MarkdownIt("commonmark").enable("table").parse(path.read_text(encoding="utf-8"))
    values: dict[str, str] = {}
    duplicates: set[str] = set()
    aliases = {
        "\u8bba\u6587 ID": "Paper ID",
        "\u7a33\u5b9a\u8bba\u6587 ID": "Paper ID",
        "\u7c7b\u522b ID": "Category ID",
        "\u5b50\u7c7b\u522b ID": "Subcategory ID",
    }
    in_overview = in_table = False
    cells: list[str] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h2":
            heading = tokens[index + 1].content
            in_overview = bool(re.match(r"^1[.)]\s+", heading))
        elif token.type == "table_open":
            in_table = in_overview
        elif token.type == "table_close":
            in_table = False
        elif in_table and token.type == "tr_open":
            cells = []
        elif in_table and token.type == "inline":
            cells.append(token.content.strip())
        elif in_table and token.type == "tr_close" and len(cells) >= 2:
            key = aliases.get(cells[0], cells[0])
            if key not in {"Paper ID", "Category ID", "Subcategory ID"}:
                continue
            if key in values:
                duplicates.add(key)
            values[key] = cells[1].strip("`")
    for key in duplicates:
        values.pop(key, None)

    return values


def read_classification(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read an RFC 4180 classification CSV without changing field values."""

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        return list(headers), [dict(row) for row in reader]


def validate_classification(
    csv_path: Path,
    taxonomy_path: Path,
    *,
    target_root: Path | None = None,
    require_comparison_ready: bool = False,
    audit_context: AuditContext | None = None,
) -> ClassificationAudit:
    """Validate schema, exclusive assignment, paths, and semantic IDs."""

    errors: list[str] = []
    if require_comparison_ready and audit_context is None:
        from .markdown_audit import AuditContext

        audit_context = AuditContext()
    headers, rows = read_classification(csv_path)
    expected_headers = list(CLASSIFICATION_COLUMNS)
    if headers != expected_headers:
        errors.append(
            "CSV header does not match the fixed 25-column contract: "
            f"expected {expected_headers}, observed {headers}"
        )

    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    if taxonomy_errors := validate_instance(taxonomy, "taxonomy.schema.json"):
        errors.extend(f"taxonomy: {error}" for error in taxonomy_errors)
    taxonomy_index = _taxonomy_index(taxonomy, errors)
    paper_ids: set[str] = set()

    if target_root is not None:
        root = target_root.resolve()
        if csv_path.resolve() != root / "classification.csv":
            errors.append("classification CSV must be <target-root>/classification.csv")
        if taxonomy_path.resolve() != root / "taxonomy.json":
            errors.append("taxonomy must be <target-root>/taxonomy.json")

    for row_number, row in enumerate(rows, start=2):
        prefix = f"row {row_number}"
        row_errors = validate_instance(row, "classification-row.schema.json")
        errors.extend(f"{prefix}: {error}" for error in row_errors)
        paper_id = row.get("paper_id", "")
        if paper_id in paper_ids:
            errors.append(f"{prefix}: duplicate paper_id {paper_id}")
        paper_ids.add(paper_id)
        try:
            authors = json.loads(row.get("authors_json", ""))
            valid_authors = isinstance(authors, list) and all(
                isinstance(author, str) for author in authors
            )
            if not valid_authors:
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            errors.append(f"{prefix}: authors_json must encode an array of strings")

        if row.get("taxonomy_id") != taxonomy.get("taxonomy_id"):
            errors.append(f"{prefix}: taxonomy_id does not match taxonomy.json")
        if row.get("taxonomy_version") != taxonomy.get("taxonomy_version"):
            errors.append(f"{prefix}: taxonomy_version does not match taxonomy.json")
        category_id = row.get("category_id", "")
        subcategory_id = row.get("subcategory_id", "")
        if category_id not in taxonomy_index:
            errors.append(f"{prefix}: unknown category_id {category_id}")
        else:
            category_name, subcategories = taxonomy_index[category_id]
            if row.get("category_name") != category_name:
                errors.append(f"{prefix}: category_name does not match taxonomy.json")
            if subcategory_id not in subcategories:
                errors.append(
                    f"{prefix}: subcategory_id {subcategory_id} does not belong to {category_id}"
                )
            elif row.get("subcategory_name") != subcategories[subcategory_id]:
                errors.append(f"{prefix}: subcategory_name does not match taxonomy.json")

        if require_comparison_ready:
            errors.extend(
                _comparison_row_errors(
                    row, prefix, target_root or csv_path.parent, audit_context=audit_context
                )
            )

    return ClassificationAudit(valid=not errors, row_count=len(rows), errors=tuple(errors))


def _comparison_row_errors(
    row: dict[str, str],
    prefix: str,
    target_root: Path,
    *,
    audit_context: AuditContext | None = None,
) -> list[str]:
    from .pdf import validate_pdf
    from .report_audit import audit_paper_report

    errors: list[str] = []
    if row.get("verification_status") != "verified":
        errors.append(f"{prefix}: comparison requires verification_status=verified")
    if row.get("review_status") != "confirmed":
        errors.append(f"{prefix}: comparison requires review_status=confirmed")
    resolved: dict[str, Path] = {}
    for path_field in ("local_pdf_path", "report_path"):
        relative = row.get(path_field, "")
        if not relative:
            errors.append(f"{prefix}: {path_field} is required")
            continue
        path = (target_root / relative).resolve()
        if not path.is_relative_to(target_root.resolve()):
            errors.append(f"{prefix}: {path_field} escapes target root")
            continue
        if not path.is_file():
            errors.append(f"{prefix}: missing artifact {relative}")
            continue
        resolved[path_field] = path

    pdf = resolved.get("local_pdf_path")
    if pdf is not None:
        pdf_audit = validate_pdf(
            pdf,
            expected_title=row.get("title") or None,
            expected_doi=row.get("doi") or None,
        )
        errors.extend(f"{prefix}: PDF: {error}" for error in pdf_audit.errors)
        if pdf_audit.identity_status != "confirmed":
            errors.append(
                f"{prefix}: PDF identity_status must be confirmed for comparison; "
                f"observed {pdf_audit.identity_status}"
            )

    report = resolved.get("report_path")
    if report is not None:
        from .content_review import load_artifact_review

        review = load_artifact_review(target_root, report)
        report_audit = audit_paper_report(
            report,
            content_review=review,
            context=audit_context,
        )
        errors.extend(f"{prefix}: report: {error}" for error in report_audit.errors)
        if report_audit.content_status != "complete":
            errors.append(
                f"{prefix}: report requires a current complete content review; "
                f"observed {report_audit.content_status}"
            )
        elif pdf is not None and review is not None:
            reviewed_sources = {Path(source["path"]).resolve() for source in review["sources"]}
            if pdf.resolve() not in reviewed_sources:
                errors.append(f"{prefix}: selected PDF is not bound to the report content review")
        info = _basic_information(report)
        expected = {
            "Paper ID": row.get("paper_id", ""),
            "Category ID": row.get("category_id", ""),
            "Subcategory ID": row.get("subcategory_id", ""),
        }
        for field, value in expected.items():
            if info.get(field) != value:
                errors.append(f"{prefix}: Basic Information field {field!r} must equal {value!r}")
    return errors


def write_classification(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the fixed classification CSV deterministically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(CLASSIFICATION_COLUMNS),
            extrasaction="raise",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
