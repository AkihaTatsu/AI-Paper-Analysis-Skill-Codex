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
Use a small paper-supported case when counts, combinations, or negative
conclusions would otherwise require the reader to supply a missing step.

For equations, explain inputs, operations, intermediate quantities, outputs, and
role. For theory, connect assumptions to the conclusion and the alternatives
they rule out. Define a metric's meaning, scoring, and preferred direction before
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
- A complete glossary covering every named nontrivial concept, abbreviation,
  method, module, dataset, metric, and task in the read main text and appendix.

Use the canonical output-language term as each glossary entry. Include an
original-language alias only when it meets the retention rule above or is
needed to disambiguate a cited proper name. The glossary must cross-reference
formula cards rather than duplicate every symbol. Keep entries brief and explain
how a concept is used where it first carries the prose argument.
A translation, acronym expansion, or definition using unexplained jargon is
not a sufficient explanation.

## 2. Core Content

Explain:

- The solved problem in one sentence.
- Complete input and output objects, how information moves between them, and
  why those boundaries matter to the solved problem.
- Innovations relative to every reference work the paper itself uses for its
  novelty argument. For each comparison, connect the referenced baseline, the
  paper's change, and the paper-stated consequence in cohesive prose.
  Distinguish paper-stated differences from later external comparisons.

Use the confirmed complete novelty-comparison set and verified originals under
[evidence-policy.md](evidence-policy.md). Support baseline details with that baseline's own
original, the target authors' novelty framing with the target paper, and any
explicitly labeled cross-paper inference with both sides. Apply the required
visible source-limitation wording when an original remains legally unavailable;
never invent the missing baseline detail.

## 3. Environment and Assumptions

Explain each environment setting and assumption, where it appears, how it
affects the method or claim, and why the paper says or structurally requires it.
Do not invent necessity arguments. Mark a narrow contextual interpretation as
interpretation.

## 4. End-to-End Flow

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
  and supported boundary conditions as a complete narrative.
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
and author conclusions. Apply the required visible limitation wording when a
defining original is legally unavailable, adding no unverified native detail.

Do not infer significance, causality, superiority, or generalization beyond the
paper's evidence.

## 7. Limitations and Future Work

Separate:

- Limitations stated by the paper.
- Limitations directly demonstrated by its assumptions or experiments.
- Future directions stated by the paper.
- Independently verified related papers for each direction.

Related papers require a separately approved search budget and original full
text. Explain similarities, differences, and relationship to the target paper
using a clearly labeled external evidence channel. Put each local external PDF
link only in the corresponding footnote definition, using the portable relative
path `<target-stem>_references/<external-paper-stem>.pdf`.

Only semantically reviewed complete reports are eligible for category
comparison.
