# Category Comparison Report Specification

Translate human-facing headings when needed, but preserve one level-one title
and the three numbered level-two sections.

## 1. Overview

State:

- The category's overall concept in plain language.
- The problem it addresses in one sentence.
- The concrete properties shared by all eligible papers.

Support technical commonalities with paper evidence. Do not define the category
so broadly that it erases the confirmed taxonomy boundary.

## 2. Overall Paper Relationships

Provide one Mermaid graph containing every eligible paper and only evidence-
backed edges from the fixed relationship enum. Follow it with a reading order
that uses:

1. Dependency prerequisites.
2. Conceptual difficulty.
3. Publication year as the tie-breaker.

Explain the reason for each step. A singleton category receives a one-node graph
and a one-item reading order.

## 3. Subcategory Discussion

Use the confirmed mutually exclusive subcategories. Every paper appears in one
and only one most-relevant subcategory.

For each subcategory, provide:

- A Mermaid relationship graph for its papers.
- One refined version of the category-wide everyday scenario. Keep it complete,
  friendly, jargon-free, and free of complex long sentences.
- A comparison table with parallel phrasing.

The comparison table must contain:

- Original paper title.
- Official canonical page.
- Legal PDF URL.
- Relative local PDF path.
- Relative local report path.
- Paper overview.
- The setting added to the shared scenario, written without academic jargon.
- The problem solved by the paper.
- Compact evidence anchors.

Mark missing links explicitly. Keep sentence structure similar across rows so
the differences remain visible.

## Input exclusions

The formal report may use only `verified + confirmed` rows whose PDF and report
files exist, whose semantic identifiers agree, and whose paper report audit is
`structure-valid` with `content_status=complete`. Validate the category report
separately as `relationship-valid`; this status does not replace the input
classification and paper-report gates. Report excluded paper IDs and reasons
in the completion summary. Persist them only when the user requested a formal
audit output outside `.ai-paper-analysis`. Do not include partial papers in
technical commonalities or relationship edges.
