# Auditable Paper Relationships

Use only these directed relationship values:

| Value | Subject paper's relationship to object paper |
| --- | --- |
| `depends_on` | Requires the object's central result, method, or formulation. |
| `extends` | Adds a capability or component while retaining the object's core. |
| `improves_on` | Demonstrates a supported improvement on the same target. |
| `generalizes` | Broadens scope or relaxes a limiting assumption. |
| `specializes` | Tailors the object to a narrower setting. |
| `adapts_to` | Transfers the object to a new domain, task, or environment. |
| `combines_with` | Integrates the object with another distinct line. |
| `simplifies` | Removes assumptions, components, or cost while preserving purpose. |
| `evaluates` | Primarily tests or benchmarks the object. |
| `reproduces` | Replicates or independently validates the object. |
| `contrasts_with` | Presents an evidence-backed alternative or conflicting claim. |
| `surveys` | Synthesizes the object as part of a broader review. |

An edge states `subject -> relation -> object`. Do not use chronology alone as
a relationship. Do not invent an edge because two papers share a keyword or
subcategory.

Every edge requires a temporary relationship-ledger record containing both
paper IDs, the enum value, source class, and locator. Use it for validation,
then delete it with the temporary workspace unless the user explicitly
requested it as a formal output outside `.ai-paper-analysis`. Prefer direct
statements from the subject paper. When a relationship is an explicitly
labeled synthesis across verified evidence, record every supporting locator
and keep the claim narrow.

If no enum accurately describes the evidence, omit the edge and explain the
absence in prose. There is no `other` escape value.
