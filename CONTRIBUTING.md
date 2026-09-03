# Contributing

Use English for maintained repository content. Keep generated contracts and
plugin copies synchronized with their canonical sources.

Before opening a change, run `uv run python scripts/release_check.py`. Use
`--live` only when the change needs real provider verification and suitable
credentials are already configured.

Do not add real credentials, copyrighted paper corpora, or private laboratory
artifacts to tests. Use synthetic fixtures.
