# Complete-Candidate Semantic Reviewer

Review one complete candidate at the supplied version. The approved run
specification is mandatory input because it defines the source sets, language,
scenario, coverage, and publication intent. Read
[evidence-policy.md](evidence-policy.md), [report-style.md](report-style.md),
and only the relevant content rules:
[paper-content.md](paper-content.md) plus [formulas.md](formulas.md) for a paper,
or [category-content.md](category-content.md) plus
[relationships.md](relationships.md) for a category. Do not load acquisition,
lifecycle, writer, reviser, sibling Skill, unrelated draft, or run-history
instructions.

Use verified evidence packets as the complete-reading record. Do not reread all
external originals indiscriminately. Open exact original locators for formulas,
result tables, numerical or high-risk claims, disputed statements, packet
boundaries, and any place where surrounding context could change the meaning.
A packet, parser result, writer summary, or old receipt cannot by itself prove a
claim.

Review every section, table, diagram, formula card, footnote, and required
object once:

- **Source fidelity and coverage:** trace claims to the correct source class and
  precise locator; account for all terms, modules, equations, comparisons,
  Benchmarks, category members, conflicts, and limitations.
- **Terminology and reasoning:** first-use explanations let a reader without
  field knowledge follow the setup, operation, intermediate steps, conclusion,
  and boundary. Flag unexplained jargon, missing links, fragmented prose, and
  repeated boilerplate. Apply the style contract's `terminology` and `reasoning`
  criteria, preserving necessary definitions, qualifications, and evidence.
- **Formulas and analogy:** page verification, transcription, conditions,
  symbols, composite expressions, whole-equation meaning, technical boundary,
  and the one scenario are accurate and consistent.
- **Experiments and relationships:** original table values, precision,
  conditions, metrics, conclusions, Benchmark provenance, relationship enum and
  direction, reading order, assignments, and semantic IDs are supported.

Return one issue file conforming to
[../contracts/review-issues.schema.json](../contracts/review-issues.schema.json).
Give every issue an ID, report and source locator, impact, exact repair
condition, and `deterministic` or `semantic` classification. List an obsolete
literal only when that complete text must disappear. When closure requires a
specific evidence marker, record its locator ID and numbered report section so
`prepare-report --review-issues` can check it. Merge issues that require edits
to the same passage. When the correct replacement is fully determined from
evidence already inspected, include one exact `automatic_patch` old/new block;
otherwise set it to null. JSON escaping must preserve TeX bytes. Do not edit or
publish the candidate.

After automatic patches and any necessary residual edits, continue once in the
same reviewer thread with the baseline, complete diff, issue file, and affected evidence. Check every changed
passage and cross-section dependency, carry forward explicitly identified
unaffected coverage, and update issue outcomes instead of repeating the full
review. Close a deterministic issue only when the reported literal or
diagnostic is absent, and close a semantic issue only when the changed report
passage and exact source locator satisfy its repair condition. If broad or
repeated omissions remain, return one
consolidated failed/partial result and stop this candidate's review loop. Any
real unresolved defect remains blocking.

When all checks pass, create the assessment required by
[../contracts/report-review.schema.json](../contracts/report-review.schema.json).
Every numbered section must be covered. A genuine evidence gap uses visible
`partial` status; only coverage may be relaxed, while other semantic checks must
pass. `record-content-review` binds that assessment to final report bytes,
publication path, semantic policy, and stable originals.
