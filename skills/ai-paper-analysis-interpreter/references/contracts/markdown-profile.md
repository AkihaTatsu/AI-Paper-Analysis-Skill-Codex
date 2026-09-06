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

Choose `flowchart TB` or `flowchart LR` by estimating both layouts before
publication. Run `fix-mermaid-direction <candidate.md>` before the final audit;
add `--dry-run` to inspect the estimates without writing. This command processes
all supported flowcharts in the specified file and changes only their top-level
direction tokens. It accepts TD as a TB alias and reports other diagram types
or directions as skipped. A parse or estimation failure leaves the entire file
unchanged. Use it on the candidate during the existing report revision workflow.

Prefer the layout whose horizontal side is the short side (width <= height).
If both qualify, minimize width, then height. If neither qualifies, minimize
width/height, then width. Preserve the current direction on an exact tie and
for zero- or one-node graphs. Do not decide from node counts, chain length,
cycles, or maximum degree.

Dimensions are deterministic estimates from the locked Mermaid parser and
Dagre layout engine, including disconnected nodes, labels, and subgraphs.
Text uses an approximate half-em ordinary character width, one em for CJK and
emoji, and a 1.5-em line height; combining marks have no advance. Node shapes,
padding, Markdown-label wrapping, and spacing contribute to the bounds. These
are estimates, not measured SVG dimensions. Unsupported layouts, shapes, or
size-affecting CSS fail explicitly. Estimation needs Node.js but no browser;
the final rendering gate still requires its browser.

The read-only audit uses the same estimates and blocks a mismatched direction,
reporting both sizes and the recommended replacement. Wrap paper modules in
`subgraph`. Avoid raw HTML and formulas in labels.

Every Mermaid block must pass the official locked `mermaid.parse()` syntax
check. A reported syntax error blocks publication. An unavailable parser,
renderer, or required browser also blocks publication.

## Publication gate

Require Markdownlint with `MD013` disabled, CommonMark/GFM parsing,
Obsidian-profile checks, MkDocs strict build, MathJax, KaTeX, Mermaid rendering,
relative-link checks, and browser console checks. A syntax or rendering failure
blocks publication. A content-level `partial` report is not an exception to
this gate.
