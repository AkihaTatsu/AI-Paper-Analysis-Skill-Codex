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

For each core equation:

1. Render the original PDF page.
2. Compare operators, indices, superscripts, subscripts, grouping, cases, and
   equation number against the page.
3. Cite the original page with the report's reusable source-footnote protocol.
4. Expand only custom LaTeX macros, preserving mathematical structure and
   symbols.
5. Mark the formula verified only after this comparison.

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

Immediately below, place a table with these semantic columns translated into
the output language:

| Symbol | Meaning | Analogy | Role in the Formula |
| --- | --- | --- | --- |

Include every single symbol and every meaningful composite term. Then add:

- A cohesive explanation of the equation's overall meaning, mechanism, and
  role in the surrounding module.
- A cohesive explanation of the equation's overall shared-scenario analogy.
- A separate technical paragraph stating the limits of that mapping.
- Its reusable source footnote marker.

## Shared-scenario map

Prefer a scenario explicitly used by the paper. Otherwise present two or three
ordinary scenarios to the user in Plan Mode and confirm one.

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
separate technical paragraph required above, where defined technical language
may be used. Run a semantic concrete-language review rather than relying on a
vocabulary heuristic; passing a token check does not prove that an analogy is
ordinary, understandable, or accurate.
