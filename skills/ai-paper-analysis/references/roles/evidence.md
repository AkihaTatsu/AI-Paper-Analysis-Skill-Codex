# Evidence Acquisition and Isolation

Use four report source classes: `paper`, `supplement`, `official_code`, and
`external_paper`. Verify identity before assigning a class. Do not execute
untrusted code. Pin official code to a tag, release, or commit and retain its
author-controlled provenance. Keep contradictions visible and return affected
claims as blocked.

## Locator packets and generated footnotes

Give every usable source location a stable `apa-*` ID based on source and
locator, such as `apa-paper-s3-2-e7`; reuse the ID for the same evidence bundle.
The report cites these IDs as Markdown footnotes. Reserve this namespace for
evidence packets. Hand-written footnotes use other IDs.

`prepare-report --evidence PACKET` regenerates managed footnote definitions and
one reusable reference-style link per source. Each locator must name a precise
page, section, equation, figure, table, commit, or line range. An unknown ID
blocks preparation. Report prose does not contain evidence links or visible
bracket anchors.

Only original paper/supplement PDFs, pinned official-code files, and verified
external PDFs may be linked as evidence. Never cite run specifications, logs,
candidate tables, extracted text, page renders, audits, drafts, or packets.

## Project evidence cache

Use `.ai-paper-analysis/evidence-cache/` only through
`lookup-evidence-cache` and `record-evidence-cache`. The cache covers PDF source
classes `paper`, `supplement`, and `external_paper`. Its key binds exact source
bytes, evidence policy, source class, and assignment coverage fingerprint.
Missing, stale, corrupt, incomplete, or source-mismatched records are misses.

Store concise structured facts, stable locators, full-coverage ranges, visual
formula status, and limitations. Never store a PDF copy, rendered or extracted
page, raw/full text, or report prose. The packet indexes the original; it does
not become a report source.

## Build mandatory external sets

Derive both sets after complete target reading and have the user confirm them
before dependent drafting. They are independent of the optional future-work
budget.

For the **novelty-comparison set**, include every cited work that the target
uses for a substantive baseline claim about setting, assumptions, method,
guarantee, or difference. Include every named member of a grouped claim. Exclude
background-only citations, datasets, tools, or borrowed components unless the
report makes a substantive method comparison.

For the **Benchmark-source set**, include every independently published
original needed to support a dataset, environment, or Benchmark's provenance,
construction, native setting, or defining properties. Do not add a method paper
solely because its name appears in a result table. A Benchmark introduced and
fully defined by the target needs no duplicate source.

For every member, use [sources.md](sources.md) to acquire and verify the exact
legal original and supplement when needed, then assign complete relevant
full-text reading to [evidence-reader.md](evidence-reader.md). Do not substitute
a survey, nearby paper, abstract, metadata record, website, or code
documentation. Record an exhausted legal-source search explicitly so the writer
can apply the source-limitation wording in [evidence-policy.md](evidence-policy.md).

## Future-work sources and file placement

Future-work papers require separately confirmed date/source bounds, target
count per direction, and candidate cap. Acquire, verify, and read their original
full text under the same rules.

For target `papers/<target-stem>.pdf`, publish external PDFs under
`papers/<target-stem>_references/<external-paper-stem>.pdf`; keep only PDFs in
that directory. When the same original supports multiple targets, publish a
verified copy in each directory. During revision, validate an atomically copied
file before updating the candidate link and retain the old file until separately
approved cleanup.

The coordinator need not reread originals solely to transfer them. Writers and
reviewers use verified coverage packets, reopen exact claim locators, and expand
context when needed. Keep external claims visibly separate from statements
attributed to the target paper.
