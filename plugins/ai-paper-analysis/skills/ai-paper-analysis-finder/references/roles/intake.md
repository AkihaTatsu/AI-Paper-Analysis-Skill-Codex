# Shared Intake and Approval

The coordinator owns all user questions, scope decisions, and approvals. A
worker returns an unresolved decision to the coordinator; it never starts a
separate questionnaire or changes the approved scope.

## Establish facts before asking

Inspect the request, relevant existing formal artifacts, and directly relevant
source identities first. Separate established facts, unresolved decisions, and
blocked evidence. Do not ask the user to supply an answer available through
authorized read-only inspection. Do not recursively read hidden run history.

In Plan Mode, inspection is read-only: do not create run directories, download
files, write extracted text, render pages to disk, or mutate formal artifacts.
If resolving a fact requires acquisition or another write, propose that work in
the acquisition stage and execute it only after its approval and Plan Mode exit.

Ask with `request_user_input` in focused rounds of at most three questions.
Choose the next question from the current decision frontier: resolve the
decision that unlocks the most relevant inspection or downstream choices.
Challenge conflicting requirements, explain the concrete tradeoff, and
recommend an option. Reuse established answers; do not present the full
checklist below as one questionnaire. Resolve every material omission and
consequential default before its dependent work. If the question tool is
unavailable, stop; do not substitute plain-text questions or assumptions.

## Stage 1: target acquisition

Confirm the requested workflows, create versus revise, input files/URLs/IDs,
search bounds when relevant, target root, and source acquisition needed to
identify and inspect the exact target papers. Confirm whether this run may use
subagents; authorization is per run. Recommend bounded parallel evidence work
when authorized, and sequential work otherwise. Do not ask again within the
same run unless the requested delegation exceeds its approved scope.

Present a consolidated acquisition specification with
`approval_stage=target_acquisition`, ask for confirmation, and present its final
plan while still in Plan Mode. Execution starts only after the user exits Plan
Mode. This stage authorizes only target acquisition and source inspection; it
does not authorize drafting, classification publication, or category reports.
When the targets already exist, inspect them read-only rather than acquiring
duplicate copies.

## Stage 2: complete execution

Return to Plan Mode with the discovered identities, actual source coverage,
and remaining decisions. Resolve the applicable requirements below. Each
entrypoint independently arranges missing materials through its bundled shared
roles and CLI; the user need not install or invoke a sibling Skill.

For discovery/acquisition, confirm:

- Research question, literal queries, inclusion/exclusion criteria, dates,
  languages, paper types, finite provider set, and every query expansion.
- Public-only access or explicitly authorized commercial/browser access.
- A target accepted count plus candidate cap, or exhaustive paging within
  explicit bounds. Batch-review borderline candidates.
- Classification choice. If requested, confirm mutually exclusive definitions,
  then review ambiguous assignments and confirm the complete assignment table.
- Temporary staging by default. Confirm an absolute visible destination outside
  `.ai-paper-analysis` only when retained staging was requested.
- OCR only when a preflight establishes that it is needed; confirm it separately.

For every paper report, confirm:

- Exact target PDF, supplements, existing report, verified official-code
  identity when available, language when ambiguous, and new versus revision.
- The finite novelty-comparison set derived from the target's substantive
  novelty argument; every named original in a grouped comparison is included.
- The finite defining-original set for Benchmarks, datasets, and environments.
  A result-table method name alone does not add a source. A Benchmark fully
  introduced by the target needs no duplicate external original.
- Verified local-PDF coverage of both sets and exact missing originals. These
  mandatory sets are independent of the future-work budget.
- Separate future-work date/source bounds, target papers per direction, and
  candidate cap per direction.
- Whether a mandatory original that remains legally inaccessible after the
  confirmed search may be represented solely by the target paper's visibly
  labeled characterization, without independent full-text comparison.
- One everyday analogy scenario. Prefer the paper's own scenario; otherwise
  offer two or three concrete, jargon-free choices and confirm one.

For category comparison, confirm:

- Classification CSV, taxonomy, selected categories, corpus, and language when
  ambiguous; inspect actual input eligibility before proposing work.
- Missing PDFs or complete reports to prepare within this run. Report creation
  uses the shared whole-paper writer and the paper-report decisions above.
- Proposed taxonomy/subcategory changes, the complete assignment preview, and
  one category-wide everyday scenario.

## Final confirmation and later changes

Present one consolidated `approval_stage=full_execution` specification:
workflow order; exact inputs and outputs; mandatory source sets and local
coverage; separate future-work budgets; provider/credential choices; taxonomy;
scenario; language; OCR; staging; revision and publication boundaries;
subagent authorization and proposed concurrency. Include low-risk network
defaults unless changed: per-host concurrency 2, timeout 60 seconds, three
retries, and a 200 MiB PDF limit. Include execution preferences; default to
`draft_model_policy=fastest_suitable` and `evidence_cache=project` unless the
user has chosen otherwise. These defaults do not require a separate question.

Ask for final confirmation with `request_user_input`, then present the final
plan while still in Plan Mode. Execute only after the user exits Plan Mode.
Never edit an approved specification in place. A new material ambiguity,
changed source set, or consequential scope change during execution pauses the
dependent work and requires a return to Plan Mode and a replacement approval.
Existing access, evidence, no-overwrite, and publication gates remain in force.
