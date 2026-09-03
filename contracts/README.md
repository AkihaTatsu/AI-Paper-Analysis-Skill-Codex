# Public Contracts

These files are the canonical, versioned interfaces shared by all four Skills.
Generated copies under each Skill must match them byte for byte.

- `run-spec.schema.json` defines the confirmed execution specification.
- `artifact-state.schema.json` defines the compact state retained for one
  published formal artifact.
- `classification-row.schema.json` defines one RFC 4180 CSV row.
- `taxonomy.schema.json` defines exclusive categories and subcategories.
- `relationship-record.schema.json` defines paper relationship edges.
- `provider-registry.json` defines built-in discovery and retrieval sources.

Schema identifiers are stable. Breaking changes require a schema-version and
plugin-version update.
