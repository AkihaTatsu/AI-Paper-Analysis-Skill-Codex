---
name: ai-paper-analysis-finder
description: Discover papers within confirmed search bounds, acquire and verify legal originals, and optionally prepare an exclusive classification. Use explicitly for paper search or acquisition.
---

# AI Paper Analysis Finder

Use explicitly or when selected for the requested paper workflow. This Skill
is self-contained: obtain missing materials through its bundled shared roles
and `scripts/apa.py`, without requiring a sibling Skill.

Read [references/roles/intake.md](references/roles/intake.md) for focused
questions, two-stage approval, scope changes, and per-run subagent authorization.
Follow [references/roles/orchestration.md](references/roles/orchestration.md)
for bounded assignments and minimal contexts. The coordinator owns questions
and scope; workers load only their assigned references. Execute after approval
and Plan Mode exit.

Maintain one visible checklist under
[references/contracts/execution-plan.md](references/contracts/execution-plan.md),
using its text-table fallback when the native plan tool is unavailable.

## Discovery and publication

Confirm search criteria, finite providers, access mode, stopping bounds,
query expansions, target root, and optional classification before search.
Dispatch [references/roles/sources.md](references/roles/sources.md) for acquisition,
identity/version/structure/full-text relevance checks, and legal-source rules.
Read [references/roles/classification.md](references/roles/classification.md)
only when classification is requested. After per-run authorization, independent
identities or provider batches may run concurrently within the shared limits.

The coordinator publishes validated originals atomically under their stable
PDF stems, retains compact state, and cleans temporary artifacts. A readable
PDF with inconclusive identity is a candidate requiring confirmation, never a
verified input. Never overwrite an ambiguous identity/version, bypass an access
control, or use unconfirmed OCR. Confirm the complete exclusive assignment
preview before publishing classification or taxonomy.

Use this Skill's shared `tools list`, `tools doctor`, `tools ensure`, `read-pdf`,
`render-pdf-pages`, and other CLI operations as needed; inspect command `--help`
for arguments. Missing compatible shared tools are resolved by capability,
not by installing another paper-analysis Skill.
