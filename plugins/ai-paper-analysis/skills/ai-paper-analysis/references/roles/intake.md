# Plan Once, Then Execute

The coordinator owns planning, user questions, scope, and publication. Workers
return unresolved decisions to it without starting their own questionnaires.

## Start or resume

For a new task without an accepted plan, check the conversation's current mode.
If it is not Plan Mode, remind the user in their language to enter Plan Mode
and complete the task plan before execution. Do not start downloads, report
writing, or publication yet. The Skill cannot switch the host's mode.

If an accepted plan already exists, resume it when execution is permitted.
Do not restart planning or repeat approval merely because a task resumed or
reached another workflow step.

## Gather facts and settle decisions

Inspect the request, existing artifacts, and relevant source identities before
asking. Reuse established answers. Ask only about applicable decisions that
cannot be resolved from evidence and materially affect the work. Prefer an
available question tool; its absence does not block planning or require a new
approval procedure.

When the host permits planning writes, use one system-temporary workspace for
bounded source downloads, extraction, page renders, and planning notes. Keep
formal outputs unchanged. If the host prohibits those writes, plan the needed
preparation and perform it at the start of execution without another planning
round. Reuse existing originals and prepared files.

Generated reports and explanations support Chinese and English only. Record
`output_language` as `zh` or `en`, optionally with locale/script subtags. If another
output language is requested, ask the user to choose Chinese or English before
execution; do not silently substitute. Source-paper language filters are separate.

Resolve the following as relevant to the request:

- Workflows, known inputs or discovery criteria, output language and destination,
  and new reports versus revisions. For revisions, settle candidate-only
  delivery or promotion of named reports with the existing archive procedure.
- Search providers, inclusion/exclusion criteria, dates, access permissions,
  stopping bounds, and allowed query expansion. Set future-work search bounds
  separately from mandatory novelty and Benchmark sources, within this plan.
- How to handle unavailable originals, whether OCR may be used if needed, and
  whether temporary material should be retained at a specified destination.
- Classification scope, taxonomy or its derivation criteria, selected categories,
  and permission to prepare missing originals or reports. Resolve known
  assignment ambiguities during planning.
- A main explanatory scenario, with local analogies or numerical examples when
  clearer, preferably grounded in the paper's own objects. If inspection must
  wait until execution, agree on the basis for choosing it rather than inventing
  a paper-specific mapping. Settle subagent authorization here if delegation
  will be useful; otherwise use the roles sequentially.

Use existing defaults unless the user chooses otherwise: per-host concurrency
2, timeout 60 seconds, three retries, a 200 MiB PDF limit,
`draft_model_policy=fastest_suitable`, and `evidence_cache=project`. Do not ask
separate questions about these defaults.

## One accepted plan

Present one complete plan covering preparation, evidence, report writing,
review, delivery, and cleanup. Make consequential choices and any deferred
source-dependent decisions visible. If task-specific constraints need more
space, link the temporary `instructions.md` described in
[../contracts/execution-plan.md](../contracts/execution-plan.md).

The user's explicit acceptance of the plan, including an instruction to
implement it, supplies confirmation. Record `plan_confirmed=true` and the
actual `approved_at` time in the version 2 run specification; no particular
question tool or second approval is required. A draft uses
`plan_confirmed=false` and may omit `approved_at`. Execute only when the host
allows execution.

## Continue within the plan

Resolve source identities, complete mandatory source inventories, and review
classification assignments within the accepted criteria. Fill in these facts
as they become known; they do not constitute a new authorization stage. Before
a dependent report or comparison, require its actual verified inputs and the
existing evidence and eligibility checks.

Continue through writing, review, revision, and authorized publication without
asking the user to start the next step. Ask only when a necessary decision
cannot be resolved within the accepted plan or would exceed its authorization;
continue unaffected work. A missing source follows the agreed limitation
policy. An unresolved correctness failure remains visible and blocks the
affected output, not unrelated work. Do not require a return to Plan Mode for
routine findings or changes to derived source lists.
