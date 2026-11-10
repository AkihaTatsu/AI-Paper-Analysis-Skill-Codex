---
name: ai-paper-analysis-interpreter
description: Create or non-destructively revise complete, source-grounded paper reports with novice-facing explanations, verified equations, shared everyday analogies, experiments, and full-report review. Use explicitly for paper interpretation.
---

# AI Paper Analysis Interpreter

Use explicitly or when selected for the requested paper workflow. This Skill
independently acquires missing originals and prepares reports using its bundled
shared roles and `scripts/apa.py`; do not require Finder or another sibling Skill.

Read [references/roles/intake.md](references/roles/intake.md) for focused
questions, two-stage approval, scope changes, and per-run subagent authorization.
Follow [references/roles/orchestration.md](references/roles/orchestration.md)
for bounded assignments and minimal contexts. The coordinator owns questions
and scope; workers load only their assigned references. Execute after approval
and Plan Mode exit.

Maintain one visible checklist under
[references/contracts/execution-plan.md](references/contracts/execution-plan.md),
using its text-table fallback when the native plan tool is unavailable.

## One complete report

Follow [references/roles/report-lifecycle.md](references/roles/report-lifecycle.md).
Start the whole-report writer as soon as the verified target and approved scope
are available. It reads the full target/supplement, builds complete terminology,
module, experiment and equation coverage, verifies equations visually, and
writes in one continuous context. Prepare confirmed finite novelty-comparison
and Benchmark-source originals concurrently when authorized; the complete draft
must receive their verified evidence before making dependent claims. Future-work
search retains its separate confirmed budget.

Assign [references/roles/paper-writer.md](references/roles/paper-writer.md) to one
whole report. The writer alone reads its detailed content rules and produces
all seven sections with connected explanations for readers without prior field
knowledge, no word cap, and one approved concrete everyday scenario. Do not
split chapters among writers or make the coordinator copy all writing rules.

The lifecycle defines automatic checks, one semantic review, automatic exact
patches, residual revision when needed, scoped continuation, final audit, and approved
publication. Partial reports cannot enter category comparison. A revision
remains a candidate until the user approves promotion; only the coordinator
publishes and maintains state under that contract.
