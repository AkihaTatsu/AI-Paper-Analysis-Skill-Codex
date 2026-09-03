# Intake and Confirmation Protocol

Use this checklist as a decision tree, not as one giant questionnaire. Inspect
the request and existing artifacts first. Ask only questions that remain
unresolved, in batches of at most three.

## Shared requirements

Confirm:

- Which workflows are required and their execution order.
- Whether the request creates new artifacts or revises existing ones.
- Input files, URLs, paper IDs, or corpus root.
- Target root and requested output language; follow the request language when
  it is unambiguous.
- Whether the current run may use subagents. Default to sequential execution.

## Finder requirements

Confirm all of the following before search:

- Research question or topic and any query phrases that must be literal.
- Inclusion and exclusion criteria.
- Date, language, paper-type, and source bounds.
- Proposed query expansions and finite provider set.
- Public-only versus explicitly authorized access.
- Either target accepted count plus candidate cap, or exhaustive paging within
  the confirmed bounds.
- Target root and classification choice. Staging is temporary by default. If
  retained staging is explicitly requested, confirm its absolute visible
  destination outside `.ai-paper-analysis`.
- OCR only if structural preflight later shows it is needed.

If classification is requested, propose mutually exclusive category and
subcategory definitions. Confirm the taxonomy before assignments, resolve
borderline assignments, then confirm the complete assignment table.

## Interpreter requirements

Confirm:

- Paper PDFs, supplements, existing reports, and known official-code links.
- Whether this is a new report or a candidate revision.
- After reading the target paper, the finite novelty-comparison set: every
  named work that will support a substantive claim about a baseline's setting,
  assumptions, method, guarantee, or difference. A grouped comparison includes
  every named paper in that group; exclude citations used only for background,
  datasets, tools, or borrowed components. Record verified local originals in
  `input_refs` and identify which exact originals still require Finder.
- After reading the target paper, the finite Benchmark-source set: every
  independently published original that defines a Benchmark, dataset, or
  environment and is needed to support its description or parameter
  explanation. Do not include every method named only as a result-table row.
  Record verified local originals in `input_refs` and identify which exact
  originals still require Finder. A Benchmark introduced and fully defined by
  the target paper needs no duplicate external source.
- Separately, future-work date/source bounds, target papers per direction, and
  candidate cap per direction. This budget does not cap the mandatory
  novelty-comparison or Benchmark-source set.
- Whether a required novelty-comparison or Benchmark-source original that
  remains legally inaccessible after the confirmed search may be described
  only through the target paper's explicitly labeled characterization, without
  independent full-text verification.
- A shared analogy scenario when the paper itself supplies none. Present two or
  three concrete, jargon-free choices.
- OCR when needed. An unavailable official repository is not a blocker.

## Comparator requirements

Confirm:

- Classification CSV, taxonomy, paper/report corpus, and selected categories.
- Any proposed taxonomy or subcategory change.
- The category-wide everyday scenario.
- The complete assignment preview before publication.

## Two-stage confirmation

The first approved specification must use `approval_stage=target_acquisition`
and may authorize only the Finder work needed to identify exact target papers
and inspect sources. It must not authorize report drafting, classification
publication, or category comparison. After that acquisition finishes, present
the resolved paper sets and all remaining choices, then create a replacement
specification with `approval_stage=full_execution`.

## Final confirmation

Present one consolidated summary containing:

- Workflow order and artifact inputs/outputs.
- The exact novelty-comparison and Benchmark-source sets, their local-PDF
  coverage, and all separate future-work search bounds and budgets.
- Provider and credential choices.
- Taxonomy, scenario, OCR, temporary staging or its explicit visible retention
  destination, revision, and subagent choices.
- Network defaults: per-host concurrency 2, timeout 60 seconds, three retries,
  and a 200 MiB PDF limit unless explicitly changed.
- Access-control, no-overwrite, evidence, and Markdown publication gates.

Ask once more with `request_user_input`. The answer approves the exact
full-execution specification. Any later material change requires a replacement
approval.
