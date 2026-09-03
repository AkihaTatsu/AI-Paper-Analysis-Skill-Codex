---
name: ai-paper-analysis-comparator
description: Build auditable category-level paper comparison reports from exclusive verified classifications, including evidence-backed relationship graphs, reading order, shared scenarios, and subcategory tables. Use explicitly after classification and paper reports exist.
---

# AI Paper Analysis Comparator

Use this Skill only when explicitly invoked or selected by
`$ai-paper-analysis`.

Read [references/comparison-spec.md](references/comparison-spec.md) for the
report structure and [references/relationships.md](references/relationships.md)
before constructing graphs. Read
[references/contracts/markdown-profile.md](references/contracts/markdown-profile.md) before the
final audit. Start from
[references/templates/category-report.md](references/templates/category-report.md).

## Input gate

Confirm the target root, selected categories, output-language ambiguity,
taxonomy draft or changes, subcategory draft, and everyday scenario through
`request_user_input` in Plan Mode. Present the entire assignment preview and
obtain confirmation before publishing `<target-root>/classification.csv`,
`<target-root>/taxonomy.json`, or a category report. Stop if the question tool
is unavailable.

Consume only rows with `verification_status=verified` and
`review_status=confirmed`, plus existing PDF/report files, passing report
audits, and passing report/CSV semantic consistency. List
excluded rows and reasons in the completion summary; do not silently repair
them. Persist a detailed exclusion audit only when the user explicitly asks
for it as a formal output outside `.ai-paper-analysis`.

## Required outcome

Generate one report per category under `category-reports/`. Every paper belongs
to exactly one category and one most-relevant subcategory. A singleton category
still receives a complete single-node report.

Use one category-wide jargon-free everyday world and refine it slightly for
each subcategory. Each subcategory includes its relationship graph, shared
scenario, and a parallel-phrased comparison table with canonical, legal PDF,
local PDF, and local report links.

Use only the relationship enum in the relationship reference. Treat the edge
as subject paper to object paper and attach a source locator to every edge.
Recommend reading order by dependency first, difficulty second, and publication
year as the tie-breaker.

Audit Markdown, links, official Mermaid syntax, taxonomy exclusivity,
relationship evidence, and cross-artifact semantics. Any syntax or audit
failure blocks formal publication; an unavailable Markdown parser, Mermaid
parser, renderer, or required browser is itself a blocking failure.

Keep relationship ledgers, graph renderings, detailed audits, diffs, and any
one-off scripts in a randomly named system temporary directory created with
`create-temp`, then remove it with `cleanup-temp`. In the hidden run directory
retain only a candidate report that must survive an approval pause. After
publication, write the compact state record with `record-state` and remove the
run with the strictly scoped `cleanup-run` command. Do not recursively inspect
hidden run history during later edits, and do not persist a project helper
without the user's individual approval, a report-independent implementation,
a short English purpose note, and a focused test.
