# Plain-Language Research Reports

Apply these rules while drafting and during the existing semantic review of
paper and category reports. They adapt Humanizer 3.1.0's editing
principles to factual research writing. Reports contain final content, without
intermediate drafts or editing notes.

## Meaning and reader

Assume only basic calculus, linear algebra, probability, and mathematical
statistics. Explain everything beyond that foundation through familiar actions
and those mathematical operations. This applies to prose, headings, tables,
diagram labels, and formula explanations in both paper and category reports.

At the first use of each necessary specialist term, give its plain meaning and
a concrete analogy, small simulation, or worked numerical example. Explain the
operation, not just a renamed object. Use the plain name consistently afterward;
briefly recall an earlier explanation only when needed. An acronym expansion or
a definition made of other unexplained terms is insufficient. Avoid introducing
terms that the explanation does not need.

Preserve method and experiment coverage, equations, numbers, units, conditions,
source attribution, and evidence locators. Retain the intermediate steps needed
to follow a conclusion. Introduce illustrative numbers as an example, keeping
them distinct from experimental measurements. Explain a paper's specific
contribution through supported differences, without inventing uniqueness or
turning a proposed application into a demonstrated result.

## Bilingual checks

Output supports Chinese and English only. The sole executable rule catalog is
[prose-rules.json](../contracts/prose-rules.json). Maintain each problem category
in both languages using natural constructions, not literal translations. A
language-specific subrule must state why the other language is inapplicable.
The scanner extracts candidates; the reviewer judges both matches and unlisted
paraphrases. A clean scan does not replace reading the prose.

## Information and structure

State the subject or finding directly. Each sentence must add information or a
necessary explanation. Remove staged introductions, inflated significance,
imagined objections, repeated conclusions, chat wrappers, and narration of how
the report was assembled or checked. Remove defensive tails such as "this does
not mean", "cannot establish", and "does not prove" that rebut an unasked
objection. Express the actual condition or finding directly. Keep an informative
comparison only when both sides supply facts needed to understand the method,
result, or mathematical relation. Source support and logical validity alone do
not make a sentence useful. Apply this equally to author-written caveats and
writer-added deductions. Introduce an example once; do not add a second sentence
defending its illustrative status.

Report a defect only when the paper explicitly identifies it or it follows
directly from the architecture. State the concrete cause and consequence; for
an architectural deduction, show the short reasoning and cite its premises.
A defect must identify a concrete mechanism, condition, and consequence. Merely
not claiming a broader theorem or not checking a larger problem is not a defect
to append. Do not turn a scope description into a denial of guarantees.
Do not add hypothetical failure lists or general warnings. Preserve actual
negative results, conflicting values, and missing measurements as direct facts
at the relevant location. Attribute a target-only account to the target authors
instead of appending a disclaimer.

Organize paragraphs around ideas, with clear referents and connected reasoning.
Merge fragments that merely label an input, operation, or result. Choose the
length needed for the explanation. Keep requested one-sentence summaries to
one sentence each. Use the agreed main scenario where it helps;
switch locally to a clearer example or numerical calculation when needed.

Give each representation a purpose: optional short glossaries index concepts,
diagrams show connections, tables present values or comparisons, and prose explains mechanisms
and conclusions. Explain what a table or diagram means without reciting every
cell or announcing a layout the reader can already see. Use brief cross-references
when a definition or mechanism has already been explained.

## Presentation and review

Use lists for genuinely parallel items or sequences and headings that describe
their contents. Avoid forced triads, decorative bold labels, repeated one-line
closers, and dashes used to string clauses together. Prefer ordinary punctuation
in prose; preserve punctuation in quotations, titles, names, numerical ranges,
mathematics, code, commands, paths, and link targets.

Judge scanner candidates in context; do not treat a match as an automatic deletion or a style score.
Technical uses, informative comparisons, and factual conditions remain.
Review every first-use explanation against the stated mathematical foundation
and check that its example actually explains the operation. Check defensive
wording semantically; deleting a negative word alone can change a true claim.
Review terminology problems under `terminology`; review scanner candidates, repetition, filler,
unclear organization, and missing reasoning under `reasoning`. Give an exact
passage and repair condition through the existing issue workflow. Check that
the repair preserves facts and evidence; no additional review round is needed.
