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

For a new task without an accepted plan, if the current mode is not Plan Mode,
remind the user to enter Plan Mode and finish planning before execution. Start
no downloads, report writing, or publication until then. With an accepted plan,
continue or resume execution when the host permits it; do not ask to plan again.

Read [references/roles/intake.md](references/roles/intake.md) to settle decisions
in one complete plan, then execute continuously within its accepted scope.
Follow [references/roles/orchestration.md](references/roles/orchestration.md)
for bounded assignments and minimal contexts. The coordinator owns questions
and scope; workers load only their assigned references and task instructions.

Maintain one visible checklist under
[references/contracts/execution-plan.md](references/contracts/execution-plan.md),
using its text-table fallback when the native plan tool is unavailable.

## Plan and execute

Use this Skill's `scripts/apa.py` for shared tools, verified source acquisition,
PDF reading/rendering, temporary work, validation, and atomic publication.
Discover capabilities with `tools list`, `tools doctor`, and command `--help`.

Acquire and verify required originals before substantive comparison. Prepare
missing complete paper reports through the shared whole-paper writer before
category use. Report workflows follow
[references/roles/report-lifecycle.md](references/roles/report-lifecycle.md).
Preserve original-page formula checks, complete content coverage, source
separation, and accepted access and publication boundaries.

Generated questions and reports use the requested language. Skill instructions,
CLI text, schemas, and repository documentation remain English.
