# Paper Report Specification

Write human-facing headings and content in the requested output language, but
preserve the numeric level-two section IDs. Keep one level-one title and exactly
these seven numbered sections.

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

Every substantive prose paragraph must form an explanatory closure: identify
the object or claim, explain its mechanism or reasoning, state why it matters
in the current section, and include any consequence, boundary, or contrast that
the paper supports. Use the shared analogy to deepen this explanation, not to
replace it. Combine adjacent micro-paragraphs that merely label an input,
operation, effect, or locator. Tables and diagrams organize evidence but do not
replace connected prose; introduce them and synthesize the relationships they
show.

Do not impose a word or sentence quota and do not pad unsupported detail. The
required one-sentence problem statement, headings, equations, table cells,
captions, source locators, lists, and code or Mermaid blocks are structural
elements rather than substantive prose paragraphs.

## Novice-facing reasoning

For every non-obvious academic conclusion, present the reasoning in dependency
order: define or recall the starting conditions, state the operation or
comparison, derive each intermediate result, state the conclusion, and then
give its supported boundary. Use one new inference per sentence whenever
combining steps would force the reader to supply a missing link. Give every
pronoun and transition an explicit referent, and define an unfamiliar term
before it carries part of the argument.

Unpack counts, combinations, comparisons, and negative conclusions with a
small paper-supported case. Do not replace a necessary step with words such as
"usually," "clearly," or "therefore." For example, do not stop at "a rotated
coordinate usually needs three or more means and cannot use one binary gate."
First hold the history fixed, state why each original quantity has two possible
centers, show how mixing their choices can create more than two centers, compare
that result with the two choices allowed by one binary gate, and only then state
why the mixed coordinate falls outside the assumed form.

For an equation, follow input, operation, intermediate quantity, output, and
role. For a theoretical result, follow assumptions, the alternatives they rule
out, and the conclusion. For an experiment, follow setup, measurement,
observation, comparison, and the conclusion the evidence supports. Reorganize
paper material when needed for clarity, but do not invent an intermediate fact;
label a narrow explanatory inference or omit it when the source does not
support it. A reader who knows only the preceding report content must be able to
restate why the conclusion follows.

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
formula cards rather than duplicate every symbol.

## 2. Core Content

Explain:

- The solved problem in one sentence.
- Complete input and output objects, how information moves between them, and
  why those boundaries matter to the solved problem.
- Innovations relative to every reference work the paper itself uses for its
  novelty argument. For each comparison, connect the referenced baseline, the
  paper's change, and the paper-stated consequence in cohesive prose.
  Distinguish paper-stated differences from later external comparisons.

Before drafting these comparisons, confirm the finite novelty-comparison set.
Include every named work actually used for a substantive statement about a
baseline's setting, assumptions, method, guarantee, or difference. A collective
claim about a named group requires every original paper in that group. Exclude
citations used only for background, datasets, tools, or borrowed components.
This set is mandatory and is not capped by the Section 7 related-work budget.

Read a verified local original full-text PDF for every work in the set, plus its
supplement when the comparison depends on it. Cite the target paper or
supplement for its authors' novelty framing, cite the external original for the
baseline's own details, and cite both source sides for a derived difference;
label the latter as an external cross-paper comparison.

If no legal full text is available after the confirmed search is exhausted,
paraphrase only the target paper and label the passage "target paper's
characterization only; no independent full-text comparison." Do not add
unverified baseline details or call the result an independent detailed
comparison.

## 3. Environment and Assumptions

Explain each environment setting and assumption, where it appears, how it
affects the method or claim, and why the paper says or structurally requires it.
Do not invent necessity arguments. Mark a narrow contextual interpretation as
interpretation.

## 4. End-to-End Flow

Provide one complete Mermaid flow from input to output. Include state,
iterations, branches, stopping conditions, and outputs where present. Wrap
modules in `subgraph` blocks. Follow the direction threshold in the Markdown
profile.

Follow the graph with a module table and cohesive prose explaining the role,
input/output boundary, interactions, and downstream effect of every module. The
graph is navigation, not a replacement for prose.

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

1. Detailed prose describing its origin, task, data or environment,
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
4. Cohesive prose that walks through the relevant rows and columns, explains
   the comparison, states the authors' conclusion, and limits it to the
   evidence shown.

This form is structural rather than metric-specific: a controlled result may
place source-reported condition columns before `Method`, while an unconditional
result begins with `Method`. Never force one paper's conditions or metrics onto
another paper. Case Studies retain the general requirements above unless the
paper also treats them as Benchmarks.

Before writing a Benchmark subsection, confirm the finite set of independently
published originals needed to define its Benchmark, dataset, or environment.
Read each verified local full-text PDF and place it under the target paper's
reference directory. Use those originals for provenance and defining details;
use the target paper or supplement for adopted parameters, result values, and
author-stated conclusions. A target-paper-introduced Benchmark needs no
duplicate source, and a result-table baseline alone does not trigger a download
unless the prose makes a substantive claim about that method.

If a required legal full text remains unavailable after the confirmed search,
label the subsection "target paper's characterization only; Benchmark source
not independently verified," use only target-paper-supported facts, and do not
claim independent Benchmark verification.

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

## Final audit

Review each numbered section rather than sampling. Check reusable source
footnotes, exclusion of generated intermediates, single-line prose layout,
terminology localization, explanatory closure, reasoning continuity, formula
cards, concrete-language analogy coverage, Mermaid, Markdown, and source-channel
isolation. For every substantive Section 2 comparison, manually confirm either
a verified local external PDF or the required source-limitation label. For every
Section 6 Benchmark, manually confirm the local source PDF or required
limitation label, the four-part content order, the three parameter-table core
columns, and the source-faithful result-table column order. Correct every
discovered deviation before publication. Report `structure-valid` separately
from `content_status=complete|partial`; only complete reports are eligible for
category comparison.
