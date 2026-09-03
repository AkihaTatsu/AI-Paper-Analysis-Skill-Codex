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

Use `flowchart TB` unless the graph has at most six nodes, longest chain at most
four, no cycle, and maximum degree at most two. Only then may it use LR. Wrap
paper modules in `subgraph`. Avoid raw HTML and formulas in labels.

Every Mermaid block must pass the official locked `mermaid.parse()` syntax
check. A reported syntax error blocks publication. An unavailable parser,
renderer, or required browser also blocks publication.

## Publication gate

Require Markdownlint with `MD013` disabled, CommonMark/GFM parsing,
Obsidian-profile checks, MkDocs strict build, MathJax, KaTeX, Mermaid rendering,
relative-link checks, and browser console checks. A syntax or rendering failure
blocks publication. A content-level `partial` report is not an exception to
this gate.
