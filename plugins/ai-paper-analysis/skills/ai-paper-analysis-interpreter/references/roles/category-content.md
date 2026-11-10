# Category Report Content

Read [report-style.md](report-style.md). Explain shared concepts once and use
consistent, compact comparisons to show each paper's contribution.

## Eligible inputs

Use only `verification_status=verified` and `review_status=confirmed` rows
whose PDF/report files exist, semantic identifiers agree, and paper report
audit is `structure-valid` with a valid content review and
`content_status=complete`. Accept a current review bound to the artifact and
source versions through an active receipt or the report's compact artifact
state. A legacy report without either must be reviewed when it is needed,
not silently treated as complete. The coordinator
can arrange missing paper reports with the shared whole-paper writer after
scope approval. Do not silently repair an excluded input or infer permission
to create its replacement. Excluded IDs and reasons go in the completion
summary; retain a detailed exclusion artifact only if explicitly requested.

Translate headings into the output language, preserving one level-one title
and the three numbered level-two sections below. A singleton category still
gets all three sections, a single-node graph, and a one-item reading order.

## 1. Overview

Explain the category's overall concept in plain language, state its problem in
one sentence, and explain concrete properties shared by every eligible paper.
Support technical commonalities with original evidence and respect the
confirmed taxonomy boundary. Partial or excluded papers cannot support these
commonalities or relationship edges.

## 2. Overall Paper Relationships

Provide one Mermaid graph containing every eligible paper and only
evidence-backed edges from the fixed enum in [relationships.md](relationships.md).
Read the shared [Mermaid rules](../contracts/markdown-profile.md#mermaid) before
describing the graph's layout.
Explain a reading order by dependency prerequisites first, conceptual difficulty
second, and publication year as the tie-breaker. Give the reason for each step;
chronology alone is not relationship evidence.

## 3. Subcategory Discussion

Every paper belongs to exactly one category and one most-relevant subcategory.
Use the confirmed mutually exclusive definitions. Each subcategory contains
its paper relationship graph, a complete refined everyday scenario, and a
comparison table with parallel phrasing.

The table contains the original title; official canonical page; legal PDF URL;
relative local PDF and report links; paper overview; concrete addition to the
shared scenario; problem solved; and compact evidence anchors. Mark missing
links explicitly. Describe differences without changing the meaning of the
shared scenario or switching terminology between rows.

Validate the final category report as `relationship-valid`, separately from
input classification and report eligibility.
