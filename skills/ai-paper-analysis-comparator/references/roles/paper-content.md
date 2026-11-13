# Paper Report Specification

Write human-facing headings and content in the requested output language, but
preserve the numeric level-two section IDs. Keep one level-one title and exactly
these seven numbered sections.

Read [report-style.md](report-style.md) for concise, novice-facing explanations
that preserve complete coverage and evidence.

## Output language and explanatory depth

Translate foreign-language terminology into the requested output language
throughout headings, prose, explanatory table cells, captions, Mermaid labels,
formula explanations, and analogies. Retain a foreign term only when it cannot
be translated reliably or when its original name is the overwhelmingly
conventional identifier, such as a named paper method, dataset, benchmark, or
established abbreviation. Explain a retained name in the output language on
first use. Exact bibliographic titles, author names, identifiers, URLs, code
identifiers, and mathematical symbols are not narrative terminology and may
remain unchanged. Do not preserve an ordinary translatable term merely for
traceability.

Use one consistent translated term for each concept. Before publication,
perform a semantic foreign-language review of human-facing content; do not use
a token counter or word blacklist as a substitute for judgment.

## Novice-facing reasoning

Explain non-obvious conclusions in dependency order, retaining the starting
conditions and intermediate steps needed to connect the evidence to the result.
Use a small worked example when counts, combinations, or conclusions would
otherwise require the reader to supply a missing step. Identify invented
illustrative values as examples, separate from the paper's measurements.

For equations, explain inputs, operations, intermediate quantities, outputs, and
role. For theory, connect assumptions to the actual conclusion; explain a necessary
alternative only when it helps follow the argument. Define a metric's meaning, scoring, and preferred direction before
interpreting its results. Reuse these explanations in later comparisons.
Label supported explanatory inferences; never invent an intermediate fact.

## 1. Overview

Include:

- A basic-information table with original title, translated title when useful,
  authors, year, venue, identifiers, canonical link, primary PDF version, paper
  type, and reusable source-footnote markers.
- Stable paper ID and, when classified, the confirmed category ID and
  subcategory ID. These IDs enable cross-artifact semantic auditing.
- Fields involved in the paper.
- A reading guide that tells a general reader what to notice and in what order.
- First-use explanations for specialist terms actually used in the report.

Explain terms in place, following the mathematical foundation and example rules
in [report-style.md](report-style.md). A short index is optional when it improves
navigation; do not reproduce the paper's vocabulary as a mandatory glossary.

## 2. Core Content

Use exactly two level-three subsections, localized into the output language:

### One-sentence overview

Write three items, each exactly one sentence, answering respectively:

1. What problem does the work solve?
2. What makes that problem distinctive, and what downstream use does it serve?
3. What specific contribution distinguishes this work from similar work?

Use ordinary language here; develop mechanisms in the following sections.
Ground applications and contributions in the sources, preserving whether an
application is proposed or demonstrated.

### Differences from related work

Cover every reference work used in the paper's substantive novelty argument.
Connect each baseline's approach, the paper's change, and its consequence in
plain prose. Level-four headings may separate comparisons. Distinguish the
paper's comparisons from verified later comparisons.

Use the confirmed complete novelty-comparison set and verified originals under
[evidence-policy.md](evidence-policy.md). Support baseline details with that baseline's own
original, the target authors' novelty framing with the target paper, and any
explicitly labeled cross-paper inference with both sides. When an original is
outside the approved source scope or unavailable, use the agreed target-only
policy and direct attribution; never invent the missing baseline detail.

## 3. Environment and Assumptions

Explain each environment setting and assumption, where it appears, how it
affects the method or claim, and why the paper says or structurally requires it.
Do not invent necessity arguments. Mark a narrow contextual interpretation as
interpretation. State actual conditions directly, without appending denials of
general guarantees or hypothetical reader interpretations.

## 4. End-to-End Flow

Before the graph and module table, state the overall input and output whenever
the work has them. Describe the actual objects and relevant shapes or units;
separate training from model use when their inputs or outputs differ. Keep the
whole-model boundary visible instead of leaving it scattered across module rows.

Provide one complete Mermaid flow from input to output. Include state,
iterations, branches, stopping conditions, and outputs where present. Wrap
modules in `subgraph` blocks. Read the shared
[Mermaid rules](../contracts/markdown-profile.md#mermaid) for simulated layout
selection and explanations that remain correct after automatic orientation changes.

Follow the graph with a module table covering every module's role, input/output
boundary, and downstream effect. Explain how modules interact in connected
prose; reserve their internal mechanisms for section 5.

## 5. Module Details

Give every paper-appropriate module its own level-three subsection. For each:

- State its inputs and outputs.
- Explain its central idea, mechanism, role, connection to adjacent modules,
  and necessary operating conditions as a complete narrative, following the
  shared prose rule rather than appending a scope disclaimer.
- Include every module-core equation required to define the method, objective,
  update, constraint, or key conclusion.
- Apply the formula-card protocol immediately after each equation.

For a theory, benchmark, empirical, case-study, or review paper, map "module"
to the corresponding proof component, evaluation design, data construction,
case mechanism, or synthesis theme. Explain the mapping and explicit
not-applicable items instead of deleting section intent.

## 6. Experiments and Results

Give each Benchmark or Case Study a level-three subsection. State:

- What it is and which evidence identifies it.
- Its defining characteristics.
- How it differs from every other included Benchmark or Case Study.
- The reported result, including metric, uncertainty, and comparison context
  when available.
- The conclusion the paper's authors draw from that result.

After presenting the individual facts, synthesize how the setup, distinguishing
features, result, and author-stated conclusion connect. Avoid leaving a
benchmark subsection as a table or sequence of atomic observations.

For every Benchmark, use this exact content order:

1. Concise prose describing its origin, task, data or environment,
   distinguishing features, and difference from the other included
   Benchmarks.
2. A parameter table with the localized core columns `Parameter or setting`,
   `Value`, and `Role in the evaluation`, in that order. Cover every reported
   split size, input shape, seed or repeat count, environment condition, and
   evaluation setting that materially affects interpretation. Append a
   paper-specific column only after these core columns. Write `not reported`
   rather than infer a missing value.
3. One experiment-results and comparison table. Preserve the source paper's
   exact result-table structure: place any conditioning columns first, then
   `Method`, then every reported metric column in source order. Preserve metric
   names, units, optimization arrows, uncertainty notation, row groupings, and
   reported precision. Collapse distinct baselines into a synthetic summary
   row only when the source reports that aggregate or every component value is
   source-verifiable; state the aggregation rule and never imply that such a
   row represents one baseline model.
4. Prose explaining the comparisons needed to support the authors' conclusion
   and its scope. Refer to relevant values without restating the entire table.

This form is structural rather than metric-specific: a controlled result may
place source-reported condition columns before `Method`, while an unconditional
result begins with `Method`. Never force one paper's conditions or metrics onto
another paper. Case Studies retain the general requirements above unless the
paper also treats them as Benchmarks.

Use the confirmed complete Benchmark-source set and source-channel rules in
[evidence-policy.md](evidence-policy.md). Cite verified defining originals for native
Benchmark properties and the target/supplement for adopted settings, values,
and author conclusions. When a defining original is outside the approved scope
or unavailable, attribute the description to the target paper and add no
unverified native detail.

Do not infer significance, causality, superiority, or generalization beyond the
paper's evidence.

## 7. Limitations and Future Work

Separate:

- Limitations stated by the paper.
- Defects directly deducible from the architecture, with their reasoning and
  source premises.
- Future directions stated by the paper.
- Independently verified related papers when future-work search is approved.

State concrete causes and consequences under the shared style rule. A missing
general guarantee or a restatement of method scope is not itself a defect.
State defects directly under the shared style rule. Do not fill the section
with hypothetical objections. Report experimental failures in section 6 and
avoid repeating their full explanation here.

Related papers require a separate search budget in the initial plan and original full
text. Explain similarities, differences, and relationship to the target paper
using a clearly labeled external evidence channel. Put each local external PDF
link only in the corresponding footnote definition, using the portable relative
path `<target-stem>_references/<external-paper-stem>.pdf`.

Only semantically reviewed complete reports are eligible for category
comparison.
