"""Bind formula and workflow demonstrations to final report passages."""

from __future__ import annotations

import re
from typing import Any

from .contracts import validate_instance
from .markdown_audit import _outside_fences


def targets_from_matrix(matrix: dict[str, Any], report_kind: str) -> list[dict[str, Any]]:
    errors = validate_instance(matrix, "coverage-matrix.schema.json")
    if errors:
        raise ValueError("; ".join(errors))
    if matrix["report_kind"] != report_kind:
        raise ValueError("demonstration coverage matrix report kind differs")
    return [
        {
            "id": row["id"],
            "kind": row["demonstration_kind"],
            "report_section": row["report_section"],
            "target_quote": row["demonstration_target"],
        }
        for row in matrix["rows"]
        if "demonstration_kind" in row
    ]


def demonstration_errors(
    text: str,
    targets: list[dict[str, Any]],
    records: list[dict[str, Any]],
    report_kind: str,
) -> list[str]:
    """Check coverage and exact visible quotations; meaning is reviewed by an agent."""
    visible_lines, _ = _outside_fences(text.splitlines())
    visible = "\n".join(visible_lines)
    visible = re.sub(r"`+[^`\n]*`+", lambda m: " " * len(m[0]), visible)
    sections = list(re.finditer(r"(?m)^##\s+([1-7])\.\s+.*$", visible))
    ranges = {
        int(match[1]): (
            match.start(),
            sections[i + 1].start() if i + 1 < len(sections) else len(visible),
        )
        for i, match in enumerate(sections)
    }
    errors: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    target_spans: dict[str, tuple[int, int]] = {}
    for target in targets:
        identifier = target["id"]
        if identifier in by_id:
            errors.append(f"demonstration: duplicate target {identifier}")
        by_id[identifier] = target
        start, end = ranges.get(target["report_section"], (0, 0))
        quote = target["target_quote"]
        passage = visible[start:end]
        if passage.count(quote) != 1:
            errors.append(f"demonstration: {identifier} target must occur once in its section")
            continue
        offset = start + passage.index(quote)
        target_spans[identifier] = (offset, offset + len(quote))
        if target["kind"] == "formula" and not (
            re.fullmatch(r"\$\$[\s\S]*?\$\$", quote)
            and "$$" not in quote[2:-2]
            or re.fullmatch(r"\$[^$\n]+\$", quote)
        ):
            errors.append(
                f"demonstration: {identifier} formula target must quote its math delimiters"
            )
        if report_kind == "paper" and target["kind"] == "flow" and target["report_section"] != 4:
            errors.append(f"demonstration: {identifier} paper flow must be in section 4")
    locations = [(by_id[key]["kind"], span) for key, span in target_spans.items()]
    if len(locations) != len(set(locations)):
        errors.append("demonstration: duplicate target passage")
    if report_kind == "paper" and not any(t["kind"] == "flow" for t in targets):
        errors.append("demonstration: paper requires an end-to-end flow target")

    seen: set[str] = set()
    example_spans: list[tuple[int, int]] = []
    for record in records:
        identifier = record["target_id"]
        if identifier in seen:
            errors.append(f"demonstration: duplicate example record for {identifier}")
        seen.add(identifier)
        if identifier not in by_id:
            errors.append(f"demonstration: unknown target {identifier}")
            continue
        start, end = ranges.get(by_id[identifier]["report_section"], (0, 0))
        quote = record["example_quote"]
        passage = visible[start:end]
        if passage.count(quote) != 1:
            errors.append(f"demonstration: {identifier} example must occur once in its section")
            continue
        offset = start + passage.index(quote)
        span = (offset, offset + len(quote))
        target_span = target_spans.get(identifier)
        if target_span and span[0] < target_span[1] and target_span[0] < span[1]:
            errors.append(f"demonstration: {identifier} example overlaps its target")
        example_spans.append(span)
    for identifier in by_id.keys() - seen:
        errors.append(f"demonstration: missing example for {identifier}")

    # Displayed example arithmetic belongs to its example, not a recursive new card.
    formula_spans = [
        span for identifier, span in target_spans.items() if by_id[identifier]["kind"] == "formula"
    ]
    for match in re.finditer(r"(?m)^[ \t]*\$\$[ \t]*\n[\s\S]*?\n[ \t]*\$\$[ \t]*$", visible):
        math_start = match.start() + match[0].index("$$")
        math_end = match.start() + match[0].rindex("$$") + 2
        if not any(
            start <= math_start and math_end <= end
            for start, end in formula_spans + example_spans
        ):
            line = visible[: match.start()].count("\n") + 1
            errors.append(
                f"demonstration: display formula at line {line} has no target or example owner"
            )
    return errors
