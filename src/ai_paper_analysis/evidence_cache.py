"""Project-local, content-addressed cache for concise source evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .artifacts import write_json_atomic
from .content_review import file_digest
from .contracts import contract_directory, validate_instance

_FORBIDDEN_KEYS = frozenset(
    {"raw_text", "full_text", "page_text", "extracted_text", "pdf_bytes", "document_text"}
)

_IMPRECISE_LOCATOR = re.compile(
    r"(?:"
    r"\b(?:tbd|n/?a|unknown|unresolved|unspecified)\b|"
    r"exact .* locator .* unresolved|"
    r"formal method or main result|"
    r"method\s*/\s*assumptions?|"
    r"methods?\s+or\s+(?:assumptions?|main results?)|"
    r"main text|relevant pages?|paper generally"
    r")",
    re.IGNORECASE,
)
_LOCATOR_ANCHOR = re.compile(
    r"(?:§|\b(?:sections?|sec\.?|theorems?|thm\.?|definitions?|def\.?|propositions?|"
    r"prop\.?|lemmas?|(?:corollary|corollaries)|equations?|eq\.?|figures?|fig\.?|tables?|"
    r"algorithms?|(?:appendix|appendices)|remarks?|assumptions?|conditions?|examples?|proofs?|"
    r"methods?|results?|discussions?|conclusions?)\b)",
    re.IGNORECASE,
)


def _roles_directory() -> Path:
    contracts = contract_directory()
    direct = contracts.parent / "roles"
    return direct if direct.is_dir() else contracts.parent / "references" / "roles"


def evidence_policy_digest() -> str:
    """Bind cache reuse to evidence meaning and coverage rules."""

    digest = hashlib.sha256()
    for path in (
        _roles_directory() / "evidence-policy.md",
        _roles_directory() / "evidence.md",
        _roles_directory() / "evidence-reader.md",
        contract_directory() / "evidence-cache.schema.json",
    ):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def cache_key(
    source_sha256: str,
    source_class: str,
    coverage_fingerprint: str,
    *,
    policy_sha256: str | None = None,
) -> str:
    payload = {
        "source_sha256": source_sha256,
        "source_class": source_class,
        "coverage_fingerprint": coverage_fingerprint,
        "evidence_policy_sha256": policy_sha256 or evidence_policy_digest(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def cache_directory(target_root: Path) -> Path:
    return target_root.resolve() / ".ai-paper-analysis" / "evidence-cache"


def _cache_path(target_root: Path, key: str) -> Path:
    return cache_directory(target_root) / f"{key}.json"


def _find_forbidden_key(value: object, prefix: str = "") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{prefix}.{key}" if prefix else str(key)
            if key in _FORBIDDEN_KEYS:
                return location
            found = _find_forbidden_key(child, location)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_forbidden_key(child, f"{prefix}[{index}]")
            if found:
                return found
    return None


def _validate_semantics(record: dict[str, Any]) -> list[str]:
    errors = validate_instance(record, "evidence-cache.schema.json")
    forbidden = _find_forbidden_key(record)
    if forbidden:
        errors.append(f"{forbidden}: copied source text is not cacheable")
    locators = record.get("locators")
    if isinstance(locators, list):
        identifiers = [item.get("id") for item in locators if isinstance(item, dict)]
        if len(identifiers) != len(set(identifiers)):
            errors.append("locators: locator IDs must be unique")
        known = set(identifiers)
        coverage = record.get("coverage")
        page_count = coverage.get("page_count") if isinstance(coverage, dict) else None
        unreadable = (
            set(coverage.get("unreadable_pages", [])) if isinstance(coverage, dict) else set()
        )
        for index, item in enumerate(locators):
            if not isinstance(item, dict):
                continue
            locator = item.get("locator", "")
            page = item.get("page")
            if isinstance(locator, str) and (
                _IMPRECISE_LOCATOR.search(locator) or not _LOCATOR_ANCHOR.search(locator)
            ):
                errors.append(
                    f"locators.{index}: locator must name a precise section, theorem, "
                    "definition, equation, figure, table, appendix, or comparable anchor"
                )
            if isinstance(page, int):
                if isinstance(page_count, int) and page > page_count:
                    errors.append(f"locators.{index}: page {page} exceeds {page_count}")
                if page in unreadable:
                    errors.append(f"locators.{index}: page {page} is marked unreadable")
        for collection in ("facts", "formulas"):
            items = record.get(collection, [])
            if not isinstance(items, list):
                continue
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                references = (
                    item.get("locator_ids", [])
                    if collection == "facts"
                    else [item.get("locator_id")]
                )
                for reference in references:
                    if reference not in known:
                        errors.append(f"{collection}.{index}: unknown locator ID {reference}")
    coverage = record.get("coverage")
    if isinstance(coverage, dict):
        page_count = coverage.get("page_count")
        ranges = coverage.get("page_ranges")
        if isinstance(page_count, int) and isinstance(ranges, list):
            pages: set[int] = set()
            for item in ranges:
                if (
                    isinstance(item, list)
                    and len(item) == 2
                    and all(isinstance(v, int) for v in item)
                ):
                    start, end = item
                    if start > end:
                        errors.append(f"coverage.page_ranges: reversed range {start}-{end}")
                    elif end > page_count:
                        errors.append(f"coverage.page_ranges: page {end} exceeds {page_count}")
                    else:
                        pages.update(range(start, end + 1))
            unreadable_values = coverage.get("unreadable_pages", [])
            unreadable = (
                set(unreadable_values)
                if isinstance(unreadable_values, list)
                and all(isinstance(item, int) for item in unreadable_values)
                else set()
            )
            if pages & unreadable:
                errors.append("coverage: readable and unreadable pages overlap")
            if pages | unreadable != set(range(1, page_count + 1)):
                errors.append(
                    "coverage: readable ranges and unreadable pages must cover the source"
                )
    return errors


def record_evidence_cache(
    target_root: Path,
    source: Path,
    source_class: str,
    coverage_fingerprint: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Validate and atomically store one completed evidence packet."""

    source = source.expanduser().resolve(strict=True)
    policy = evidence_policy_digest()
    source_hash = file_digest(source)
    key = cache_key(source_hash, source_class, coverage_fingerprint, policy_sha256=policy)
    source_input = evidence.get("source", {})
    label = source_input.get("label") if isinstance(source_input, dict) else None
    payload = {
        **evidence,
        "schema_version": "1.0.0",
        "cache_key": key,
        "source": {
            "path": str(source),
            "sha256": source_hash,
            "label": label or source.stem,
        },
        "source_class": source_class,
        "evidence_policy_sha256": policy,
        "coverage_fingerprint": coverage_fingerprint,
    }
    errors = _validate_semantics(payload)
    if errors:
        raise ValueError("Invalid evidence cache record: " + "; ".join(errors))
    destination = _cache_path(target_root, key)
    write_json_atomic(destination, payload)
    verified = lookup_evidence_cache(target_root, source, source_class, coverage_fingerprint)
    if not verified["hit"]:
        raise ValueError(
            "Evidence cache write did not pass immediate read-back validation: "
            + str(verified.get("reason", "unknown failure"))
        )
    return verified


def lookup_evidence_cache(
    target_root: Path,
    source: Path,
    source_class: str,
    coverage_fingerprint: str,
) -> dict[str, Any]:
    """Return a verified cache hit or a compact miss reason without raising on stale data."""

    source = source.expanduser().resolve(strict=True)
    policy = evidence_policy_digest()
    source_hash = file_digest(source)
    key = cache_key(source_hash, source_class, coverage_fingerprint, policy_sha256=policy)
    path = _cache_path(target_root, key)
    if not path.is_file():
        return {"hit": False, "cache_key": key, "reason": "missing", "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"hit": False, "cache_key": key, "reason": "corrupt", "path": str(path)}
    validation_errors = _validate_semantics(payload) if isinstance(payload, dict) else []
    if not isinstance(payload, dict) or validation_errors:
        return {
            "hit": False,
            "cache_key": key,
            "reason": "invalid",
            "path": str(path),
            "errors": validation_errors[:8],
        }
    expected = {
        "cache_key": key,
        "source_class": source_class,
        "coverage_fingerprint": coverage_fingerprint,
        "evidence_policy_sha256": policy,
    }
    if any(payload.get(name) != value for name, value in expected.items()):
        return {"hit": False, "cache_key": key, "reason": "stale", "path": str(path)}
    cached_source = payload.get("source", {})
    if cached_source.get("sha256") != source_hash or cached_source.get("path") != str(source):
        return {"hit": False, "cache_key": key, "reason": "source-mismatch", "path": str(path)}
    return {"hit": True, "cache_key": key, "path": str(path), "record": payload}


def load_evidence_record(path: Path) -> dict[str, Any]:
    """Load one packet for report preparation with all cache invariants rechecked."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Evidence packet is not an object: {path}")
    errors = _validate_semantics(payload)
    if errors:
        raise ValueError(f"Invalid evidence packet {path}: " + "; ".join(errors))
    source = Path(payload["source"]["path"])
    if not source.is_file() or file_digest(source) != payload["source"]["sha256"]:
        raise ValueError(f"Evidence packet source changed or is missing: {source}")
    if payload["evidence_policy_sha256"] != evidence_policy_digest():
        raise ValueError(f"Evidence packet policy is stale: {path}")
    return payload
