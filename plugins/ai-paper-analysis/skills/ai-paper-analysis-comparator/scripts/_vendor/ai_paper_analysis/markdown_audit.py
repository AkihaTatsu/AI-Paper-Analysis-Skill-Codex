"""Portable Markdown, mathematics, Mermaid, and report-structure audits."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt

MERMAID_CHECK_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class MarkdownAudit:
    valid: bool
    path: str
    report_kind: str
    display_formula_count: int
    mermaid_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _closed_fence(line: str, markup: str) -> bool:
    # CommonMark container prefixes may precede a closing fence.
    return bool(re.fullmatch(rf"[ >\t]*{re.escape(markup[0])}{{{len(markup)},}}\s*", line))


def _outside_fences(lines: list[str]) -> tuple[list[str], list[tuple[int, str]]]:
    visible = lines.copy()
    blocks: list[tuple[int, str]] = []
    for token in MarkdownIt("commonmark").parse("\n".join(lines)):
        if token.type not in {"fence", "code_block"} or token.map is None:
            continue
        start, end = token.map
        visible[start:end] = [""] * (end - start)
        if token.type == "fence":
            if token.info.strip().lower() == "mermaid":
                blocks.append((start + 1, token.content))
            if end <= start + 1 or not _closed_fence(lines[end - 1], token.markup):
                visible[start] = f"APA_UNCLOSED_FENCE_AT_{start + 1}"
    return visible, blocks


def _strip_inline_code(line: str) -> str:
    return re.sub(r"`+[^`]*`+", "", line)


def _unescaped_dollars(line: str) -> list[int]:
    positions: list[int] = []
    for index, character in enumerate(line):
        if character != "$":
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and line[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            positions.append(index)
    return positions


_MARKDOWN_LINK = re.compile(r"!?\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")
_FOOTNOTE_MARKER = re.compile(r"\[\^[^\]]+\]")
_AUTOLINK = re.compile(r"<(?:https?://|mailto:)[^>]+>")
_BARE_TEX_COMMAND = re.compile(r"\\[A-Za-z]+")
_BARE_SCRIPTED_SYMBOL = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]|[\u0370-\u03ff\u1f00-\u1fff])"
    r"(?:[_^](?:\{[^{}\n]+\}|[A-Za-z0-9]))"
)
_PARENTHESIZED_FRAGMENT = re.compile(r"\(([^()\n]{1,80})\)")
_MATH_PUNCTUATION = frozenset("+-*/=<>^_,[]{}≤≥≈±×÷−")
_FIGURE_PANEL_LABELS = frozenset("abcd")


def _mask_inline_math(line: str) -> str:
    characters = list(line)
    dollars = _unescaped_dollars(line)
    for left, right in zip(dollars[::2], dollars[1::2], strict=False):
        characters[left : right + 1] = " " * (right - left + 1)
    return "".join(characters)


def _looks_like_bare_parenthesized_math(fragment: str, *, table_row: bool) -> bool:
    compact = fragment.strip()
    if compact in {"K", "N"}:
        return True
    if (
        table_row
        and len(compact) == 1
        and compact.isalpha()
        and compact.lower() not in _FIGURE_PANEL_LABELS
    ):
        return True
    if not any(character in _MATH_PUNCTUATION for character in compact):
        return False
    if re.search(r"[A-Za-z]{2,}", compact):
        return False
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9\s.,+\-*/=<>^_{}\[\]\\≤≥≈±×÷−]+",
            compact,
        )
    )


def _bare_math_error(line: str, number: int) -> str | None:
    visible = _strip_inline_code(line)
    visible = _MARKDOWN_LINK.sub(r"\1", visible)
    visible = _FOOTNOTE_MARKER.sub("", visible)
    visible = _AUTOLINK.sub("", visible)
    visible = _mask_inline_math(visible)

    match = _BARE_TEX_COMMAND.search(visible) or _BARE_SCRIPTED_SYMBOL.search(visible)
    if match is not None:
        fragment = match.group(0)
        return (
            f"line {number}: probable bare mathematics {fragment!r}; "
            "use $...$ for math or backticks for code"
        )

    table_row = visible.lstrip().startswith("|")
    for match in _PARENTHESIZED_FRAGMENT.finditer(visible):
        if _looks_like_bare_parenthesized_math(match.group(1), table_row=table_row):
            return (
                f"line {number}: probable bare mathematics {match.group(0)!r}; "
                "use $...$ for math or backticks for code"
            )
    return None


def _math_errors(lines: list[str]) -> tuple[list[str], int]:
    errors: list[str] = []
    display_open_at: int | None = None
    display_content = False
    display_count = 0
    for number, raw in enumerate(lines, start=1):
        line = _strip_inline_code(raw)
        if "\\(" in line or "\\)" in line or "\\[" in line or "\\]" in line:
            errors.append(f"line {number}: only $ and $$ mathematical delimiters are allowed")
        if line.strip() == "$$":
            if display_open_at is None:
                display_open_at = number
                display_content = False
            else:
                if not display_content:
                    errors.append(f"line {display_open_at}: empty display-math block")
                display_open_at = None
                display_count += 1
            continue
        if "$$" in line:
            errors.append(f"line {number}: $$ delimiters must be on standalone lines")
        if display_open_at is not None:
            if line.strip():
                display_content = True
            continue
        dollars = _unescaped_dollars(line)
        if len(dollars) % 2:
            errors.append(
                f"line {number}: unbalanced inline $ delimiter or unescaped currency sign"
            )
        for left, right in zip(dollars[::2], dollars[1::2], strict=False):
            if not line[left + 1 : right].strip():
                errors.append(f"line {number}: empty inline-math span")
        if bare_math_error := _bare_math_error(line, number):
            errors.append(bare_math_error)
    if display_open_at is not None:
        errors.append(f"line {display_open_at}: unclosed display-math block")
    return errors, display_count


def _heading_errors(lines: list[str]) -> list[str]:
    errors: list[str] = []
    headings: list[tuple[int, int, str]] = []
    for number, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        headings.append((number, level, title))
        if number > 1 and lines[number - 2].strip():
            errors.append(f"line {number}: heading must be preceded by a blank line")
        if number < len(lines) and lines[number].strip():
            errors.append(f"line {number}: heading must be followed by a blank line")
    if not headings or headings[0][1] != 1 or headings[0][0] != 1:
        errors.append("document must start with exactly one level-one ATX heading")
    if sum(level == 1 for _, level, _ in headings) != 1:
        errors.append("document must contain exactly one level-one heading")
    duplicates = [
        title for title, count in Counter(title for _, _, title in headings).items() if count > 1
    ]
    if duplicates:
        errors.append(f"duplicate headings are not portable: {duplicates}")
    previous_level = 0
    for number, level, _ in headings:
        if previous_level and level > previous_level + 1:
            errors.append(f"line {number}: heading level skips from {previous_level} to {level}")
        previous_level = level
    return errors


def _mermaid_checker_path() -> Path | None:
    configured = os.environ.get("APA_RENDERER_ROOT")
    roots = [Path(configured).resolve()] if configured else []
    source = Path(__file__).resolve()
    roots.extend((source.parent / "_data" / "renderer", source.parents[2]))
    for base in roots:
        for candidate in (base / "check_mermaid.mjs", base / "scripts" / "check_mermaid.mjs"):
            if candidate.is_file():
                return candidate
    return None


def _renderer_script_path() -> Path | None:
    configured = os.environ.get("APA_RENDERER_ROOT")
    roots = [Path(configured).resolve()] if configured else []
    source = Path(__file__).resolve()
    roots.extend((source.parent / "_data" / "renderer", source.parents[2]))
    for base in roots:
        candidate = base / "scripts" / "render_report.mjs"
        if candidate.is_file():
            return candidate
    return None


def _mermaid_check_records(blocks: list[tuple[int, str]]) -> list[dict[str, Any]]:
    """Return official syntax and pure layout estimates through one Node process."""

    if not blocks:
        return []
    node = shutil.which("node")
    checker = _mermaid_checker_path()
    if node is None or checker is None:
        missing = "Node.js" if node is None else "the Mermaid checker script"
        raise ValueError(f"official Mermaid syntax check unavailable: {missing}")
    payload = {
        "blocks": [{"line": line_number, "code": code} for line_number, code in blocks],
        "layout": True,
    }
    try:
        completed = subprocess.run(
            [node, str(checker)],
            input=json.dumps(payload),
            capture_output=True,
            check=False,
            text=True,
            timeout=MERMAID_CHECK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"official Mermaid syntax check failed to run: {error}") from error
    if completed.returncode:
        detail = " ".join((completed.stderr or completed.stdout).split())[:500]
        raise ValueError(f"official Mermaid syntax parser failed: {detail}")
    try:
        result = json.loads(completed.stdout)
        records = result["results"]
        if not isinstance(records, list) or len(records) != len(blocks):
            raise ValueError("result count does not match Mermaid block count")
        for record, (line, _) in zip(records, blocks, strict=True):
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("valid"), bool)
                or record.get("line") != line
            ):
                raise ValueError(
                    "result records must contain matching lines and Boolean valid fields"
                )
        return records
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(
            f"official Mermaid syntax parser returned invalid output ({error})"
        ) from error


def _record_errors(record: dict[str, Any], *, enforce_direction: bool) -> list[str]:
    line = record["line"]
    if not record["valid"]:
        parser_line = record.get("parser_line")
        if isinstance(parser_line, int) and parser_line > 0:
            line += parser_line
        message = " ".join(str(record.get("message") or "parse error").split())[:500]
        return [f"line {line}: invalid Mermaid syntax: {message}"]
    if record.get("layout_error"):
        return [f"line {line}: Mermaid layout estimation failed: {record['layout_error']}"]
    layout = record.get("layout")
    if not isinstance(layout, dict):
        return [f"line {line}: Mermaid layout estimate unavailable"]
    if layout.get("skipped"):
        return []
    try:
        if layout["current"] not in {"TB", "TD", "LR"} or layout["recommended"] not in {"TB", "LR"}:
            raise ValueError("invalid direction")
        if not isinstance(layout["changed"], bool) or not isinstance(
            layout["direction_offset"], int
        ):
            raise ValueError("invalid change or source offset")
        if layout["changed"] != (
            ("TB" if layout["current"] == "TD" else layout["current"]) != layout["recommended"]
        ):
            raise ValueError("inconsistent direction change")
        if not isinstance(layout["sizes"], dict):
            raise ValueError("invalid sizes object")
        for size in layout["sizes"].values():
            if not isinstance(size, dict):
                raise ValueError("invalid size object")
            if any(
                not isinstance(size[key], (int, float)) or not 0 <= size[key] < float("inf")
                for key in ("width", "height")
            ):
                raise ValueError("invalid dimensions")
        tb, lr = layout["sizes"]["TB"], layout["sizes"]["LR"]
    except (KeyError, TypeError, ValueError) as error:
        return [f"line {line}: invalid Mermaid layout estimate ({error})"]
    if enforce_direction and layout["changed"]:
        return [
            f"line {line}: Mermaid direction should be {layout['recommended']}; "
            f"estimated TB={tb['width']:g} x {tb['height']:g}, "
            f"LR={lr['width']:g} x {lr['height']:g}; run fix-mermaid-direction"
        ]
    return []


def _mermaid_syntax_audit(
    blocks: list[tuple[int, str]], *, require_module_subgraphs: bool = False
) -> tuple[list[str], list[str]]:
    """Check syntax and estimated direction without modifying the report."""

    try:
        records = _mermaid_check_records(blocks)
    except ValueError as error:
        return [str(error)], []
    errors = [
        error for record in records for error in _record_errors(record, enforce_direction=True)
    ]
    for record in records:
        layout = record.get("layout")
        if not isinstance(layout, dict):
            continue
        if layout.get("skipped"):
            errors.append(f"line {record['line']}: Mermaid graph must declare TB or LR")
        if (
            require_module_subgraphs
            and isinstance(layout.get("node_count"), int)
            and layout["node_count"] > 2
            and not layout.get("has_subgraph")
        ):
            errors.append(f"line {record['line']}: module flow must use at least one subgraph")
    return errors, []


def fix_mermaid_direction(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    """Atomically replace only top-level direction tokens in one Markdown file."""

    path = path.resolve()
    original = path.read_bytes()
    text = original.decode("utf-8")
    lines = text.splitlines(keepends=True)
    tokens = MarkdownIt("commonmark").parse(text)
    blocks: list[tuple[int, str]] = []
    starts: list[int] = []
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    for token in tokens:
        if token.type != "fence" or token.info.strip().lower() != "mermaid" or token.map is None:
            continue
        start, end = token.map
        if end <= start + 1 or not _closed_fence(lines[end - 1], token.markup):
            raise ValueError(f"line {start + 1}: unclosed Mermaid fence")
        blocks.append((start + 1, token.content))
        starts.append(start + 1)
    records = _mermaid_check_records(blocks)
    errors = [
        error for record in records for error in _record_errors(record, enforce_direction=False)
    ]
    if errors:
        raise ValueError("; ".join(errors))
    edits: list[tuple[int, int, str]] = []
    for record, (_, code), start in zip(records, blocks, starts, strict=True):
        layout = record["layout"]
        if layout.get("skipped") or not layout["changed"]:
            continue
        unit_offset = layout["direction_offset"]
        if unit_offset < 0:
            raise ValueError("Invalid Mermaid source offset")
        offset = len(code.encode("utf-16-le")[: unit_offset * 2].decode("utf-16-le"))
        current = layout["current"]
        if code[offset : offset + len(current)] != current:
            raise ValueError("Mermaid source direction does not match the analyzed token")
        before = code[:offset]
        source_line = start + before.count("\n")
        content_line = code.splitlines()[before.count("\n")]
        column = len(before.rsplit("\n", 1)[-1])
        prefix = lines[source_line].find(content_line)
        if prefix < 0:
            raise ValueError("Cannot map the parsed Mermaid direction to its source line")
        source_offset = offsets[source_line] + prefix + column
        edits.append((source_offset, source_offset + len(current), layout["recommended"]))
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    if edits and not dry_run:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".updating", dir=path.parent
        )
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(text.encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
            shutil.copymode(path, temporary)
            if path.read_bytes() != original:
                raise ValueError(
                    "Report changed during analysis; refusing to overwrite newer content"
                )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {
        "path": str(path),
        "dry_run": dry_run,
        "changed": bool(edits),
        "written": bool(edits) and not dry_run,
        "results": records,
    }


def _full_renderer_errors(path: Path) -> list[str]:
    node = shutil.which("node")
    renderer = _renderer_script_path()
    if node is None or renderer is None:
        missing = "Node.js" if node is None else "the full renderer script"
        return [f"full Markdown renderer unavailable: {missing}"]
    try:
        completed = subprocess.run(
            [node, str(renderer), str(path.resolve())],
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return [f"full Markdown renderer failed to run: {error}"]
    if completed.returncode:
        detail = " ".join((completed.stderr or completed.stdout).split())[:1000]
        return [f"full Markdown renderer failed: {detail or 'unknown renderer error'}"]
    return []


def _relative_link_errors(path: Path, text: str) -> list[str]:
    if "templates" in path.parts:
        return []
    errors: list[str] = []
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for destination in pattern.findall(text):
        raw = destination.strip().strip("<>").split(maxsplit=1)[0]
        parsed = urlparse(raw)
        if not raw or raw.startswith("#") or parsed.scheme or parsed.netloc:
            continue
        candidate = (path.parent / unquote(parsed.path)).resolve()
        if not candidate.exists():
            errors.append(f"relative link target does not exist: {raw}")
    return errors


def _portable_syntax_errors(lines: list[str]) -> list[str]:
    errors: list[str] = []
    text = "\n".join(lines)
    if lines and lines[0].strip() == "---":
        errors.append("YAML front matter is not part of the portable profile")
    if "[[" in text or "]]" in text:
        errors.append("Wikilinks are not permitted")
    for number, line in enumerate(lines, start=1):
        if re.match(r"^\s*(?:!!!|\?\?\?)\s", line):
            errors.append(f"line {number}: renderer-specific admonitions are not permitted")
        if re.search(r"<[A-Za-z][^>]*>", line):
            errors.append(f"line {number}: raw HTML is not permitted")
        if line.rstrip() != line:
            errors.append(f"line {number}: trailing whitespace is not permitted")
    if "APA_UNCLOSED_FENCE_AT_" in text:
        marker = re.search(r"APA_UNCLOSED_FENCE_AT_(\d+)", text)
        errors.append(f"line {marker.group(1) if marker else '?'}: unclosed code fence")
    return errors


def _section_errors(lines: list[str], report_kind: str) -> list[str]:
    if report_kind == "paper":
        required = range(1, 8)
    elif report_kind == "category":
        required = range(1, 4)
    else:
        return []
    errors: list[str] = []
    for section in required:
        if not any(re.match(rf"^##\s+{section}[.)]\s+", line) for line in lines):
            errors.append(f"missing numbered level-two section {section}")
    return errors


def audit_markdown(path: Path, *, report_kind: str = "generic") -> MarkdownAudit:
    """Audit one Markdown report against the approved portable profile."""

    text = path.read_text(encoding="utf-8")
    newline_errors = ["document must use LF newlines"] if "\r" in text else []
    lines = text.splitlines()
    visible, mermaid_blocks = _outside_fences(lines)
    errors = newline_errors
    errors.extend(_portable_syntax_errors(visible))
    errors.extend(_heading_errors(visible))
    math_errors, formula_count = _math_errors(visible)
    errors.extend(math_errors)
    mermaid_syntax_errors, warnings = _mermaid_syntax_audit(
        mermaid_blocks, require_module_subgraphs=report_kind == "paper"
    )
    errors.extend(mermaid_syntax_errors)
    errors.extend(_section_errors(visible, report_kind))
    errors.extend(_relative_link_errors(path, text))
    try:
        MarkdownIt("commonmark", {"html": False}).parse(text)
    except Exception as error:
        errors.append(f"CommonMark parser failed: {error}")
    if report_kind in {"paper", "category"}:
        errors.extend(_full_renderer_errors(path))
    return MarkdownAudit(
        valid=not errors,
        path=str(path),
        report_kind=report_kind,
        display_formula_count=formula_count,
        mermaid_count=len(mermaid_blocks),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
