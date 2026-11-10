# Whole-Category Report Writer

Own one complete three-section candidate. Read
[category-content.md](category-content.md), [relationships.md](relationships.md),
[evidence-policy.md](evidence-policy.md), [report-style.md](report-style.md), and
[report-editing.md](report-editing.md); use
[../templates/category-report.md](../templates/category-report.md). Receive the
approved taxonomy, complete eligible corpus, scenario, reviewed paper reports,
original paths, and relationship evidence. Do not load lifecycle, reviewer,
reviser, source-provider, sibling Skill, or run-history instructions.

Before prose, write a temporary `coverage-matrix.schema.json` matrix covering
every required term, paper, relationship, comparison, subcategory, and report
output, with its numbered section, one exact heading or sentence fragment that
will occur once in that passage, and its required evidence locators. Write the
whole report in one pass using consistent localized terminology and parallel
comparisons.

After the complete candidate exists, run `prepare-report` once with the matrix,
evidence packets, category kind, and publication path, without `--render`.
Handle only listed coverage omissions in one batch and make one fast recheck;
do not perform an open-ended sweep or semantic-review revision.

Return the candidate path and version, automatic gate status, object counts,
and unresolved evidence gaps. Keep the matrix temporary. Do not publish or
write a separate timing or disposition artifact.
