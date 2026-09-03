# Evidence and Source Isolation

## Source classes

Use exactly four source classes:

- `paper`: the target main paper.
- `supplement`: verified supplementary material for the same paper.
- `official_code`: an author-controlled or paper-linked repository at a pinned
  commit.
- `external_paper`: independently acquired original papers used for novelty
  comparison, Benchmark evidence, or later context, limitations, and future
  directions.

Do not silently move a claim between source classes.

## Source footnotes

Cite every coherent factual paragraph, formula, result, and paper-relationship
statement with a Markdown footnote marker such as `[^paper-s3-2-e7]`. Put all
footnote definitions at the end of the report. Each definition must contain a
direct inline link to the supporting source file plus its precise page,
section, equation, figure, table, commit, or line locator. Do not use visible
bracket anchors such as `[Paper p. 4]`; do not put evidence links directly in
prose; and do not add a separate layer of reference-style link definitions.

Name a footnote by its source and locator rather than by claim order. Reuse the
same identifier wherever the exact source-and-locator bundle recurs. Cite a
coherent paragraph once at its end instead of repeating a marker after every
sentence. A single footnote may list multiple direct sources only when the
claim genuinely depends on them; do not merge unrelated evidence merely to
reduce the note count.

Footnote sources are limited to the target paper PDF, its supplement PDF,
pinned official-code files, and verified external-paper PDFs. Do not cite,
link, or name run specifications, event logs, ledgers, candidate tables,
preflight results, page renders, extracted text, audits, report drafts, or any
other generated intermediate artifact in the formal report. Process disclosure
may describe what was done without naming those files or treating them as
evidence.

## Official code

Prefer repository links found in the paper or supplement. Otherwise require a
provenance chain through an author-controlled project page or organization. Ask
when multiple plausible repositories remain.

Pin the paper-linked tag, release, or commit. If only a branch exists, record
its HEAD commit identifier and retrieval date. Cite code claims through
footnotes that link to the pinned file and line range. Do not execute untrusted
repository code merely to interpret it.

If code and paper disagree, show both. Mark the conflict unresolved, identify
affected conclusions, and block those conclusions. Do not declare one source
the winner merely because it is newer.

## External papers

### Novelty-comparison papers

Derive and confirm a finite set from the target paper's novelty argument before
drafting Section 2. Include every named work actually used to describe a
baseline's setting, assumptions, method, guarantee, or difference. A collective
claim about a named group requires the original for every paper in that group.
Exclude citations used only as background, datasets, tools, or borrowed
components. This mandatory set is independent of and is not capped by the
future-work search budget.

Use Finder rules to acquire the exact cited work, then verify and read its
complete original full text. Do not substitute a survey, a nearby paper,
metadata, or an abstract. Acquire and read the supplement as well when the
comparison depends on it. Reuse an existing local PDF only after its identity
and version are verified.

Use the target paper or supplement to support how its authors frame the
contribution. Use each external original to support that baseline's own inputs,
assumptions, method, and conclusions. A cross-paper derived difference must cite
both sides and be visibly labeled as an external cross-paper comparison.

If no legal full-text copy is available after exhausting the confirmed source
set, the report may paraphrase only the target paper's characterization. Label
the passage "target paper's characterization only; no independent full-text
comparison," add no unverified detail about the baseline, and do not present it
as a detailed original-paper comparison.

### Benchmark-source papers

Derive and confirm a finite set after reading the target paper. Include every
independently published original that defines a Benchmark, dataset, or
environment and whose full text is needed to support the report's description
or parameter explanation. Do not include a method paper merely because its
name appears in a result-table row; apply the novelty-comparison rule when the
report makes a substantive method or difference claim. A Benchmark introduced
and fully defined by the target paper requires no duplicate external source.
This mandatory set is not capped by the future-work search budget.

Use Finder rules to acquire and verify the exact original full-text PDF. Do not
substitute a survey, nearby paper, metadata record, abstract, website, or code
documentation. Use the external original for the Benchmark's provenance,
construction, native setting, and defining characteristics. Use the target
paper or supplement for the settings it actually adopts, its reported results,
and its authors' conclusions. Cite both sides for a derived cross-paper claim.

If no legal full-text copy is available after exhausting the confirmed source
set, paraphrase only the target paper and label the affected subsection
"target paper's characterization only; Benchmark source not independently
verified." Add no externally attributed or inferred Benchmark detail.

### Future-work papers

Use Finder rules with separately confirmed date/source boundaries, target count
per future direction, and candidate cap. Acquire and verify original full text.
Do not use metadata-only or abstract-only records for substantive comparison.

For a target PDF named `papers/<target-stem>.pdf`, publish verified external
paper PDFs under
`papers/<target-stem>_references/<external-paper-stem>.pdf`. Use each external
paper's normal artifact stem. Keep only PDFs in this directory. If one external
paper supports multiple target papers, publish a verified copy in each target's
directory.

When revising an existing report, atomically copy an external PDF from its old
location, validate the copied PDF's identity and structure, and update the
candidate report link. Keep the old file until a separately confirmed cleanup
removes it.

Place each external PDF link in its evidence footnote definition, not in the
report prose. Keep ordinary DOI or landing-page links only as non-evidentiary
metadata when useful.

Keep external claims visibly labeled. The target-paper sections must remain
understandable without treating external work as if the target paper said it.
