# Formula and Analogy Protocol

## Core-equation inventory

Before drafting equations, inventory every equation that defines:

- The algorithm or system transformation.
- A training or optimization objective.
- A state or parameter update.
- A constraint, assumption, estimator, or decision rule.
- A theorem statement or key quantitative conclusion needed by a module.

Non-core derivations may be summarized, but the inventory must explain why they
are non-core. Sampling a few convenient equations is not acceptable.

## Visual verification

For each core equation printed in a paper:

1. Render the original PDF page.
2. Compare operators, indices, superscripts, subscripts, grouping, cases, and
   equation number against the page.
3. Cite the original page with the report's reusable source-footnote protocol.
4. Expand only custom LaTeX macros, preserving mathematical structure and
   symbols.
5. Mark the formula verified only after this comparison.

When two cited parts of the same source disagree in symbols, dependencies,
signs, or optimization direction, preserve both printed forms, state the
conflict, and limit the interpretation instead of silently harmonizing them.

Apply the same check to additional paper equations, including inline ones.
For explicitly labeled code-derived equations absent from the paper, use the
pinned-code tracing protocol below instead; never attribute them to the paper.

Do not use OCR text as final equation evidence. Official source TeX can assist
transcription but does not replace the original-page comparison.

If the equation cannot be verified, explain the failure in the report, display
a `partial` status, and do not render a guessed equation.

## Formula card

Write inline mathematics only with `$...$`. Write a display equation only as:

```text
$$
portable LaTeX
$$
```

Use `$...$` directly from the first draft, including in every table cell. Never
use `\(...\)` as an intermediate form or rely on a later delimiter conversion.
Before publication, resolve every parenthesized identifier, shape, range,
comparison, or TeX-like fragment as either `$...$` mathematics or backticked
code.

For an equation derived from code rather than printed in the paper, trace the
value through every later scale, limit, clip, or storage operation. Give raw
intermediates and stored outputs distinct symbols, verify the branch guard, and
never assign a pre-transform distribution directly to a post-transform value.

Immediately below each displayed core equation, give a compact table of its
symbols and meaningful composite terms, with localized columns:

| Symbol or important term | Plain meaning and role |
| --- | --- |

Explain the calculation through basic calculus, linear algebra, probability,
and statistics: what enters, what operations occur, what comes out, and why the
module needs it. Give each new specialist concept a concrete analogy, small
simulation, or numerical example. Explain introduced notation before using it
to explain another concept. Preserve the original equation; simplicity belongs
in its explanation, not an altered mathematical claim.

Reuse established definitions with short reminders or cross-references in the
table. Basic symbols need meanings, not a separate forced metaphor. A new
example should explain an operation or relationship; do not merely rename
symbols as objects. State illustrative values as examples, separate from paper
measurements. Omit ritual warnings about what an analogy does not establish.

Give each displayed core equation its own heading, table, explanation, and
source locator. Include a compact core-equation coverage table mapping each
original locator to its card or a supported non-core omission reason. Keep
coverage bookkeeping out of the explanatory prose.

## Connected examples

Choose a main scenario during planning, preferably grounded in the paper's
objects. Reuse its meanings consistently. Allow a local numerical example,
small simulation, or different familiar scene when it makes a concept easier
to understand. The existing scenario field records this main scenario and the
agreed use of local examples.

Follow [report-style.md](report-style.md) for first-use explanations and review.
An example must show an action or calculation and its observable result. A
reader should understand it without learning another specialist vocabulary.
Use basic mathematical language freely where it is clearer than a physical
metaphor. Review the correspondence for accuracy within the existing semantic
review, without requiring a separate boundary paragraph for each example.
