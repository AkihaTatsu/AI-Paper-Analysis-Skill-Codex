---
name: ai-paper-analysis-finder
description: Discover research papers across a confirmed finite source set, acquire legal PDFs through temporary staging, validate identity and relevance, publish verified files atomically, and optionally create an exclusive classification CSV. Use explicitly for paper search or acquisition workflows.
---

# AI Paper Analysis Finder

Use this Skill only when explicitly invoked or selected by
`$ai-paper-analysis`.

Before execution, read [references/workflow.md](references/workflow.md). When
classification is requested, also read
[references/classification.md](references/classification.md). Read
[references/sources.md](references/sources.md) when selecting providers or
credentials.

## Non-negotiable gate

Do not search or download until the user has confirmed all material fields in
Plan Mode through `request_user_input`: research topic, inclusion and exclusion
rules, date/language/type bounds, provider set, access mode, stopping policy,
target root, classification choice, any explicitly requested staging-retention
destination, and any query expansion.

The stopping policy must be either a target accepted count plus candidate cap,
or exhaustive paging within explicit bounds. Batch-review borderline
candidates. Confirm the complete exclusive classification preview before
publishing it. Staging is temporary unless the user explicitly requests and
confirms an absolute visible retention directory outside
`.ai-paper-analysis`. Stop if the question tool is unavailable.

## Access boundary

Never bypass a paywall, CAPTCHA, robots exclusion, rate limit, or access
control. Google Scholar batch search requires a user-configured API. Chinese or
commercial databases require explicit authorization and a valid existing
session. Record inaccessible sources; do not improvise an evasion.

## Publication invariant

Download each candidate into a randomly named system temporary directory.
Validate PDF structure, identity, inclusion criteria, full-text relevance,
and version before publication. Preserve one primary PDF in the order:
legally available version of record, author manuscript, latest preprint. Record
alternatives in temporary decision notes while the run is active.

Publish only with the deterministic runtime. The PDF and eventual report share
the stem `{year}_{first-author}_{ascii-title-slug}_{id-digest10}` under
`papers/`. Reuse an existing file only after its bibliographic identity,
version, and PDF structure match the confirmed work. Any identity or version
ambiguity requires another Plan Mode decision and must not overwrite. After
publication, use `record-state` to retain only the PDF's stable path, run ID,
and publication status.

A structurally readable PDF with no reliable title, identifier, author, or
source-chain signal is a valid candidate with `identity_status=inconclusive`,
not a verified paper. Show it to the user for identity confirmation before it
can be published as verified or used in any novelty, Benchmark, or category
comparison.

Delete failed binaries and temporary decision notes at run completion. When
retained staging was approved, publish the requested copies to its confirmed
visible destination instead of the hidden run directory. OCR requires a
separate question-tool confirmation, operates on a temporary copy, and never
replaces the original PDF.

Do not persist one-off search, conversion, or audit scripts. A project helper
may enter `.ai-paper-analysis/tools/` only after individual user approval and
only when it has no report-specific constants, has a short English purpose
note, and has a focused test.
