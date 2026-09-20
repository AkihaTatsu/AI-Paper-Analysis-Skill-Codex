---
name: ai-paper-analysis
description: Plan and coordinate source-grounded paper discovery, interpretation, revision, and category comparison through shared evidence and report roles. Use for academic-paper workflows requiring source inspection, not ordinary prose summaries.
---

# AI Paper Analysis Router

Use only when explicitly invoked as `$ai-paper-analysis`.

Identify the smallest necessary workflow: discovery/acquisition, paper
interpretation/revision, category comparison, or their approved combination.
The named Finder, Interpreter, and Comparator Skills are alternative user
entrypoints. Use the shared roles and bundled CLI directly; no workflow
requires another Skill to be installed or invoked.

Read [references/roles/intake.md](references/roles/intake.md) for fact-first,
focused clarification and two-stage approval. Read
[references/roles/orchestration.md](references/roles/orchestration.md) to dispatch
only the needed roles. Do not preload their content rules. The coordinator
asks all questions, holds the approved scope, and integrates role results.

## Plan and execute

Remain read-only in Plan Mode. Confirm target acquisition first, inspect the
approved sources after Plan Mode exit when execution is needed, then return
with exact source sets and remaining choices for full-execution approval and
final confirmation. Execute only after the user exits Plan Mode. A new material
ambiguity requires returning to Plan Mode; stop if `request_user_input` is
unavailable. Ask for subagent authorization once per run; after authorization
recommend bounded parallel evidence work and use fresh minimal worker contexts.

Read [references/contracts/execution-plan.md](references/contracts/execution-plan.md)
and maintain one visible `update_plan` checklist for the task; when unavailable,
explain and maintain the specified text table while continuing authorized work.
Use this Skill's `scripts/apa.py` for shared tools, verified source acquisition,
PDF reading/rendering, temporary work, validation, and atomic publication.
Discover capabilities with `tools list`, `tools doctor`, and command `--help`.

Acquire and verify required originals before substantive comparison. Prepare
missing complete paper reports through the shared whole-paper writer before
category use. Report workflows follow
[references/roles/report-lifecycle.md](references/roles/report-lifecycle.md).
Preserve original-page formula checks, complete content coverage, source
separation, and all access/approval/publication gates.

Generated questions and reports use the requested language. Skill instructions,
CLI text, schemas, and repository documentation remain English.
