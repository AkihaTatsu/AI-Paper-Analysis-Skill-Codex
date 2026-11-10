# Exclusive Classification Contract

The coordinator reads this role only for requested classification. Workers
return proposed assignments and ambiguities; the coordinator owns all user
questions, confirmed atomic replacements, and formal publication.

Classification is optional. Do not create taxonomy or classification artifacts
when the user did not request them.

## Taxonomy

If the user does not provide a complete taxonomy, propose one with:

- Stable English IDs and user-language names.
- A definition for every category and subcategory.
- Positive inclusion tests and explicit exclusion boundaries.
- Mutually exclusive distinctions that cover the accepted corpus.

Settle the taxonomy or its derivation criteria in the initial plan. The
coordinator reviews derived definitions against those criteria before use;
ask again only when a necessary change exceeds that scope. Save the definitions
and confirmation metadata only at
`<target-root>/taxonomy.json`; save assignments only at
`<target-root>/classification.csv`.

## Assignment review

Assign each paper to exactly one category and exactly one subcategory. Provide
the category, subcategory, short reason, and a paper locator. Review the complete
table against the accepted taxonomy. Resolve ambiguities from evidence and
the planned criteria; ask only about essential decisions those cannot settle.

Use the fixed 25-column CSV contract from [../contracts/classification-row.schema.json](../contracts/classification-row.schema.json). Encode
authors as a JSON array string and write RFC 4180 UTF-8 CSV. The CSV is
authoritative for assignments; `taxonomy.json` is authoritative for category
definitions.

Set `review_status=confirmed` only after the coordinator has reviewed the
complete table within the accepted plan. Record the plan and actual review
basis in confirmation summaries; do not imply the user inspected derived rows.
Set `verification_status=verified` only when identity, classification evidence,
and required local files pass. Leave report fields empty until a verified
report exists; update them only through an audited, authorized atomic CSV
replacement.

Before category comparison, require nonempty PDF/report paths, existing files, a
`structure-valid` report audit with `content_status=complete`, current content
review from an active receipt or the compact artifact state, and exact Paper
ID, Category ID, and Subcategory ID values inside the report's basic
information section. This semantic cross-check prevents
structurally valid but meaningfully inconsistent manifests.

The compact `<report-stem>.paper-report.json` record carries the published
review summary. Validate its report hash, source versions, and policy when the
report is used. Do not require the old temporary receipt to survive cleanup or
re-review a still-valid report solely because that file was removed.
