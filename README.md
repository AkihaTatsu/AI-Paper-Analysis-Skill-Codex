# AI Paper Analysis

AI Paper Analysis is a Codex plugin and standalone Skill suite for legal paper discovery, source-grounded paper interpretation, exclusive classification, and auditable category comparison. Reports may use the language requested by the user; maintained Skill instructions, code, schemas, and repository documentation are English.

## Included Skills

- `$ai-paper-analysis` routes a request through the smallest required workflow and requires the three child Skills to be installed.
- `$ai-paper-analysis-finder` is independently installable and handles discovery, legal PDF acquisition, identity and relevance checks, and optional exclusive classification.
- `$ai-paper-analysis-interpreter` is independently installable and creates or revises detailed seven-section paper reports from verified original sources.
- `$ai-paper-analysis-comparator` is independently installable and creates category reports from verified classifications and complete paper reports.

The router is eligible for automatic selection. The child Skills are explicit-only. A child Skill does not require the router or its siblings, while the router stops and identifies any missing child instead of imitating it.

## Prerequisites

- Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).
- Node.js 20 or newer and npm for report audits. The renderer prefers an installed Chrome, Chromium, or Edge executable; if none is available, it installs the locked headless shell in the shared cache.
- Network access for discovery and first-use dependency installation.
- Optional: SOPS and age for encrypted project credentials, and OCRmyPDF for user-approved OCR.

The Skill launchers create no virtual environment inside an installed Skill or paper library. They use a locked, versioned cache under the platform cache directory, or `APA_CACHE_DIR` when set. Installing a child first and the router or full plugin later reuses a compatible runtime instead of reinstalling it. Renderer dependencies are added lazily only when an interpretation or comparison audit needs them. Incompatible future runtime APIs can coexist, and only the two newest initialized versions of each layer are retained.

## Install as a plugin

Clone the repository, register its local marketplace, and install the plugin:

```bash
git clone https://github.com/AkihaTatsu/AI-Paper-Analysis-Skill-Codex.git
codex plugin marketplace add /absolute/path/to/AI-Paper-Analysis-Skill-Codex
codex plugin add ai-paper-analysis@ai-paper-analysis
```

The plugin contains the router and all three child Skills. Start a new Codex thread after installation or update so the available Skills are refreshed.

## Install standalone Skills

Copy only the required directories from `skills/` into the Codex Skill directory. For example, this installs Finder without the other capabilities:

```bash
cp -R skills/ai-paper-analysis-finder ~/.codex/skills/ai-paper-analysis-finder
```

Install all three child directories before installing `skills/ai-paper-analysis` when the router is required. A later child or router installation detects and reuses the shared cached runtime created by an earlier child.

## Install the local Python distribution

The wheel exposes the deterministic runtime CLI independently of Codex Skill discovery:

```bash
uv build
uv tool install ./dist/ai_paper_analysis-0.1.0-py3-none-any.whl
ai-paper-analysis-runtime providers
```

The repository supports local wheel and source-distribution builds. It does not automate publishing to PyPI or GitHub Releases.

## Credentials

Environment variables take precedence. Supported adapters use `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `UNPAYWALL_EMAIL`, and the configured Scholar endpoint or token variables documented by the selected provider. Alternatively, pass an explicit SOPS file or place it at `<target-root>/.ai-paper-analysis/credentials.sops.yaml`.

```bash
sops <target-root>/.ai-paper-analysis/credentials.sops.yaml
```

Keep age private keys outside the project. If encrypted configuration is selected but either `sops` or `age` is missing, that credential source stops with a concise setup error. Decrypted values are kept in memory and are never written to run specifications or logs.

## Repository layout

- `skills/` contains the canonical, independently installable Skills.
- `src/ai_paper_analysis/` contains the canonical deterministic runtime.
- `contracts/` and `templates/` contain public artifact contracts and report templates.
- `plugins/ai-paper-analysis/` is the generated complete plugin mirror.
- `.agents/plugins/marketplace.json` exposes the local repository marketplace.

Generated Skill runtimes and the plugin mirror must match canonical sources. Regenerate them with `uv run python scripts/sync_materialized.py`; verify without changes by adding `--check`.

## Development and release checks

Install locked dependencies and run the single local gate:

```bash
uv sync --all-extras
uv run python scripts/release_check.py
```

The default gate is deterministic and offline except for dependency installation. Add `--live` to run opt-in provider checks; temporary provider failures are reported separately from deterministic failures. CI covers Python 3.11 through 3.14 on Linux, baseline Linux, macOS, and Windows compatibility, and one full report-template rendering smoke test. It does not publish or release artifacts.

## Safety, support, and access

The project never bypasses paywalls, CAPTCHAs, robots exclusions, rate limits, or access controls. PDFs, metadata, Markdown, and linked repositories are treated as untrusted input, and paper-linked code is inspected but not executed merely for interpretation. Do not commit real credentials, copyrighted paper corpora, or private laboratory artifacts. Report all defects and security concerns through the repository's public GitHub Issues page.

## License and acknowledgements

Original code and documentation are licensed under the MIT License. The interaction design was informed by the public structure of [Matt Pocock's skills repository](https://github.com/mattpocock/skills), and the evidence workflow was informed by the public [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills) and [ARS-Codex](https://github.com/Imbad0202/academic-research-skills-codex) repositories. No third-party Skill text, prompts, templates, paper reports, or code are copied into this repository. Local laboratory reports were consulted only as read-only design references; their text, private paths, and paper content are not included.
