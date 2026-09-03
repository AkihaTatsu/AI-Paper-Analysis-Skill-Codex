"""Portable Markdown, mathematics, Mermaid, and report-structure audits."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path
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


def _outside_fences(lines: list[str]) -> tuple[list[str], list[tuple[int, str]]]:
    visible: list[str] = []
    mermaid_blocks: list[tuple[int, str]] = []
    fence: str | None = None
    language = ""
    buffer: list[str] = []
    start = 0
    for number, line in enumerate(lines, start=1):
        match = re.match(r"^(`{3,}|~{3,})([^`]*)$", line.rstrip())
        if fence is None and match:
            fence = match.group(1)
            language = match.group(2).strip().lower()
            buffer = []
            start = number
            visible.append("")
            continue
        if fence is not None:
            if re.match(rf"^{re.escape(fence[0])}{{{len(fence)},}}\s*$", line):
                if language == "mermaid":
                    mermaid_blocks.append((start, "\n".join(buffer)))
                fence = None
                language = ""
            else:
                buffer.append(line)
            visible.append("")
            continue
        visible.append(line)
    if fence is not None:
        visible.append(f"APA_UNCLOSED_FENCE_AT_{start}")
    return visible, mermaid_blocks


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


def _extract_graph(code: str) -> tuple[str, set[str], list[tuple[str, str]], bool]:
    lines = code.splitlines()
    direction = ""
    if lines:
        match = re.match(r"\s*(?:flowchart|graph)\s+(TB|TD|BT|LR|RL)\b", lines[0])
        if match:
            direction = "TB" if match.group(1) == "TD" else match.group(1)
    nodes: set[str] = set()
    edges: list[tuple[str, str]] = []
    node_pattern = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\[|\(|\{|$)")
    edge_pattern = re.compile(
        r"([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\[[^]]*\]|\([^)]*\)|\{[^}]*\})?\s*"
        r"(?:-->|---|-.->|==>)\s*([A-Za-z_][A-Za-z0-9_-]*)"
    )
    for line in lines[1:]:
        if node_match := node_pattern.match(line):
            nodes.add(node_match.group(1))
        for left, right in edge_pattern.findall(line):
            nodes.update((left, right))
            edges.append((left, right))
    has_subgraph = any(re.match(r"\s*subgraph\b", line) for line in lines)
    return direction, nodes, edges, has_subgraph


def _graph_metrics(nodes: set[str], edges: list[tuple[str, str]]) -> tuple[bool, int, int]:
    outgoing: dict[str, list[str]] = defaultdict(list)
    indegree = {node: 0 for node in nodes}
    degree = Counter({node: 0 for node in nodes})
    for left, right in edges:
        outgoing[left].append(right)
        indegree[right] = indegree.get(right, 0) + 1
        indegree.setdefault(left, 0)
        degree[left] += 1
        degree[right] += 1
    queue = deque(node for node, value in indegree.items() if value == 0)
    distances = {node: 1 for node in nodes}
    visited = 0
    while queue:
        node = queue.popleft()
        visited += 1
        for child in outgoing[node]:
            distances[child] = max(distances.get(child, 1), distances[node] + 1)
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    acyclic = visited == len(indegree)
    longest_chain = max(distances.values(), default=0) if acyclic else len(nodes)
    maximum_degree = max(degree.values(), default=0)
    return acyclic, longest_chain, maximum_degree


def _mermaid_errors(blocks: list[tuple[int, str]], *, require_module_subgraphs: bool) -> list[str]:
    errors: list[str] = []
    for line_number, code in blocks:
        direction, nodes, edges, has_subgraph = _extract_graph(code)
        if direction not in {"TB", "LR"}:
            errors.append(f"line {line_number}: Mermaid graph must declare TB or LR")
            continue
        acyclic, longest_chain, maximum_degree = _graph_metrics(nodes, edges)
        lr_allowed = len(nodes) <= 6 and longest_chain <= 4 and acyclic and maximum_degree <= 2
        if direction == "LR" and not lr_allowed:
            errors.append(
                f"line {line_number}: graph is too complex for LR; use TB "
                f"(nodes={len(nodes)}, longest_chain={longest_chain}, "
                f"acyclic={acyclic}, max_degree={maximum_degree})"
            )
        if require_module_subgraphs and len(nodes) > 2 and not has_subgraph:
            errors.append(f"line {line_number}: module flow must use at least one subgraph")
        if "<" in code or ">" in code.replace("-->", "").replace("==>", ""):
            errors.append(f"line {line_number}: Mermaid labels must not contain raw HTML")
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


def _mermaid_syntax_audit(
    blocks: list[tuple[int, str]],
) -> tuple[list[str], list[str]]:
    """Validate Mermaid with the official parser when its local runtime is available."""

    if not blocks:
        return [], []
    node = shutil.which("node")
    checker = _mermaid_checker_path()
    if node is None or checker is None:
        missing = "Node.js" if node is None else "the Mermaid checker script"
        return [f"official Mermaid syntax check unavailable: {missing}"], []
    payload = {"blocks": [{"line": line_number, "code": code} for line_number, code in blocks]}
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
        return [f"official Mermaid syntax check failed to run: {error}"], []
    if completed.returncode:
        detail = " ".join((completed.stderr or completed.stdout).split())[:500]
        suffix = f": {detail}" if detail else ""
        return [f"official Mermaid syntax parser failed{suffix}"], []
    try:
        result = json.loads(completed.stdout)
        records = result["results"]
        if not isinstance(records, list) or len(records) != len(blocks):
            raise ValueError("result count does not match Mermaid block count")
        if any(
            not isinstance(record, dict) or not isinstance(record.get("valid"), bool)
            for record in records
        ):
            raise ValueError("result records must contain a Boolean valid field")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        return [f"official Mermaid syntax parser returned invalid output ({error})"], []

    errors: list[str] = []
    for record in records:
        if not isinstance(record, dict) or record.get("valid") is not False:
            continue
        fence_line = record.get("line")
        parser_line = record.get("parser_line")
        line_number = fence_line if isinstance(fence_line, int) else "?"
        if isinstance(line_number, int) and isinstance(parser_line, int) and parser_line > 0:
            line_number += parser_line
        message = " ".join(str(record.get("message") or "parse error").split())[:500]
        errors.append(f"line {line_number}: invalid Mermaid syntax: {message}")
    return errors, []


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
    errors.extend(_mermaid_errors(mermaid_blocks, require_module_subgraphs=report_kind == "paper"))
    mermaid_syntax_errors, warnings = _mermaid_syntax_audit(mermaid_blocks)
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
