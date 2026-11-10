"""Content-bound attestations of an actual agent review, not factual proofs."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import contract_directory, load_json, validate_instance

CHECKS = (
    "source_fidelity",
    "coverage",
    "terminology",
    "reasoning",
    "formulas_and_analogies",
    "experiments_and_relationships",
)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def policy_digest(report_kind: str = "paper") -> str:
    contracts = contract_directory()
    roles = contracts.parent / "roles"
    if not roles.is_dir():
        roles = contracts.parent / "references" / "roles"
    specific = {
        "paper": ("paper-content.md", "formulas.md"),
        "category": ("category-content.md", "relationships.md"),
    }
    if report_kind not in specific:
        raise ValueError("report_kind must be paper or category")
    names = (*specific[report_kind], "evidence-policy.md", "report-style.md")
    files = [roles / name for name in sorted(names)]
    digest = hashlib.sha256()
    policy = load_json("semantic-policy.json", directory=contracts)
    digest.update(str(policy["semantic_version"]).encode("utf-8"))
    digest.update(json.dumps(CHECKS, separators=(",", ":")).encode("utf-8"))
    for path in files:
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def compatible_policy_digests(report_kind: str) -> set[str]:
    policy = load_json("semantic-policy.json", directory=contract_directory())
    values = policy.get("compatible_legacy_sha256", {}).get(report_kind, [])
    return {value for value in values if isinstance(value, str)}


def create_content_review(
    report: Path,
    assessment: dict[str, Any],
    sources: tuple[Path, ...],
    *,
    report_kind: str = "paper",
    publication_path: Path | None = None,
) -> dict[str, Any]:
    """Bind a supplied, completed human/agent assessment to exact artifacts."""
    destination = (publication_path or report).resolve()
    payload = {
        "schema_version": "1.0.0",
        "report_kind": report_kind,
        "report_sha256": file_digest(report),
        "publication_path": str(destination),
        "policy_sha256": policy_digest(report_kind),
        "sources": [
            {"path": str(path.resolve()), "sha256": file_digest(path)}
            for path in sorted(set(sources))
        ],
        "reviewer": assessment.get("reviewer"),
        "reviewed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "reviewed_sections": assessment.get("reviewed_sections"),
        "checks": assessment.get("checks"),
        "content_status": assessment.get("content_status"),
        "limitations": assessment.get("limitations", []),
    }
    status, errors = validate_content_review(
        report, payload, publication_path=destination, report_kind=report_kind
    )
    if errors or status == "unreviewed":
        raise ValueError("; ".join(errors))
    return payload


def validate_content_review(
    report: Path,
    review: dict[str, Any] | None,
    *,
    publication_path: Path | None = None,
    report_kind: str = "paper",
) -> tuple[str, list[str]]:
    if review is None:
        return "unreviewed", []
    errors = validate_instance(review, "report-review.schema.json")
    if errors:
        return "unreviewed", [f"content review: {error}" for error in errors]
    required = set(range(1, 8 if report_kind == "paper" else 4))
    if set(review["reviewed_sections"]) != required:
        errors.append("content review must cover every numbered section exactly once")
    if review["report_kind"] != report_kind:
        errors.append("content review report kind differs")
    try:
        report_hash = file_digest(report)
    except OSError:
        report_hash = None
    if review["report_sha256"] != report_hash:
        errors.append("content review is stale: report changed")
    if review["publication_path"] != str((publication_path or report).resolve()):
        errors.append("content review is stale: publication location changed")
    accepted_policies = {policy_digest(report_kind), *compatible_policy_digests(report_kind)}
    if review["policy_sha256"] not in accepted_policies:
        errors.append("content review is stale: review policy changed")
    for source in review["sources"]:
        path = Path(source["path"])
        try:
            source_hash = file_digest(path)
        except OSError:
            source_hash = None
        if source_hash != source["sha256"]:
            errors.append(f"content review is stale: source changed or missing: {path}")
    if review["content_status"] == "complete":
        if not all(review["checks"].get(key) is True for key in CHECKS):
            errors.append("complete content requires every semantic check to pass")
        if review["limitations"]:
            errors.append("complete content cannot retain unresolved review limitations")
    elif not review["limitations"]:
        errors.append("partial content requires explicit unresolved limitations")
    if review["content_status"] == "partial" and not all(
        review["checks"].get(key) is True for key in CHECKS if key != "coverage"
    ):
        errors.append("partial content may relax coverage only, not unresolved semantic defects")
    return ("unreviewed" if errors else review["content_status"]), errors


def load_artifact_review(
    root: Path, report: Path, *, report_kind: str = "paper"
) -> dict[str, Any] | None:
    """Read only the directly addressed compact artifact state, never history."""
    if report_kind not in {"paper", "category"}:
        raise ValueError("report_kind must be paper or category")
    kind = f"{report_kind}-report"
    state = root / ".ai-paper-analysis" / "state" / f"{report.stem}.{kind}.json"
    if not state.is_file():
        return None
    try:
        payload = json.loads(state.read_text(encoding="utf-8"))
        if validate_instance(payload, "artifact-state.schema.json"):
            return None
        if payload["artifact"]["kind"] != kind or payload["status"] != "published":
            return None
        if (root / payload["artifact"]["path"]).resolve() != report.resolve():
            return None
        review = payload.get("content_review")
        return review if isinstance(review, dict) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None
