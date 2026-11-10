# Portable Markdown Profile

Generated reports must be one Markdown source compatible with GitHub,
Obsidian's documented syntax, and the repository's locked MkDocs configuration.

## Allowed syntax

- ATX headings with one level-one title and no skipped levels.
- Paragraphs separated by blank lines and written without internal source-line
  wrapping.
- Standard Markdown links with portable relative paths.
- GFM tables, fenced code, block quotes, ordered and unordered lists.
- Mermaid fenced blocks.
- Footnotes, task lists, and strikethrough.

Do not use raw HTML, Wikilinks, Obsidian callouts, MkDocs admonitions or
directives, YAML front matter, or renderer-specific generated anchors.

## Source-line layout

Write every prose-bearing block on one physical Markdown source line. This rule
applies to ordinary paragraphs, each list item, each block-quote paragraph, and
each footnote definition. Keep the footnote marker on the same line as its
paragraph. Separate distinct paragraphs with at least one blank line.

Do not wrap prose at 100 characters or any other line length. Disable
Markdownlint rule `MD013` for generated reports; all other configured rules
remain active. Headings and table rows remain one line by structure. Display
mathematics, fenced code, and Mermaid blocks may use the multiple lines their
syntax requires.

## Mathematics

- Use `$...$` for inline mathematics.
- Put opening and closing `$$` on separate lines for display mathematics.
- Do not use `\(...\)`, `\[...\]`, or a `math` code fence.
- Escape literal currency signs as `\$`.
- Do not place display mathematics inside a table.
- Use only MathJax/KaTeX common syntax. Expand custom macros without changing
  the equation's mathematical content.

## Mermaid

After the complete report exists, run `prepare-report` with its report kind and
intended publication path. It includes the shared direction fixer; the
standalone `fix-mermaid-direction <candidate.md>` and its `--dry-run` remain
available for a focused direction change. These commands prepare a candidate
and do not bypass semantic review or publication approval.

Use the official locked Mermaid parser and the shared deterministic TB/LR
layout estimates. Prefer width <= height, then smaller width and height; if
neither qualifies, prefer the smaller width/height ratio and then width. Keep
the current direction on an exact tie or a zero-/one-node graph. Do not choose
from node counts or graph topology. Estimates are not measured rendered SVG
dimensions, and final browser rendering is still required.

The read-only audit uses those same estimates and blocks a mismatched direction.
Describe the flow using node or module names instead of fixed left/right or
top/bottom positions: automatic preparation may change the orientation. Review
any remaining spatial wording against the prepared graph before publication.
Wrap paper modules in `subgraph`. Avoid raw HTML and formulas in labels.
Every Mermaid block must pass the official locked `mermaid.parse()` check.
Unsupported layout estimation or parser/rendering failure blocks publication;
do not replace a missing required parser, renderer, or browser with a heuristic.

## Publication gate

Require Markdownlint with `MD013` disabled, CommonMark/GFM parsing,
Obsidian-profile checks, MkDocs strict build, MathJax, KaTeX, Mermaid rendering,
relative-link checks, and browser console checks. A syntax or rendering failure
blocks publication. A content-level `partial` report is not an exception to
this gate.

Run `audit-paper` or `audit-category-report` with a current `--content-review`
receipt and the intended `--publication-path`. Link validity is judged at that
publication location. The receipt binds an actual whole-report semantic review
to the candidate and sources; command success cannot replace the review.
Structure validity, complete/partial content, and eligibility for comparison
are distinct. A visibly partial report can be published only within its approval
and after all structural gates pass; only complete paper reports are eligible
for category comparison.
