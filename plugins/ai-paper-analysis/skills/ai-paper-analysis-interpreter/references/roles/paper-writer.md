# Whole-Paper Report Writer

Own one complete seven-section candidate. Read
[paper-content.md](paper-content.md), [formulas.md](formulas.md), and
[evidence-policy.md](evidence-policy.md), [report-style.md](report-style.md), and
[report-editing.md](report-editing.md); use
[../templates/paper-report.md](../templates/paper-report.md). Do not load source
acquisition, lifecycle, reviewer, reviser, sibling Skill, or run-history
instructions.

On a target cache miss, read the complete paper, appendix, and relevant
supplement while building the term, module, experiment, comparison, and
core-equation inventories. On a validated complete target hit, reuse those
inventories. In either case, visually verify report equations on their original
pages and open only exact original context needed for a packet gap or conflict.

Before prose, write one temporary matrix conforming to
`coverage-matrix.schema.json`. Give every required term, equation, module,
comparison, experiment, metric, and workflow output a unique row, its intended
numbered report section, a short exact heading or sentence fragment that will
occur once in that passage, and every evidence locator that passage must cite.

Write the whole report in one pass using the approved language and scenario.
Apply the linked content, formula, and evidence contracts while drafting; do not
stop for paragraph review or chapter approval. Stable evidence markers belong
on the factual sentence they support, and `prepare-report --evidence` owns their
definitions.

Only after the complete candidate exists, run `prepare-report` once with the
matrix, all evidence packets, report kind, and publication path, without
`--render`. If it reports matrix omissions, fix only those listed passages in
one batch and make one fast recheck. Do not start a manual row-by-row sweep,
general polish pass, or revision of semantic-review issues.

Return the candidate path and version, automatic gate status, object counts,
and unresolved evidence gaps. Keep the matrix temporary. Do not publish or
write a separate timing or disposition artifact.
