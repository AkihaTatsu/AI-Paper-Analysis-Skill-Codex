"""Data-driven prose candidates and content-bound review exceptions."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .contracts import load_json


def validate_rules(payload: dict[str, Any]) -> list[str]:
    """Validate the small bilingual rule format and its executable matchers."""
    errors: list[str] = []
    identifiers: set[str] = set()
    if payload.get("schema_version") != "1.0.0":
        errors.append("unsupported prose rules schema_version")
    if payload.get("supported_languages") != ["zh", "en"]:
        errors.append("prose rules must support zh and en")
    if payload.get("scope") != "visible_report_text":
        errors.append("prose rules must target visible_report_text")
    if set(payload.get("bibliography_fields", {})) != {"zh", "en"}:
        errors.append("bibliography field labels must cover zh and en")
    for rule in payload.get("rules", []):
        identifier = rule.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            errors.append(f"missing or duplicate prose rule ID: {identifier}")
        identifiers.add(str(identifier))
        check = rule.get("check")
        if check not in {"regex", "pairs", "repeated_sentence", "heading_echo"}:
            errors.append(f"{identifier}: unknown check {check}")
        for field in ("category", "message", "repair", "keep_when"):
            if not isinstance(rule.get(field), str) or not rule[field].strip():
                errors.append(f"{identifier}: missing {field}")
        languages = rule.get("languages", {})
        if set(languages) != {"zh", "en"}:
            errors.append(f"{identifier}: both zh and en entries are required")
        for language, entry in languages.items():
            if entry.get("applicable") is False:
                if not str(entry.get("reason", "")).strip():
                    errors.append(f"{identifier}/{language}: inapplicable rules need a reason")
                continue
            if entry.get("applicable") is not True:
                errors.append(f"{identifier}/{language}: applicable must be boolean")
            patterns = entry.get("patterns", [])
            if check == "regex" and not patterns:
                errors.append(f"{identifier}/{language}: patterns are required")
            for pattern in patterns:
                try:
                    compiled = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    if compiled.match(""):
                        errors.append(f"{identifier}/{language}: empty matches are forbidden")
                except (re.error, TypeError) as error:
                    errors.append(f"{identifier}/{language}: invalid regex: {error}")
            if check == "pairs" and not entry.get("pairs"):
                errors.append(f"{identifier}/{language}: punctuation pairs are required")
            for pair in entry.get("pairs", []):
                if len(pair) != 2 or any(not isinstance(c, str) or len(c) != 1 for c in pair):
                    errors.append(f"{identifier}/{language}: invalid punctuation pair")
            if check == "repeated_sentence" and (
                not isinstance(entry.get("minimum_length"), int) or entry["minimum_length"] < 1
            ):
                errors.append(f"{identifier}/{language}: positive minimum_length required")
    if not identifiers:
        errors.append("prose rules must not be empty")
    return errors


def _visible(text: str, bibliography_fields: list[str]) -> tuple[str, list[int]]:
    """Project prose to text while retaining original byte-independent offsets."""
    hidden: list[tuple[int, int]] = []
    removed: list[tuple[int, int]] = []
    from markdown_it import MarkdownIt

    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    for token in MarkdownIt("commonmark").parse(text):
        if token.type not in {"fence", "code_block"} or token.map is None:
            continue
        start, end = token.map
        if token.type == "fence" and token.info.strip().lower() == "mermaid":
            for index in range(start, end):
                line, offset = lines[index], offsets[index]
                cursor = 0
                labels = re.finditer(
                    r'"([^"\n]*)"|\[([^\]\n]*)\]|\|([^|\n]+)\|'
                    r"|\bsubgraph\s+\w+\s+(.+)|\{([^}\n]+)\}"
                    r"|\(([^()\n]+)\)|--+\s+(.+?)\s+--+>",
                    line,
                )
                for label in labels:
                    group = next(i for i in range(1, 8) if label.group(i) is not None)
                    left, right = label.span(group)
                    hidden.append((offset + cursor, offset + left))
                    cursor = right
                hidden.append((offset + cursor, offset + len(line.rstrip("\r\n"))))
        else:
            hidden.append((offsets[start], offsets[end]))
    for index, line in enumerate(lines):
        cells = line.split("|")
        if len(cells) > 2 and cells[1].strip().casefold() in bibliography_fields:
            hidden.append((offsets[index], offsets[index] + len(line.rstrip("\r\n"))))
        if re.match(r"\s*\[(?:apa-source-|\^apa-)", line):
            hidden.append((offsets[index], offsets[index] + len(line.rstrip("\r\n"))))
    for pattern in (
        r"\$\$[\s\S]*?\$\$",
        r"(?<!\\)\$[^\n$]+(?<!\\)\$",
        r"(`+)[^`\n]*?\1",
        r"<!--[^>]*-->",
        r"\[\^[^\]]+\]",
        r"!?\[([^\]\n]+)\]\([^\n]*?\)",
        r"\[([^\]\n]+)\]\[[^\]\n]+\]",
        r"https?://[^\s<>]+",
        r"(?m)^\s*\[(?!\^)[^\]\n]+\]:[^\n]*",
    ):
        for match in re.finditer(pattern, text):
            if pattern.startswith(r"!?\[") or pattern.startswith(r"\[([^\]"):
                removed.extend([(match.start(), match.start(1)), (match.end(1), match.end())])
            else:
                hidden.append(match.span())
    mask = bytearray(len(text))
    for start, end in hidden:
        mask[start:end] = b"\x01" * (end - start)
    for start, end in removed:
        for index in range(start, end):
            if not mask[index]:
                mask[index] = 2
    # Formatting does not break a phrase: e.g. bold text inside a sentence.
    for match in re.finditer(r"\*{1,3}|_{1,3}|~~", text):
        for index in range(match.start(), match.end()):
            if not mask[index]:
                mask[index] = 2
    visible: list[str] = []
    positions: list[int] = []
    for index, char in enumerate(text):
        if mask[index] == 2:
            continue
        if mask[index]:
            if char in "\r\n":
                visible.append(char)
                positions.append(index)
            elif index == 0 or not mask[index - 1]:
                visible.append("\ufffc")
                positions.append(index)
            continue
        visible.append(char)
        positions.append(index)
    return "".join(visible), positions


def _blocks(text: str) -> list[tuple[int, int]]:
    """Keep tables, headings, lists and diagrams separate from soft prose wraps."""
    result: list[tuple[int, int]] = []
    start = 0
    active: int | None = None
    for line in text.splitlines(keepends=True):
        end = start + len(line.rstrip("\r\n"))
        structural = bool(re.match(r"\s*(?:[#>|]|[-+*] |\d+[.)] |\ufffc)", line))
        if not line.strip() or structural:
            if active is not None:
                result.append((active, start))
                active = None
            if line.strip():
                result.append((start, end))
        elif active is None:
            active = start
        start += len(line)
    if active is not None:
        result.append((active, len(text)))
    return result


def _language(text: str) -> str:
    return "zh" if re.search(r"[\u3400-\u9fff]", text) else "en"


def scan_prose(text: str) -> list[dict[str, Any]]:
    """Find review candidates; no match is automatically a factual/style verdict."""
    rules = load_json("prose-rules.json")
    errors = validate_rules(rules)
    if errors:
        raise ValueError("; ".join(errors))
    visible, positions = _visible(
        text,
        [label.casefold() for labels in rules["bibliography_fields"].values() for label in labels],
    )
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, int]] = set()

    def emit(rule: dict[str, Any], language: str, start: int, end: int) -> None:
        if start == end:
            return
        original_start = positions[start]
        original_end = positions[end] if end < len(positions) else len(text)
        key = (rule["id"], language, original_start, original_end)
        if key in seen:
            return
        seen.add(key)
        quote = text[original_start:original_end]
        identifier = hashlib.sha256(
            json.dumps([*key, quote], ensure_ascii=False).encode()
        ).hexdigest()[:24]
        findings.append(
            {
                "id": identifier,
                "rule_id": rule["id"],
                "category": rule["category"],
                "language": language,
                "line": text.count("\n", 0, original_start) + 1,
                "quote": quote,
                "context": text[max(0, original_start - 100) : original_end + 100],
                "message": rule["message"],
                "repair": rule["repair"],
                "keep_when": rule["keep_when"],
            }
        )

    for rule in rules["rules"]:
        for language, entry in rule["languages"].items():
            if not entry["applicable"]:
                continue
            if rule["check"] == "regex":
                for pattern in entry["patterns"]:
                    # Soft source wrapping is normalized within each paragraph.
                    for block_start, block_end in _blocks(visible):
                        projected = visible[block_start:block_end].replace("\n", " ")
                        for match in re.finditer(pattern, projected, re.IGNORECASE):
                            emit(
                                rule,
                                language,
                                block_start + match.start(),
                                block_start + match.end(),
                            )
            elif rule["check"] == "pairs":
                for opening, closing in entry["pairs"]:
                    for block_start, block_end in _blocks(visible):
                        stack: list[int] = []
                        for index in range(block_start, block_end):
                            char = visible[index]
                            if char == opening and (opening != closing or not stack):
                                stack.append(index)
                            elif char == closing:
                                if stack:
                                    stack.pop()
                                else:
                                    emit(rule, language, index, index + 1)
                        for index in stack:
                            emit(rule, language, index, index + 1)
            elif rule["check"] == "repeated_sentence":
                previous = ""
                for match in re.finditer(
                    r"[^\n\u3002\uff01\uff1f.!?]+[\u3002\uff01\uff1f.!?]", visible
                ):
                    sentence = match[0].strip()
                    if (
                        sentence == previous
                        and len(sentence) >= entry["minimum_length"]
                        and _language(sentence) == language
                    ):
                        emit(rule, language, match.start(), match.end())
                    previous = sentence
            elif rule["check"] == "heading_echo":
                pattern = (
                    r"(?m)^#{1,6}\s+([^\n]+)\n\s*\n"
                    r"([^\n\u3002\uff01\uff1f.!?]+)[\u3002\uff01\uff1f.!?]"
                )
                for match in re.finditer(pattern, visible):
                    heading = re.sub(r"^\d+[.\s]+", "", match[1]).strip()
                    if heading == match[2].strip() and _language(heading) == language:
                        emit(rule, language, match.start(2), match.end(2))
    return sorted(findings, key=lambda finding: (finding["line"], finding["id"]))


def audit_prose(path: Path) -> dict[str, Any]:
    findings = scan_prose(path.read_text(encoding="utf-8"))
    return {"path": str(path), "valid": not findings, "findings": findings}


def exception_errors(text: str, exceptions: list[dict[str, Any]]) -> list[str]:
    """Require exact, individually justified retention of every remaining match."""
    findings = {item["id"]: item for item in scan_prose(text)}
    errors: list[str] = []
    retained: set[str] = set()
    for item in exceptions:
        identifier = item["finding_id"]
        if identifier in retained:
            errors.append(f"duplicate prose exception: {identifier}")
        retained.add(identifier)
        finding = findings.get(identifier)
        if finding is None or item["quote"] != finding["quote"]:
            errors.append(f"stale or mismatched prose exception: {identifier}")
    for identifier in findings.keys() - retained:
        finding = findings[identifier]
        errors.append(
            f"unreviewed prose candidate at line {finding['line']} "
            f"[{finding['rule_id']}]: {finding['quote']}"
        )
    return errors
