---
name: ai-paper-analysis-interpreter
description: Create or non-destructively revise rigorous, source-grounded paper reports with localized terminology, detailed explanatory prose, core equations, symbol tables, shared everyday analogies, experiments, limitations, and lightweight audits. Use explicitly when full paper interpretation is requested.
---

# AI Paper Analysis Interpreter

Use this Skill only when explicitly invoked or selected by
`$ai-paper-analysis`.

Read [references/report-spec.md](references/report-spec.md) for every report.
Start from [references/templates/paper-report.md](references/templates/paper-report.md).
Read [references/formulas-and-analogies.md](references/formulas-and-analogies.md)
before writing technical sections. Read
[references/evidence.md](references/evidence.md) when acquiring supplementary
material, official code, or related papers. Read
[references/contracts/markdown-profile.md](references/contracts/markdown-profile.md) before the
final audit.

## Confirmation and source boundary

Resolve material omissions and ambiguities with `request_user_input` in Plan
Mode before execution. Confirm inputs, target root, language ambiguity, OCR,
the finite novelty-comparison and Benchmark-source sets extracted from the
target paper, the separate future-work search budget, and an analogy scenario
when the paper provides none. Stop if the question tool is unavailable.

Treat the target paper, supplement, and verified paper-linked official-code
commit as equally authoritative where they overlap. Show contradictions as
unresolved and block affected conclusions. Continue paper-only if official code
is unavailable. Keep independently acquired future-work papers in a separate
external evidence channel, together with independently acquired originals used
for novelty comparison or Benchmark definition.

Before drafting Section 2, require a verified local original full-text PDF for
every named work used in a substantive novelty comparison; a grouped claim
requires every named original in the group. Invoke Finder first for any missing
original. If no legal full text is available after the confirmed search, use
only the target paper's characterization, label that source limitation visibly,
and do not claim an independent detailed comparison.

Before drafting Section 6, require a verified local original full-text PDF for
every independently published work used to define or explain a Benchmark,
dataset, or environment. Invoke Finder first for any missing original. If no
legal full text is available after the confirmed search, use only the target
paper's characterization, label the missing independent verification visibly,
and add no unverified Benchmark detail.

Do not turn model reasoning into paper claims. Cite each coherent factual
paragraph with reusable Markdown footnotes whose definitions link directly to
the target paper, supplement, pinned official-code file, or verified external
paper. Never cite, link, or name generated intermediate artifacts in the formal
report. Label narrow interpretation explicitly.

## Required outcome

Produce the seven numbered sections defined in the report specification. Adapt
"algorithm" and "module" to the paper type without deleting the section's
intent. Cover all named full-text terminology and every module-core equation
needed to define the method, objective, update, constraints, or key conclusion.

Write all human-facing content in the requested output language. Translate a
foreign term unless it cannot be translated reliably or its original name is
the overwhelmingly conventional identifier. Explain every retained foreign
name in the output language on first use. Write substantive prose as complete
explanatory units rather than isolated one- or two-sentence checklist answers.
Write every prose-bearing Markdown block on one physical source line, with a
blank line between separate paragraphs; never wrap prose to satisfy a line
length limit.

Every written equation must match the paper, be visually checked against the
original page, and be followed immediately by the required symbol/composite
table, whole-equation meaning, and whole-equation analogy. If a required
equation cannot be verified, do not write it: publish an obvious `partial`
warning and keep the report out of formal comparison.

Use one user-confirmed everyday scenario. Explain each concept, module,
equation, symbol, and important composite term with a concise, accurate,
jargon-free analogy. Explain the mapping fully once, then cross-reference it.
Analogy text may use only familiar people, physical objects, visible actions,
simple sensory qualities, and directly observable outcomes; never replace one
technical term with another abstract label or abbreviation. For every
non-obvious academic conclusion, explicitly connect the starting conditions,
intermediate reasoning steps, conclusion, and supported boundary so that a
reader can follow it without prior field knowledge.

Before publication, review every chapter for source fidelity, reusable source
footnotes, single-line prose layout, terminology localization, explanatory
closure, reasoning continuity, formula-card completeness, and concrete-language
analogy quality. Manually verify that every substantive Section 2 comparison
has either its verified local external PDF or the required source-limitation
label. For every Benchmark in Section 6, manually verify its source coverage,
description-parameter-results order, and required table-column roles. Run the
Markdown, mathematics, official Mermaid syntax, rendering, and relative-link
checks.
These structural failures block publication. An unavailable Markdown parser,
Mermaid parser, renderer, or required browser is itself a blocking audit
failure.

## Revision invariant

Keep only the candidate report in the hidden run directory while it awaits
approval. Put diffs, rendered pages, conversion stages, detailed audits, local
configuration, and one-off scripts in a randomly named system temporary
directory created with `create-temp`, then remove it with `cleanup-temp` when
its dependent step ends. Do not change the formal report until the user
explicitly approves promotion. Archive the old report, atomically promote the
candidate under the original PDF-matching stem with `promote-revision`, write
its compact state record with `record-state`, and remove the completed run
with the strictly scoped `cleanup-run` command. Retain only the latest replaced
report.

For a later revision, do not recursively read `.ai-paper-analysis`. Inspect the
formal report, directly cited PDFs or pinned code, its compact state record, and
the active candidate when one exists. Read an archive or project helper only
when the request specifically requires it. Do not persist a helper unless the
user individually approves it and it has no report-specific constants, a short
English purpose note, and a focused test.
