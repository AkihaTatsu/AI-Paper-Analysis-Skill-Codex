"""Conservative, token-scoped report preparation followed by the complete audit."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from .contracts import validate_instance
from .markdown_audit import (
    AuditContext,
    AuditStage,
    Diagnostic,
    _fix_mermaid_text,
    _outside_fences,
    _write_report_atomic,
    audit_markdown,
)

_MANAGED_FOOTNOTE = re.compile(r"^\[\^(apa-[a-z0-9][a-z0-9-]*)\]:.*$")
_MANAGED_SOURCE_LINK = re.compile(r"^\[(apa-source-[a-f0-9]{12})\]:.*$")
_MANAGED_MARKER = re.compile(r"\[\^(apa-[a-z0-9][a-z0-9-]*)\]")
_NUMBERED_SECTION = re.compile(r"^\s*([1-7])\.\s+")


@dataclass(frozen=True)
class ReportPreparationResult:
    path: str
    report_kind: str
    valid: bool
    changed: bool
    written: bool
    dry_run: bool
    fixes: tuple[dict[str, Any], ...]
    diagnostics: tuple[Diagnostic, ...]
    remaining: tuple[Diagnostic, ...]
    stages: tuple[AuditStage, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _protected_lines(text: str, *, inline: bool = True) -> set[int]:
    """Code and containers are preserved, including quoted/listed formulas."""

    protected: set[int] = set()
    for token in MarkdownIt("commonmark").parse(text):
        if token.map is not None and (
            token.type in {"fence", "code_block", "blockquote_open", "list_item_open"}
            or inline
            and token.type == "inline"
            and any(child.type in {"code_inline", "hardbreak"} for child in token.children or [])
        ):
            protected.update(range(*token.map))
    lines = text.splitlines()
    opening: int | None = None
    for index, line in enumerate(lines):
        if index in protected:
            continue
        if line.strip() in {"$$", r"\[", r"\]"}:
            if opening is None:
                opening = index
            else:
                protected.update(range(opening, index + 1))
                opening = None
    if opening is not None:
        protected.update(range(opening, len(lines)))
    return protected


def _literal_code_lines(text: str) -> set[int]:
    """Return lines whose trailing bytes are literal content."""

    protected: set[int] = set()
    for token in MarkdownIt("commonmark").parse(text):
        if token.map is not None and token.type in {"fence", "code_block"}:
            protected.update(range(*token.map))
    return protected


def _safe_format(text: str) -> tuple[str, list[dict[str, Any]]]:
    fixes: list[dict[str, Any]] = []
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized != text:
        fixes.append({"code": "newlines", "message": "Normalized line endings to LF"})
    text = normalized
    lines = text.splitlines()
    protected = _literal_code_lines(text)
    for index, line in enumerate(lines):
        if index in protected:
            continue
        # Preserve Markdown's explicit two-space hard break while removing the
        # accidental one-space/tabs produced by edits, including table/list rows.
        cleaned = line.rstrip("\t")
        if cleaned.endswith(" ") and not cleaned.endswith("  "):
            cleaned = cleaned[:-1]
        if cleaned != line:
            fixes.append({"code": "trailing-whitespace", "line": index + 1})
            lines[index] = cleaned

    # A blank line between consecutive ordered items changes one list into many
    # lists. Tightening it is presentation-only when numbering and indentation
    # already prove the intended sequence.
    ordered = re.compile(r"^(\s*)(\d+)\.\s+\S")
    tightened: list[str] = []
    for index, line in enumerate(lines):
        if line or index in protected or not tightened or index + 1 >= len(lines):
            tightened.append(line)
            continue
        previous = ordered.match(tightened[-1])
        following = ordered.match(lines[index + 1])
        if (
            previous
            and following
            and previous.group(1) == following.group(1)
            and int(following.group(2)) == int(previous.group(2)) + 1
        ):
            fixes.append({"code": "ordered-list-spacing", "line": index + 1})
            continue
        tightened.append(line)
    lines = tightened
    text = "\n".join(lines) + ("\n" if lines else "")

    # Only top-level ATX headings and closed fences receive blank neighbours.
    tokens = MarkdownIt("commonmark").parse(text)
    before: set[int] = set()
    after: set[int] = set()
    for token in tokens:
        if token.level != 0 or token.map is None:
            continue
        if token.type == "heading_open" and token.markup.startswith("#"):
            start, end = token.map
        elif token.type == "fence":
            start, end = token.map
            from .markdown_audit import _closed_fence

            if not _closed_fence(lines[end - 1], token.markup):
                continue
        else:
            continue
        if start > 0 and lines[start - 1].strip():
            before.add(start)
        if end < len(lines) and lines[end].strip():
            after.add(end - 1)
    if before or after:
        spaced: list[str] = []
        for index, line in enumerate(lines):
            if index in before:
                spaced.append("")
            spaced.append(line)
            if index in after and index + 1 not in before:
                spaced.append("")
        lines = spaced
        text = "\n".join(lines) + "\n"
        fixes.append({"code": "block-spacing", "message": "Separated top-level block boundaries"})

    # Join actual paragraph softbreaks only; containers, hardbreaks, formulas,
    # inline code, tables and reference/footnote definitions stay untouched.
    tokens = MarkdownIt("commonmark").parse(text)
    joins: list[tuple[int, int]] = []
    for index, token in enumerate(tokens):
        if token.type != "paragraph_open" or token.level != 0 or token.map is None:
            continue
        inline = tokens[index + 1]
        children = inline.children or []
        start, end = token.map
        raw = "\n".join(lines[start:end])
        if (
            end - start > 1
            and any(child.type == "softbreak" for child in children)
            and not any(child.type in {"hardbreak", "code_inline"} for child in children)
            and not any(character in raw for character in ("$", "\\", "|"))
            and not any(line.lstrip().startswith("[") for line in lines[start:end])
        ):
            joins.append((start, end))
    for start, end in reversed(joins):
        lines[start:end] = [" ".join(line.strip() for line in lines[start:end])]
        fixes.append({"code": "paragraph-softbreak", "line": start + 1})
    text = "\n".join(lines) + ("\n" if lines else "")
    protected = _protected_lines(text)
    compact: list[str] = []
    positions: list[int] = []
    for index, line in enumerate(lines):
        if not line and index not in protected and (not compact or compact[-1] == ""):
            fixes.append({"code": "extra-blank-line", "line": index + 1})
            continue
        compact.append(line)
        positions.append(index)
    while compact and not compact[-1] and positions[-1] not in protected:
        compact.pop()
        positions.pop()
        fixes.append({"code": "trailing-blank-line"})
    text = "\n".join(compact) + ("\n" if compact else "")
    if normalized and not normalized.endswith("\n"):
        fixes.append({"code": "final-newline", "message": "Added final newline"})
    return text, fixes


def _safe_math_delimiters(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Convert explicit paired TeX delimiters; never infer missing mathematics."""

    lines = text.splitlines()
    protected = _protected_lines(text)
    fixes: list[dict[str, Any]] = []
    inline_delimiters = re.compile(r"\\\(([^\n$]*?)\\\)")
    for index, line in enumerate(lines):
        if index in protected or "$" in line or "`" in line:
            continue
        # Ignore link destinations, escaped delimiters, and unmatched pairs.
        if "](" in line or "http" in line or "\\\\" in line:
            continue
        matches = list(inline_delimiters.finditer(line))
        if not matches or any(not match[1].strip() for match in matches):
            continue
        if line.count(r"\(") != len(matches) or line.count(r"\)") != len(matches):
            continue
        lines[index] = inline_delimiters.sub(lambda m: "$" + m[1] + "$", line)
        fixes.append({"code": "explicit-inline-math-delimiters", "line": index + 1})
    # Standalone \[ ... \] pairs are explicit display math, outside all containers.
    code_protected: set[int] = set()
    for token in MarkdownIt("commonmark").parse(text):
        if token.map is not None and token.type in {
            "fence",
            "code_block",
            "blockquote_open",
            "list_item_open",
        }:
            code_protected.update(range(*token.map))
    start: int | None = None
    for index, line in enumerate(lines):
        if index in code_protected:
            start = None
            continue
        if line.strip() == r"\[":
            start = index
        elif line.strip() == r"\]" and start is not None:
            content = "\n".join(lines[start + 1 : index])
            if content.strip() and "$" not in content and r"\[" not in content:
                lines[start] = "$$"
                lines[index] = "$$"
                fixes.append({"code": "explicit-display-math-delimiters", "line": start + 1})
            start = None
    return "\n".join(lines) + ("\n" if lines else ""), fixes


def _safe_unpaired_middle_bars(text: str) -> tuple[str, list[dict[str, Any]]]:
    r"""Replace ``\middle|`` only when a display has no matching delimiter pair."""

    lines = text.splitlines()
    literal_code = _literal_code_lines(text)
    fixes: list[dict[str, Any]] = []
    opening: int | None = None
    for index, line in enumerate(lines):
        if index in literal_code:
            continue
        if line.strip() != "$$":
            continue
        if opening is None:
            opening = index
            continue
        block = "\n".join(lines[opening + 1 : index])
        if r"\middle|" in block and not (r"\left" in block and r"\right" in block):
            count = 0
            for line_index in range(opening + 1, index):
                lines[line_index], current = re.subn(
                    r"\\middle\s*\|", r"\\vert{}", lines[line_index]
                )
                count += current
            if count:
                fixes.append(
                    {"code": "unpaired-middle-bar", "line": opening + 1, "count": count}
                )
        opening = None
    return "\n".join(lines) + ("\n" if lines else ""), fixes


def _safe_mermaid_labels(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Normalize safe label spelling only inside parsed Mermaid fences."""

    lines = text.splitlines()
    fixes: list[dict[str, Any]] = []
    for token in MarkdownIt("commonmark").parse(text):
        if token.type != "fence" or token.info.strip().lower() != "mermaid" or token.map is None:
            continue
        start, end = token.map
        for index in range(start + 1, max(start + 1, end - 1)):
            updated, count = re.subn(r"<br\s*/?>", " ", lines[index], flags=re.IGNORECASE)
            if count:
                lines[index] = updated
                fixes.append(
                    {"code": "mermaid-label-line-break", "line": index + 1, "count": count}
                )
            line = lines[index]
            # Parentheses and pipes are valid visible text but can be parsed as
            # Mermaid shape/edge syntax when a bracket label is unquoted.
            pattern = re.compile(
                r"(?P<id>\b[A-Za-z_][A-Za-z0-9_-]*)"
                r"(?P<open>[\[\{])(?P<label>[^\]\}\n\"]*[\(\)\|][^\]\}\n\"]*)"
                r"(?P<close>[\]\}])"
            )

            def quote(match: re.Match[str]) -> str:
                return (
                    f"{match.group('id')}{match.group('open')}\""
                    f"{match.group('label')}\"{match.group('close')}"
                )

            updated, count = pattern.subn(quote, line)
            if count:
                lines[index] = updated
                fixes.append({"code": "mermaid-label-quotes", "line": index + 1, "count": count})
    return "\n".join(lines) + ("\n" if lines else ""), fixes


def _safe_table_trailing_footnotes(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Move footnote markers appended after a table's closing pipe into its last cell."""

    lines = text.splitlines()
    protected = _literal_code_lines(text)
    fixes: list[dict[str, Any]] = []
    pattern = re.compile(
        r"^(?P<body>\s*\|.*\|)(?P<markers>(?:\[\^[A-Za-z0-9_-]+\])+)(?P<tail>\s*)$"
    )
    for index, line in enumerate(lines):
        if index in protected:
            continue
        match = pattern.match(line)
        if not match:
            continue
        body = match.group("body")[:-1].rstrip()
        lines[index] = f"{body} {match.group('markers')} |{match.group('tail')}"
        fixes.append({"code": "table-trailing-footnote", "line": index + 1})
    return "\n".join(lines) + ("\n" if lines else ""), fixes


_BARE_URL = re.compile(r"(?<![<(])https?://[^\s<>|]*[A-Za-z0-9/#](?=\s*(?:\||$))")


def _safe_bare_urls(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Wrap only standalone bare URLs, preserving links, definitions, HTML and code."""

    lines = text.splitlines()
    protected = _protected_lines(text)
    fixes: list[dict[str, Any]] = []
    reference_definition = re.compile(r"^\s*\[[^]]+\]:\s+")
    for index, line in enumerate(lines):
        if (
            index in protected
            or reference_definition.match(line)
            or re.search(r"\b(?:href|src)\s*=", line, re.IGNORECASE)
        ):
            continue
        lines[index], count = _BARE_URL.subn(
            lambda match: f"[{match[0]}]({match[0]})", line
        )
        if count:
            fixes.append({"code": "bare-url-autolink", "line": index + 1, "count": count})
    return "\n".join(lines) + ("\n" if lines else ""), fixes


def _evidence_footnotes(
    text: str,
    evidence_paths: tuple[Path, ...],
    publication_path: Path,
) -> tuple[str, list[dict[str, Any]], list[Diagnostic]]:
    """Regenerate only the reserved apa-* footnote namespace from evidence packets."""

    if not evidence_paths:
        return text, [], []
    from .evidence_cache import load_evidence_record

    records = [load_evidence_record(path.resolve()) for path in evidence_paths]
    locators: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for record in records:
        for locator in record["locators"]:
            identifier = locator["id"]
            if identifier in locators:
                raise ValueError(f"Duplicate evidence locator ID: {identifier}")
            locators[identifier] = (locator, record)

    lines = [
        line
        for line in text.splitlines()
        if not _MANAGED_FOOTNOTE.match(line) and not _MANAGED_SOURCE_LINK.match(line)
    ]
    body = "\n".join(lines) + ("\n" if lines else "")
    used = sorted(set(_MANAGED_MARKER.findall(body)))
    unknown = [identifier for identifier in used if identifier not in locators]
    diagnostics = [
        Diagnostic(
            "evidence.unknown-locator",
            f"Unknown generated evidence locator: {identifier}",
            "evidence",
        )
        for identifier in unknown
    ]
    if unknown:
        return text, [], diagnostics
    if not used:
        return body, [], []

    source_aliases: dict[str, tuple[str, str]] = {}
    definitions: list[str] = []
    for identifier in used:
        locator, record = locators[identifier]
        source = record["source"]
        alias = f"apa-source-{source['sha256'][:12]}"
        source_aliases[alias] = (source["label"], source["path"])
        definitions.append(
            f"[^{identifier}]: [{source['label']}][{alias}], {locator['locator']}."
        )
    references: list[str] = []
    for alias, (_, raw_path) in sorted(source_aliases.items()):
        relative = Path(os.path.relpath(Path(raw_path), start=publication_path.parent)).as_posix()
        destination = f"<{relative}>" if any(char.isspace() for char in relative) else relative
        references.append(f"[{alias}]: {destination}")
    suffix = "\n".join((*definitions, "", *references)) + "\n"
    prepared = body.rstrip("\n") + "\n\n" + suffix
    return prepared, [{"code": "evidence-footnotes", "count": len(used)}], []


def _load_contract_object(path: Path, schema_name: str, report_kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    errors = validate_instance(payload, schema_name)
    if errors:
        raise ValueError(f"Invalid {schema_name}: " + "; ".join(errors))
    if payload["report_kind"] != report_kind:
        raise ValueError(
            f"{path} is for {payload['report_kind']}, not requested report kind {report_kind}"
        )
    entries = payload["rows"] if "rows" in payload else payload["issues"]
    identifiers = [row["id"] for row in entries]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{path}: row or issue IDs must be unique")
    return payload


def _known_evidence_ids(evidence_paths: tuple[Path, ...]) -> set[str]:
    from .evidence_cache import load_evidence_record

    known: set[str] = set()
    for path in evidence_paths:
        record = load_evidence_record(path.resolve())
        for locator in record["locators"]:
            identifier = locator["id"]
            if identifier in known:
                raise ValueError(f"Duplicate evidence locator ID: {identifier}")
            known.add(identifier)
    return known


def _section_references(text: str) -> dict[int, dict[str, list[int]]]:
    """Find evidence references in numbered sections, excluding definitions and code."""

    lines = text.splitlines()
    visible, _ = _outside_fences(lines)
    starts: list[tuple[int, int]] = []
    tokens = MarkdownIt("commonmark").parse(text)
    for index, token in enumerate(tokens):
        if (
            token.type != "heading_open"
            or token.tag != "h2"
            or token.level != 0
            or token.map is None
            or index + 1 >= len(tokens)
        ):
            continue
        match = _NUMBERED_SECTION.match(tokens[index + 1].content)
        if match:
            starts.append((int(match[1]), token.map[0]))
    references: dict[int, dict[str, list[int]]] = {}
    for position, (section, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(lines)
        section_references: dict[str, list[int]] = {}
        for line_number in range(start, end):
            line = visible[line_number]
            if not line or _MANAGED_FOOTNOTE.match(line):
                continue
            line = re.sub(r"`+[^`]*`+", "", line)
            for identifier in _MANAGED_MARKER.findall(line):
                section_references.setdefault(identifier, []).append(line_number + 1)
        references[section] = section_references
    return references


def _section_ranges(text: str) -> dict[int, tuple[int, int]]:
    """Return zero-based line ranges for top-level numbered report sections."""

    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    tokens = MarkdownIt("commonmark").parse(text)
    for index, token in enumerate(tokens):
        if (
            token.type == "heading_open"
            and token.tag == "h2"
            and token.level == 0
            and token.map is not None
            and index + 1 < len(tokens)
        ):
            match = _NUMBERED_SECTION.match(tokens[index + 1].content)
            if match:
                starts.append((int(match[1]), token.map[0]))
    return {
        section: (
            start,
            starts[position + 1][1] if position + 1 < len(starts) else len(lines),
        )
        for position, (section, start) in enumerate(starts)
    }


def _anchored_coverage_diagnostics(
    text: str,
    *,
    rows: list[dict[str, Any]],
    known: set[str],
    review_patches: tuple[tuple[str, str], ...] = (),
) -> list[Diagnostic]:
    """Bind each matrix row to one concrete passage instead of a whole section."""

    lines = text.splitlines()
    visible, _ = _outside_fences(lines)
    ranges = _section_ranges(text)
    diagnostics: list[Diagnostic] = []
    heading = re.compile(r"^(#{1,6})\s+")
    for row in rows:
        owner = row["id"]
        section = row["report_section"]
        anchor = row.get("report_anchor")
        if not anchor:
            continue
        start, end = ranges.get(section, (0, 0))
        matches = [index for index in range(start, end) if anchor in visible[index]]
        if not matches:
            section_text = "\n".join(visible[start:end])
            successors = [
                new
                for old, new in review_patches
                if anchor in old and section_text.count(new) == 1
            ]
            if len(successors) == 1:
                successor = successors[0]
                local_markers = set(_MANAGED_MARKER.findall(successor))
                for identifier in row["required_locator_ids"]:
                    if identifier not in known:
                        diagnostics.append(
                            Diagnostic(
                                "coverage.unknown-locator",
                                f"{owner} requires unknown evidence locator {identifier}",
                                "coverage",
                            )
                        )
                    elif identifier not in local_markers:
                        diagnostics.append(
                            Diagnostic(
                                "coverage.missing-near-reference",
                                f"{owner} requires {identifier} in its reviewed replacement",
                                "coverage",
                            )
                        )
                continue
            other = next(
                (
                    (candidate, index + 1)
                    for candidate, (left, right) in ranges.items()
                    if candidate != section
                    for index in range(left, right)
                    if anchor in visible[index]
                ),
                None,
            )
            diagnostics.append(
                Diagnostic(
                    "coverage.wrong-anchor-section" if other else "coverage.missing-anchor",
                    (
                        f"{owner} anchor appears in section {other[0]}, not section {section}"
                        if other
                        else f"{owner} anchor is missing from section {section}: {anchor!r}"
                    ),
                    "coverage",
                    line=other[1] if other else None,
                )
            )
            continue
        if len(matches) != 1:
            diagnostics.append(
                Diagnostic(
                    "coverage.ambiguous-anchor",
                    f"{owner} anchor occurs {len(matches)} times in section {section}: {anchor!r}",
                    "coverage",
                    line=matches[0] + 1,
                )
            )
            continue
        anchor_line = matches[0]
        heading_match = heading.match(lines[anchor_line].lstrip())
        if heading_match:
            level = len(heading_match[1])
            window_end = end
            for index in range(anchor_line + 1, end):
                candidate = heading.match(lines[index].lstrip())
                if candidate and len(candidate[1]) <= level:
                    window_end = index
                    break
        elif lines[anchor_line].lstrip().startswith("|"):
            window_end = anchor_line + 1
        else:
            window_end = anchor_line + 1
            while (
                window_end < end
                and visible[window_end].strip()
                and not heading.match(lines[window_end].lstrip())
            ):
                window_end += 1
        local_markers = set(_MANAGED_MARKER.findall("\n".join(visible[anchor_line:window_end])))
        for identifier in row["required_locator_ids"]:
            if identifier not in known:
                diagnostics.append(
                    Diagnostic(
                        "coverage.unknown-locator",
                        f"{owner} requires unknown evidence locator {identifier}",
                        "coverage",
                        line=anchor_line + 1,
                    )
                )
            elif identifier not in local_markers:
                diagnostics.append(
                    Diagnostic(
                        "coverage.missing-near-reference",
                        f"{owner} requires {identifier} in the passage anchored by {anchor!r}",
                        "coverage",
                        line=anchor_line + 1,
                    )
                )
    return diagnostics


def _evidence_requirement_diagnostics(
    requirements: list[tuple[str, str, int]],
    *,
    known: set[str],
    references: dict[int, dict[str, list[int]]],
    code_prefix: str,
    stage: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for owner, identifier, section in requirements:
        if identifier not in known:
            diagnostics.append(
                Diagnostic(
                    f"{code_prefix}.unknown-locator",
                    f"{owner} requires unknown evidence locator {identifier}",
                    stage,
                )
            )
            continue
        if identifier in references.get(section, {}):
            continue
        other = next(
            (
                (number, lines[0])
                for number, values in references.items()
                if number != section and (lines := values.get(identifier))
            ),
            None,
        )
        if other:
            diagnostics.append(
                Diagnostic(
                    f"{code_prefix}.wrong-section",
                    f"{owner} requires {identifier} in section {section}; it appears in "
                    f"section {other[0]}",
                    stage,
                    line=other[1],
                )
            )
        else:
            diagnostics.append(
                Diagnostic(
                    f"{code_prefix}.missing-reference",
                    f"{owner} requires evidence reference {identifier} in section {section}",
                    stage,
                )
            )
    return diagnostics


def _coverage_diagnostics(
    text: str,
    *,
    report_kind: str,
    coverage_matrix: Path | None,
    evidence_paths: tuple[Path, ...],
    review_issues: Path | None = None,
) -> list[Diagnostic]:
    if coverage_matrix is None:
        return []
    payload = _load_contract_object(
        coverage_matrix, "coverage-matrix.schema.json", report_kind
    )
    known = _known_evidence_ids(evidence_paths)
    review_patches: tuple[tuple[str, str], ...] = ()
    if review_issues is not None:
        review_payload = _load_contract_object(
            review_issues, "review-issues.schema.json", report_kind
        )
        review_patches = tuple(
            (patch["old_text"], patch["new_text"])
            for issue in review_payload["issues"]
            if (patch := issue.get("automatic_patch")) is not None
        )
    anchored = _anchored_coverage_diagnostics(
        text,
        rows=payload["rows"],
        known=known,
        review_patches=review_patches,
    )
    legacy_requirements = [
        (row["id"], identifier, row["report_section"])
        for row in payload["rows"]
        if not row.get("report_anchor")
        for identifier in row["required_locator_ids"]
    ]
    return anchored + _evidence_requirement_diagnostics(
        legacy_requirements,
        known=known,
        references=_section_references(text),
        code_prefix="coverage",
        stage="coverage",
    )


def _review_issue_checks(
    text: str,
    *,
    report_kind: str,
    review_issues: Path | None,
    evidence_paths: tuple[Path, ...],
) -> tuple[list[str], list[Diagnostic]]:
    if review_issues is None:
        return [], []
    payload = _load_contract_object(review_issues, "review-issues.schema.json", report_kind)
    obsolete = [literal for issue in payload["issues"] for literal in issue["obsolete_literals"]]
    obsolete.extend(
        patch["old_text"]
        for issue in payload["issues"]
        if (patch := issue.get("automatic_patch")) is not None
        and patch["old_text"] not in patch["new_text"]
    )
    requirements = [
        (issue["id"], item["locator_id"], item["report_section"])
        for issue in payload["issues"]
        for item in issue["required_evidence"]
    ]
    diagnostics = _evidence_requirement_diagnostics(
        requirements,
        known=_known_evidence_ids(evidence_paths),
        references=_section_references(text),
        code_prefix="review",
        stage="review-residual",
    )
    return obsolete, diagnostics


def _apply_review_patches(
    text: str,
    *,
    report_kind: str,
    review_issues: Path | None,
    baseline_text: str | None = None,
) -> tuple[str, list[dict[str, Any]], list[Diagnostic]]:
    """Apply exact reviewer replacements with hash and occurrence guards."""

    if review_issues is None:
        return text, [], []
    payload = _load_contract_object(review_issues, "review-issues.schema.json", report_kind)
    patches = [
        (issue["id"], issue["automatic_patch"])
        for issue in payload["issues"]
        if issue.get("automatic_patch") is not None
    ]
    if not patches:
        return text, [], []
    baseline_text = text if baseline_text is None else baseline_text
    current_hash = hashlib.sha256(baseline_text.encode("utf-8")).hexdigest()
    expected_hash = payload["baseline_sha256"]
    # Once every guarded old block is gone, a later narrow repair may have
    # legitimately refined the replacement. Closure checks and the original
    # reviewer's diff continuation validate those post-patch bytes.
    already_applied = all(
        patch["new_text"] in baseline_text or patch["old_text"] not in baseline_text
        for _, patch in patches
    )
    if current_hash != expected_hash and not already_applied:
        return text, [], [
            Diagnostic(
                "review.patch-baseline-mismatch",
                f"Automatic review patches require baseline {expected_hash}, got {current_hash}",
                "review-patch",
            )
        ]
    fixes: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    for issue_id, patch in patches:
        old = patch["old_text"]
        new = patch["new_text"]
        if old == new:
            diagnostics.append(
                Diagnostic(
                    "review.patch-noop",
                    f"{issue_id} automatic patch has identical old and new text",
                    "review-patch",
                )
            )
            continue
        if new in baseline_text and new in text:
            fixes.append(
                {"code": "review-automatic-patch-already-applied", "issue_id": issue_id}
            )
            continue
        occurrences = text.count(old)
        if occurrences == 1:
            text = text.replace(old, new, 1)
            fixes.append({"code": "review-automatic-patch", "issue_id": issue_id})
        elif occurrences == 0:
            fixes.append(
                {"code": "review-automatic-patch-already-applied", "issue_id": issue_id}
            )
        else:
            diagnostics.append(
                Diagnostic(
                    "review.patch-match-count",
                    f"{issue_id} automatic patch expected one old-text match, found {occurrences}",
                    "review-patch",
                )
            )
    return text, fixes, diagnostics


def _escaped_at(line: str, position: int) -> bool:
    preceding = position
    while preceding and line[preceding - 1] == "\\":
        preceding -= 1
    return (position - preceding) % 2 == 1


_ESCAPED_MATH_PIPE = (
    r"existing \| has renderer-dependent meaning; choose \vert{} for a single bar "
    r"or \Vert{} for a double bar after reviewing the intended mathematics"
)


def _inline_math_pipes(line: str) -> tuple[list[int], str | None]:
    """Locate only complete single-dollar pairs outside matched code spans."""

    code: set[int] = set()
    ticks = list(re.finditer(r"`+", line))
    cursor = 0
    while cursor < len(ticks):
        opening_tick = ticks[cursor]
        if _escaped_at(line, opening_tick.start()):
            cursor += 1
            continue
        closing = next(
            (i for i in range(cursor + 1, len(ticks)) if ticks[i][0] == opening_tick[0]), None
        )
        if closing is None:
            cursor += 1
            continue
        code.update(range(opening_tick.start(), ticks[closing].end()))
        cursor = closing + 1
    dollars = [
        i
        for i, char in enumerate(line)
        if char == "$" and i not in code and not _escaped_at(line, i)
    ]
    if len(dollars) % 2:
        return [], "unpaired inline dollar delimiters"
    pipes: list[int] = []
    for opening, closing in zip(dollars[::2], dollars[1::2], strict=True):
        content = line[opening + 1 : closing]
        if (
            not content
            or content[0].isspace()
            or content[-1].isspace()
            or opening > 0
            and line[opening - 1] == "$"
            or closing + 1 < len(line)
            and (line[closing + 1] == "$" or line[closing + 1].isdigit())
            or any(i in code for i in range(opening, closing + 1))
        ):
            return [], "ambiguous dollar delimiters or math/code overlap"
        # GFM removes the slash in \| but arithmatex preserves it. The latter
        # feeds TeX a double-bar command, so existing escapes require review.
        if any(line[i] == "|" and line[i - 1] == "\\" for i in range(opening + 1, closing)):
            return [], _ESCAPED_MATH_PIPE
        current = [i for i in range(opening + 1, closing) if line[i] == "|" and line[i - 1] != "\\"]
        if current and re.search(
            r"\\(?:text\w*|verb\*?|mbox|hbox|begin|char|catcode|newcommand|def)\b", content
        ):
            return current, "a pipe in text, verbatim, environment or macro syntax needs review"
        pipes.extend(current)
    if pipes and ("](" in line or "][" in line or "://" in line or re.search(r"\[[^\]]*\]:", line)):
        return [], "link/reference syntax needs review before changing inline mathematics"
    return pipes, None


def _table_column_count(line: str) -> int:
    cells = re.split(r"(?<!\\)\|", line.strip())
    if cells and cells[0] == "":
        cells.pop(0)
    if cells and cells[-1] == "":
        cells.pop()
    return len(cells)


def _safe_table_math_pipes(
    text: str,
) -> tuple[str, list[dict[str, Any]], list[Diagnostic]]:
    r"""Replace math bars by explicit single-bar TeX in actual root tables.

    Both MarkdownIt/texmath and Python-Markdown/arithmatex preserve \vert{}.
    Unlike \|, it cannot acquire double-bar semantics in the second renderer.
    The empty group terminates the command before adjacent letters. Never infer
    the meaning of existing escaped pipes or missing math/cell delimiters.
    """

    lines = text.splitlines()
    protected = _protected_lines(text, inline=False)
    fixes: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    for token in MarkdownIt("commonmark").enable("table").parse(text):
        if token.type != "table_open" or token.level != 0 or token.map is None:
            continue
        start, end = token.map
        columns = _table_column_count(lines[start])
        for index in range(start, end):
            if index in protected or index == start + 1:
                continue
            line = lines[index]
            positions, reason = _inline_math_pipes(line)
            if (
                reason
                and reason != _ESCAPED_MATH_PIPE
                and not positions
                and _table_column_count(line) <= columns
            ):
                # An unrelated dollar spelling without extra separators is not
                # this repair's responsibility (e.g. currency or inline $$).
                reason = None
            candidate = line
            if positions:
                positions_set = set(positions)
                candidate = "".join(
                    r"\vert{}" if i in positions_set else char for i, char in enumerate(line)
                )
                if _table_column_count(candidate) != columns:
                    reason = "replacing math pipes does not restore the declared table column count"
            if reason:
                diagnostics.append(
                    Diagnostic(
                        "table.math-pipe-ambiguous",
                        f"Table row left unchanged: {reason}; review its math and cell delimiters",
                        "prepare",
                        line=index + 1,
                    )
                )
            elif positions:
                lines[index] = candidate
                fixes.append(
                    {"code": "table-inline-math-pipes", "line": index + 1, "count": len(positions)}
                )
    return "\n".join(lines) + ("\n" if lines else ""), fixes, diagnostics


def prepare_report(
    path: Path,
    *,
    report_kind: str = "paper",
    dry_run: bool = False,
    publication_path: Path | None = None,
    context: AuditContext | None = None,
    render: bool = False,
    evidence_paths: tuple[Path, ...] = (),
    forbidden_literals: tuple[str, ...] = (),
    coverage_matrix: Path | None = None,
    review_issues: Path | None = None,
) -> ReportPreparationResult:
    """Apply safe presentation fixes and report all remaining technical failures.

    A successful technical audit does not establish the report's semantic accuracy.
    Dry runs audit the proposed bytes without changing the original report.
    """

    path = path.resolve()
    original = path.read_bytes()
    original_text = original.decode("utf-8")
    started = time.perf_counter()
    text, evidence_fixes, evidence_diagnostics = _evidence_footnotes(
        original_text, evidence_paths, (publication_path or path).resolve()
    )
    text, fixes = _safe_format(text)
    fixes[:0] = evidence_fixes
    text, math_fixes = _safe_math_delimiters(text)
    fixes.extend(math_fixes)
    text, middle_bar_fixes = _safe_unpaired_middle_bars(text)
    fixes.extend(middle_bar_fixes)
    text, table_footnote_fixes = _safe_table_trailing_footnotes(text)
    fixes.extend(table_footnote_fixes)
    text, bare_url_fixes = _safe_bare_urls(text)
    fixes.extend(bare_url_fixes)
    text, mermaid_label_fixes = _safe_mermaid_labels(text)
    fixes.extend(mermaid_label_fixes)
    text, pipe_fixes, pipe_diagnostics = _safe_table_math_pipes(text)
    fixes.extend(pipe_fixes)
    preparation_elapsed = time.perf_counter() - started
    patch_started = time.perf_counter()
    text, patch_fixes, patch_diagnostics = _apply_review_patches(
        text,
        report_kind=report_kind,
        review_issues=review_issues,
        baseline_text=original_text,
    )
    fixes.extend(patch_fixes)
    patch_stage = AuditStage(
        "review-patch",
        "failed" if patch_diagnostics else ("passed" if review_issues else "skipped"),
        time.perf_counter() - patch_started,
        None if review_issues else "no review issue file supplied",
    )
    coverage_started = time.perf_counter()
    coverage_diagnostics = _coverage_diagnostics(
        text,
        report_kind=report_kind,
        coverage_matrix=coverage_matrix,
        evidence_paths=evidence_paths,
        review_issues=review_issues,
    )
    coverage_stage = AuditStage(
        "coverage",
        "failed" if coverage_diagnostics else ("passed" if coverage_matrix else "skipped"),
        time.perf_counter() - coverage_started,
        None if coverage_matrix else "no coverage matrix supplied",
    )
    review_started = time.perf_counter()
    issue_literals, review_diagnostics = _review_issue_checks(
        text,
        report_kind=report_kind,
        review_issues=review_issues,
        evidence_paths=evidence_paths,
    )
    all_forbidden_literals = tuple(dict.fromkeys((*forbidden_literals, *issue_literals)))
    literal_diagnostics = [
        Diagnostic(
            "review.residual-literal",
            f"Resolved review literal is still present: {literal!r}",
            "review-residual",
        )
        for literal in all_forbidden_literals
        if literal and literal in text
    ]
    review_stage = AuditStage(
        "review-residual",
        "failed"
        if literal_diagnostics or review_diagnostics
        else ("passed" if review_issues or forbidden_literals else "skipped"),
        time.perf_counter() - review_started,
        None if review_issues or forbidden_literals else "no review issue checks supplied",
    )
    mermaid_started = time.perf_counter()
    context = context or AuditContext()
    _, blocks = _outside_fences(text.splitlines())
    notes: list[Diagnostic] = [
        *evidence_diagnostics,
        *patch_diagnostics,
        *pipe_diagnostics,
        *literal_diagnostics,
        *coverage_diagnostics,
        *review_diagnostics,
    ]
    if not pipe_diagnostics and blocks:
        try:
            text, records = _fix_mermaid_text(text, context=context)
            fixes.extend(
                {
                    "code": "mermaid-direction",
                    "line": record["line"],
                    "direction": record["layout"]["recommended"],
                }
                for record in records
                if record.get("layout", {}).get("changed")
            )
        except ValueError:
            # The audit below reuses the same checker records and reports the
            # underlying syntax/layout defect once with its source location.
            pass
    preparation_elapsed += time.perf_counter() - mermaid_started
    preparation = AuditStage(
        "prepare", "failed" if pipe_diagnostics else "passed", preparation_elapsed
    )
    updated = text.encode("utf-8")
    changed = updated != original
    with tempfile.TemporaryDirectory(prefix="ai-paper-analysis-prepare-") as workspace:
        candidate = Path(workspace) / path.name
        candidate.write_bytes(updated)
        audit = audit_markdown(
            candidate,
            report_kind=report_kind,
            publication_path=publication_path or path,
            context=context,
            full_render=render,
        )
    if changed and not dry_run:
        _write_report_atomic(path, original, updated)
    return ReportPreparationResult(
        path=str(path),
        report_kind=report_kind,
        valid=(
            audit.valid
            and not pipe_diagnostics
            and not evidence_diagnostics
            and not patch_diagnostics
            and not literal_diagnostics
            and not coverage_diagnostics
            and not review_diagnostics
        ),
        changed=changed,
        written=changed and not dry_run,
        dry_run=dry_run,
        fixes=tuple(fixes),
        diagnostics=tuple(notes) + audit.diagnostics,
        remaining=(
            tuple(evidence_diagnostics)
            + tuple(patch_diagnostics)
            + tuple(pipe_diagnostics)
            + tuple(literal_diagnostics)
            + tuple(coverage_diagnostics)
            + tuple(review_diagnostics)
            + audit.diagnostics
        ),
        stages=(
            preparation,
            patch_stage,
            coverage_stage,
            review_stage,
            *audit.stages,
            AuditStage("semantic-review", "skipped", 0, "requires source-grounded review"),
        ),
    )
