# Public Contracts

These files are the canonical, versioned interfaces shared by all four Skills.
Generated copies under each Skill must match them byte for byte.

- `run-spec.schema.json` defines the confirmed execution specification.
- `evidence-cache.schema.json` defines concise project-local coverage and locator records.
- `coverage-matrix.schema.json` binds each temporary checklist row to one exact
  report passage, numbered section, and evidence set.
- `review-issues.schema.json` defines the reviewer's single consolidated repair
  handoff, guarded exact patches, and machine-checkable closure conditions.
- `semantic-policy.json` names the semantic policy version and narrowly compatible legacy hashes.
- `artifact-state.schema.json` defines the compact state retained for one
  published formal artifact.
- `classification-row.schema.json` defines one RFC 4180 CSV row.
- `taxonomy.schema.json` defines exclusive categories and subcategories.
- `relationship-record.schema.json` defines paper relationship edges.
- `provider-registry.json` defines built-in discovery and retrieval sources.
- `execution-plan.md` defines the shared execution checklist, native plan-tool
  usage, progress updates, and text-table fallback.

Schema identifiers are stable. Breaking changes require a schema-version and
plugin-version update.

- `tool-capabilities.json` defines shared tools and transitive Skill/role requirements.
- `report-review.schema.json` binds an actual semantic review to artifact, source, and policy fingerprints.
- `artifact-state.schema.json` accepts legacy version 1 records and version 2 records with optional compact reviews.
