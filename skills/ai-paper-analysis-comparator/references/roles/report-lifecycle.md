# Complete Report Lifecycle

The coordinator owns this sequence, the approved run, and publication. Use one
whole-report writer, one semantic reviewer, and one fresh central reviser only
when automatic repair leaves residual issues. Never split a report into
separately written chapters.

## Shared tools and workspace

Use the calling Skill's `scripts/apa.py`. Run `tools list` and `tools doctor`,
then `tools ensure` only for missing approved capabilities. Validate the run
specification and call `init-run` during authorized execution. Reuse the
planning workspace and any prepared sources, following
[../contracts/execution-plan.md](../contracts/execution-plan.md) for temporary
instructions and cleanup. Keep extraction, renders, evidence packets, coverage
matrices, review issues, baselines, and diffs there. Complete source-dependent
input inventories before assigning their dependent writing or review work.

## 1. Reuse or prepare evidence

Call `lookup-evidence-cache` for every verified original. A validated hit may
replace repeated reading only for the same source bytes, policy, class, and
coverage fingerprint. A miss requires full assigned reading followed by
`record-evidence-cache`; that command writes, rereads, and validates the record
before returning `"hit": true`. Cache facts and locators, never source copies,
extracted text, or report prose.

For a paper report, a target cache miss stays with the writer, which reads the
complete paper, appendix, relevant supplement, and formula inventory in the
same context that writes the report. A validated complete target hit replaces
that repeated reading; the writer opens only exact target context needed for a
gap, conflict, or printed equation. Independent readers prepare external
packets. Category reports use only eligible reviewed paper reports and required
relationship evidence. Missing or unverifiable material remains a visible
limitation.

## 2. Write the complete candidate, then automate

Dispatch [paper-writer.md](paper-writer.md) or
[category-writer.md](category-writer.md) with the approved inputs. The writer
creates the complete report and a temporary coverage matrix before running:

```text
prepare-report CANDIDATE --report-kind paper|category --publication-path FORMAL_REPORT --evidence PACKET --coverage-matrix MATRIX
```

This invocation performs safe deterministic repairs and checks section-bound
evidence coverage without launching the browser. The writer handles any listed
coverage omissions in one batch and makes one fast recheck. It does not perform
an open-ended coverage or polishing sweep. A remaining failure is returned as a
blocker rather than hidden or retried indefinitely.

## 3. Review once and revise residuals once

Give the prepared candidate, coverage matrix, run specification, and verified packets to one
[semantic-review.md](semantic-review.md) reviewer. The reviewer reads the whole
candidate once and writes one issue file conforming to
`review-issues.schema.json`. Prose candidates from `audit-report-style` are
handled in this same review, including local grammar and stock wording. The
coordinator does not repeat this review.

If issues exist, first run the command below. It applies the reviewer's exact,
hash-guarded patches, performs safe deterministic repairs, and checks obsolete
text and section-bound evidence. This is the automatic repair attempt, not a
new review.

```text
prepare-report CANDIDATE --report-kind paper|category --publication-path FORMAL_REPORT --evidence PACKET --review-issues ISSUES
```

Only issues without an applicable exact patch go to one fresh
[report-reviser.md](report-reviser.md) worker, together with their IDs, affected
evidence, and relevant content contract. The reviser edits that residual set in
one batch and returns immediately; there is no disposition artifact or second
report sweep. Run the same command once more only after such manual residual
repairs.

Continue the original reviewer once with the baseline, complete diff, issue
file, and affected evidence. It checks changed passages and dependencies while
carrying forward unaffected coverage. Broad or repeated remaining defects end
this candidate as failed or partial; do not start another manual revision-review
loop. A localized defect may receive an automatic repair and changed-lines
confirmation only when the tool can make that repair safely.

## 4. Bind, render, and publish

After semantic passage and a final prose scan, use `record-content-review` with
all stable originals and exact justified `style_exceptions`. Missing or stale
exceptions block recording and publication even if every boolean check is true.
Then run `audit-paper-report` or `audit-category-report` with the receipt and
eventual publication path. This is the workflow's single complete browser
render and the final technical gate.

Publish according to the accepted plan. If promotion of the named report was
authorized there, archive and promote the audited candidate without another
confirmation. Otherwise deliver the candidate. Preserve compact content-bound
state and clean the task workspace after dependents finish. A visible partial
report may be published under the agreed limitation policy after structural
checks pass; only a complete paper report may enter category comparison.

The coordinator records role dispatch and completion times. Benchmark runs also
record tool-stage durations; workers do not create separate timing artifacts.
Use 75 minutes cold and 45 minutes warm as optimization references without
skipping evidence or accepting unresolved defects.

Final paper review binding requires the writer's temporary coverage matrix through
`record-content-review --coverage-matrix`. Keep the matrix until the final report
and its per-target demonstrations pass; the receipt retains the compact targets
and example quotations, so later audits do not need the temporary file.
