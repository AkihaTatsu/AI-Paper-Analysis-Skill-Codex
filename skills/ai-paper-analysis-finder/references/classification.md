# Exclusive Classification Contract

Classification is optional. Do not create taxonomy or classification artifacts
when the user did not request them.

## Taxonomy approval

If the user does not provide a complete taxonomy, propose one with:

- Stable English IDs and user-language names.
- A definition for every category and subcategory.
- Positive inclusion tests and explicit exclusion boundaries.
- Mutually exclusive distinctions that cover the accepted corpus.

Ask the user to confirm the taxonomy through the question tool before assigning
papers. Save the definitions and confirmation metadata only at
`<target-root>/taxonomy.json`; save assignments only at
`<target-root>/classification.csv`.

## Assignment approval

Assign each paper to exactly one category and exactly one subcategory. Provide
the proposed category, subcategory, short reason, and a paper locator. Batch
review ambiguous assignments, then show the complete table for final
confirmation.

Use the fixed 25-column CSV contract from `references/contracts/`. Encode
authors as a JSON array string and write RFC 4180 UTF-8 CSV. The CSV is
authoritative for assignments; `taxonomy.json` is authoritative for category
definitions.

Set `review_status=confirmed` only after complete-table confirmation. Set
`verification_status=verified` only when identity, classification evidence,
and required local files pass. Leave report fields empty until a verified
report exists; update them only through an audited, confirmed atomic CSV
replacement.

Before Comparator use, require nonempty PDF/report paths, existing files, a
`structure-valid` report audit with `content_status=complete`, and exact Paper
ID, Category ID, and Subcategory ID values inside the report's basic
information section. This semantic cross-check prevents
structurally valid but meaningfully inconsistent manifests.
