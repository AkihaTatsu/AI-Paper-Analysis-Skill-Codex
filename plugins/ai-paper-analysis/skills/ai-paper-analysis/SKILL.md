---
name: ai-paper-analysis
description: Route requests that find, classify, interpret, revise, or compare academic papers through a strict Plan Mode clarification and evidence workflow. Use when a request may need one or more AI Paper Analysis child Skills; do not use for ordinary prose summaries without source inspection.
---

# AI Paper Analysis Router

Route the request to the smallest necessary combination of these explicit-only
Skills:

- `$ai-paper-analysis-finder` for online discovery, legal PDF acquisition,
  validation, and optional exclusive classification.
- `$ai-paper-analysis-interpreter` for source-grounded paper reports or
  non-destructive revisions.
- `$ai-paper-analysis-comparator` for category-level relationship and reading
  reports from verified classifications.

Do not imitate a missing child Skill. If a selected child is unavailable, name
the missing dependency and stop before execution.

## Mandatory clarification gate

Read [references/intake.md](references/intake.md). Resolve every material
missing value, ambiguous phrase, conflicting requirement, or consequential
default with `request_user_input` in Plan Mode. Ask in focused rounds, explain
the tradeoff, and recommend one option. Do not replace the question tool with
plain-text questions or guesses.

Use two confirmation stages. First confirm only target acquisition: workflows,
input identities, search bounds, and target root. This approval authorizes
source inspection needed to resolve the remaining details, but not a full run
or formal publication. Then return with the exact discovered source sets,
taxonomy or scenario proposals, outputs, and gates for full-execution approval.

After all workflow-specific requirements are fixed:

1. Present one consolidated execution specification, including low-risk
   defaults.
2. Ask for final confirmation with `request_user_input`.
3. Produce the final plan while still in Plan Mode.
4. Execute only after the user exits Plan Mode.

If a new ambiguity appears during execution, pause and require a return to Plan
Mode. If the question tool is unavailable, stop. Plan Mode must not create run
directories, download files, or mutate formal artifacts.

## Composition order

Use Finder before Interpreter when papers must be acquired, including when any
paper in the confirmed novelty-comparison or Benchmark-source set lacks a
verified local original PDF. Use Interpreter before Comparator when verified
reports do not exist. Comparator may consume only verified, confirmed,
semantically consistent inputs. Reuse valid existing artifacts; do not call an
unrelated child merely because it is installed.

Batch work is sequential by default. Ask for per-run authorization before
using subagents. Authorization for one run does not carry to another.

## Minimal persistent workspace

Keep `.ai-paper-analysis` small. During an active run it may contain only the
approved run specification, a compact status file, and candidates that must
survive an approval pause. After publication, retain only one compact state
record per formal artifact and the latest replaced report per report stem.

Put downloads awaiting validation, rejected files, OCR copies, rendered pages,
diffs, detailed audits, conversion stages, caches, local lint configuration,
and one-off scripts in a randomly named system temporary directory. Remove the
temporary directory when its dependent step ends. Never place a virtual
environment, dependency copy, cache, or speculative helper in the target's
hidden directory.

Create a project-specific helper under `.ai-paper-analysis/tools/` only after
the user approves that individual promotion. It must contain no report-specific
paths or constants and must include a short English purpose note and a focused
test. Put helpers reusable across projects in this Skill's `scripts/` instead.

Do not recursively inspect `.ai-paper-analysis` during a later revision. Read
the formal artifact, its directly relevant sources, its compact state record,
and any active candidate required by the request. Read archives or an approved
project helper only when that specific content is needed.

## Execution contract

During execution, validate the approved `run-spec.json` with the Skill launcher.
The launcher reuses a compatible shared runtime when one already exists and
installs only a missing compatible layer:

```bash
python <skill-directory>/scripts/apa.py \
  validate-spec <run-spec.json>
```

Never edit an approved specification in place; return to Plan Mode and approve
a replacement.

Use `init-run` to create the minimal persistent run state and `create-temp` to
create the disposable workspace for all other work. Run `cleanup-temp` as soon
as its dependent work ends. After an approved publication, write the compact
artifact state with `record-state`; for an approved revision, use
`promote-revision` so archive retention remains bounded. Then use the
strictly scoped `cleanup-run` command to remove the completed run directory.
Keep detailed audit artifacts only when the user explicitly requests them as
formal outputs in a confirmed visible directory outside `.ai-paper-analysis`.

Generated questions and reports follow the user's requested language. The
Skill instructions, static CLI text, schemas, and repository documentation
remain English.
