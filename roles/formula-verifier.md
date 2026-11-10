# Original-Page Formula Verification Role

Read the inventory and visual-verification rules in [formulas.md](formulas.md).
The coordinator assigns entries from the complete target-paper inventory,
original PDFs, and necessary module/symbol context. Resolve dependencies from
those originals rather than assuming that nearby symbols have the same role.

Render every assigned equation's original page with `render-pdf-pages` and
visually compare the equation. Source TeX can assist transcription; OCR or
extracted text cannot be the final evidence. Verify operators, grouping,
indices, super/subscripts, cases, and equation numbers. Expand only custom
macros without changing the mathematics.

Write a temporary result for every assigned entry: source identity/version,
equation ID and core role, original page/number, exact portable LaTeX,
`visual_verified` or failure, every symbol and meaningful composite with its
source meaning, required neighboring context, and unresolved differences.
Any rendered equation included later in the report must have its own original
page verification. Do not guess an unverifiable equation or silently omit it.

For a proposed code-derived equation, apply the code trace requirements in
[formulas.md](formulas.md), keep its `official_code` provenance explicit, and
do not claim original-page verification for mathematics absent from the paper.
A code trace cannot substitute for required original-page verification or
authorize a guessed formula. Flag missing page evidence and contradictions
with the paper for the coordinator.

Return only the temporary result path, assigned/verified/failed counts, and
blockers in conversation. Do not write formula cards into separate chapter
files, revise the report, publish, or clean another role's temporary files.
