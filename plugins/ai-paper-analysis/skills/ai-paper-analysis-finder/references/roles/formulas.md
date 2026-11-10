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

Immediately below, place a table with these semantic columns translated into
the output language:

| Symbol | Meaning | Analogy | Role in the Formula |
| --- | --- | --- | --- |

Include every symbol and meaningful composite term. Then explain the equation's
overall meaning, mechanism, module role, shared-scenario analogy, and the
technical limits of that mapping. Keep the technical limits clearly distinct
from the everyday analogy, using sentences or paragraphs as needed. Follow
[report-style.md](report-style.md); fixed labels and paragraph counts are not
required. Use brief reminders or cross-references for unchanged definitions
and mappings, while keeping every symbol and composite term in the card's table.

Give each displayed core equation its own formula-card heading, table,
explanation, and reusable source locator. Do
not place two displayed equations above one shared table or combine several
cards under one heading. Include a core-equation coverage table before the cards
that maps each original page, equation, or theorem locator to exactly one card
or to a supported non-core omission reason.

## Shared-scenario map

Settle the scenario in the initial plan, preferring one used by the paper.
When source inspection is deferred, follow the planned selection criteria and
keep one concrete scenario consistent throughout the report.

Maintain a consistent working map for every concept, assumption, module,
benchmark, core equation, symbol, and important composite term. Fully explain
the mapping on first use. Later occurrences may use a brief reminder or
cross-reference.

## Concrete-language gate

Apply this gate to scenario names, analogy prose, and every analogy table cell.
Use only familiar people, physical objects, visible actions, simple sensory
qualities, and directly observable outcomes. Do not use abbreviations,
mathematical symbols, method names, academic terms, or abstract substitute
labels such as *model*, *system*, *mechanism*, *state*, *slot*, *coordinate*,
*dimension*, *distribution*, *representation*, *network*, *parameter*, or
*digital twin*. This list illustrates the semantic rule; it is not a token
blacklist.

An analogy must describe what a concrete person or object does and what someone
can observe. It must not merely rename a technical object. If a word needs a
special definition before a general reader can picture it, rewrite the analogy
without that word. For example, reject "a residential digital twin has state
slots." Prefer "a person writes whether the lamp is on, whether the curtain is
closed, and how warm the room feels in three separate boxes on paper."

Keep the analogy concise, vivid, and accurate. Put any mapping limitation in the
technical explanation required above, where defined technical language
may be used. Run a semantic concrete-language review rather than relying on a
vocabulary heuristic; passing a token check does not prove that an analogy is
ordinary, understandable, or accurate.
