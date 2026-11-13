# AI Paper Analysis

AI Paper Analysis is a complete Codex plugin suite for legal paper discovery, source-grounded paper interpretation, exclusive classification, and auditable category comparison. Finder can also be installed on its own for paper discovery and classification. Generated reports and explanations support only Chinese (including simplified and traditional writing) and English; source-paper languages follow the approved research scope; maintained Skill instructions, code, schemas, and repository documentation are English.

## Included Skills

- `$ai-paper-analysis` coordinates discovery, interpretation and comparison, with a shared decision-tree interview and execution checklist.
- `$ai-paper-analysis-finder` discovers, acquires, verifies and optionally classifies papers.
- `$ai-paper-analysis-interpreter` creates complete seven-section paper reports and centrally revised candidates.
- `$ai-paper-analysis-comparator` produces category relationships, reading order and comparison reports from eligible inputs.

All four Skills are explicit-only: invoke `$ai-paper-analysis`, `$ai-paper-analysis-finder`, `$ai-paper-analysis-interpreter`, or `$ai-paper-analysis-comparator` manually. Each Skill can be installed independently and selects shared tools and role references instead of calling sibling Skills. Missing comparison reports use the same whole-paper writer as Interpreter, with the required scope confirmation and quality gates.

## Installation

Use Python 3.11 or newer and uv. Report capabilities also require Node.js 22.12 or newer and npm. Windows, macOS and Linux use the same Python installer; Bash is not required. Optional OCR, SOPS/age and access credentials retain their explicit setup and authorization boundaries.

From this checked-out repository, install one or more independent Skills:

```text
python scripts/install.py --skill finder
python scripts/install.py --skill interpreter --skill comparator
```

Install or update the complete plugin through the official Codex CLI:

```text
python scripts/install.py --plugin
```

`--destination` selects a Codex home (including for the plugin's official CLI calls); `--cache-dir` selects a shared tool cache. Installation resolves the selected Skills' and roles' capability closure, adds missing compatible dependencies, and performs real readiness checks before publishing the installation. Adding a Skill preserves existing capabilities. Managed standalone/plugin overlap is handled by the installer; unmanaged same-name content is reported as a conflict.

Small executable code has one versioned shared owner. Python dependency groups and Node/browser resources are shared, and incompatible versions coexist. No environments or tool copies are created inside a paper library. `APA_CACHE_DIR` overrides the platform cache location. Copying a Skill directory alone does not install its tools; use the installer. Start a new Codex thread after updating a plugin.

The wheel also exposes `ai-paper-analysis-runtime`. All Skills forward to this shared CLI; an installed Skill's `scripts/apa.py` remains a compatible entrypoint.

## Report workflow

Output language uses `zh` or `en`, with optional locale/script subtags such as
`zh-CN`, `zh-Hant`, or `en-GB`. Request another output language only after choosing
Chinese or English during planning; source-language search filters are independent.

The shared [prose rules](contracts/prose-rules.json) are the sole maintained
catalog for defensive wording, local grammar, and stock phrasing. Every rule
contains Chinese and English implementations, or an explicit language-specific
non-applicability reason. Update both entries together. The runtime reads this
JSON; it does not maintain a second phrase list. Use `audit-report-style REPORT`
to locate candidates. It returns a nonzero exit code when review is required,
without changing the report. `prepare-report` includes candidate diagnostics as
warnings so the existing semantic review can handle them in one batch.

Final publication requires each remaining candidate to have an exact, justified
`style_exceptions` entry in the version 1.1.0 content review. Entries contain
`finding_id`, `quote`, `evidence`, and `reason`. The reviewer checks factual or
grammatical necessity; a source citation alone does not justify filler. Final
validation rescans the text and rejects uncovered or stale entries. Changes to
rule data invalidate prior reviews through the semantic policy digest.

For a new task without an accepted plan, the Skill first asks the user to enter Plan Mode if needed. Planning settles the applicable search, evidence, OCR, classification, revision, and publication decisions. Once the user accepts the complete plan and the host allows execution, the coordinator continues through delivery and cleanup without stage-by-stage confirmations. An existing accepted plan can be resumed directly. Only essential decisions outside that scope need further user input.

Where the host permits planning writes, source downloads, extraction, page renders, and optional task-specific `instructions.md` notes share one system-temporary workspace. Otherwise preparation starts during execution without another planning round. The plan links any instruction file, relevant workers read it, and execution reuses prepared files. Publish retained sources and outputs before cleaning the workspace and completed run state. One writer owns each complete report.

Prepare all required evidence and original-page formula checks, then write the complete draft before repair or review. Reports assume only basic calculus, linear algebra, probability, and statistics. Specialist terms receive a plain explanation and a concrete analogy or small worked example on first use. The shared [report style](roles/report-style.md) removes filler and repeated explanations while retaining necessary reasoning, method coverage, equations, experiments, and evidence. Paper reports begin their core content with three one-sentence answers and related-work differences; overall inputs and outputs precede the flow graph and module table. Length follows the content; there is no word cap.

```text
ai-paper-analysis-runtime tools list
ai-paper-analysis-runtime tools doctor
ai-paper-analysis-runtime read-pdf paper.pdf --pages 1,3-5 --output pages.json
ai-paper-analysis-runtime render-pdf-pages paper.pdf temporary-pages --pages 3-5
ai-paper-analysis-runtime prepare-report candidate.md --report-kind paper --publication-path papers/report.md --evidence packet.json --coverage-matrix coverage.json
```

`prepare-report` repairs deterministic defects, generates reserved evidence footnotes from `--evidence` packets, and collects preflight failures without launching the browser. `--coverage-matrix` checks that each temporary coverage row cites its required evidence in the intended numbered section; `--review-issues` applies exact review patches, then checks consolidated obsolete literals and required evidence. `--dry-run` checks prepared bytes without changing the input. The final `audit-paper-report` or `audit-category-report` performs the workflow's only complete browser render. TB/LR direction, including a missing declaration direction, uses the deterministic layout estimator.

Completed concise source coverage can be reused from the project-local `.ai-paper-analysis/evidence-cache/` through `lookup-evidence-cache` and `record-evidence-cache`. Cache identity includes source bytes, evidence policy, source class, and coverage scope; original files, extracted/full text, and report prose are never copied into it.

One semantic review task covers the complete draft's accuracy and readability. Exact patches apply automatically. Only patch-null or failed residuals go once to a fresh central reviser with their affected evidence; it does not inherit the writer's source corpus or create a disposition artifact. The original reviewer then inspects the complete diff and cross-section dependencies once. Use temporary baselines, diffs, coverage matrices, and issue records instead of repeated corpus handoffs. Bind the final assessment with `record-content-review`, then run `audit-paper-report` or `audit-category-report` with `--content-review` and the eventual `--publication-path`. See command `--help` and the report contracts; a receipt attests to actual review, not programmatic proof of correctness.

Structure and content status are separate. An unreviewed legacy report is checked when needed; it is not silently deemed complete. Only currently reviewed complete reports qualify for comparison. A genuinely partial report may be published within its approval after every structural gate passes, with visible limitations. `record-state --content-review` retains the compact bound review for later reuse; changes to the report, reviewed sources or policy invalidate it. Reviews made before the current plain-language policy must be renewed when the report is next used. Detailed issues and evidence packets remain temporary. Revision promotion follows the initial plan's explicit authorization; otherwise the candidate is delivered.

## Repository layout

- `skills/` contains the independent Skill instruction packages and thin launchers.
- `roles/` contains canonical, selectively loaded workflow and role references.
- `src/ai_paper_analysis/` contains the shared deterministic tools and installer.
- `contracts/` and `templates/` contain public contracts and report skeletons.
- `plugins/ai-paper-analysis/` contains the generated complete plugin mirror.

Regenerate instruction copies with `python scripts/sync_materialized.py`; use `--check` to verify drift. Tool implementations are not copied into each Skill.

## Credentials

Environment variables take precedence. Supported adapters use `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `UNPAYWALL_EMAIL`, and the configured Scholar endpoint or token variables documented by the selected provider. Alternatively, pass an explicit SOPS file or place it at `<target-root>/.ai-paper-analysis/credentials.sops.yaml`.

```bash
sops <target-root>/.ai-paper-analysis/credentials.sops.yaml
```

Keep age private keys outside the project. If encrypted configuration is selected but either `sops` or `age` is missing, that credential source stops with a concise setup error. Decrypted values are kept in memory and are never written to run specifications or logs.

## Development checks

Run static checks with `python scripts/sync_materialized.py --check`,
`uv run --extra dev python scripts/validate_repository.py`, `uv run ruff check .`,
`uv run mypy src`, and `npm run lint:markdown`.

Create development test scripts, fixtures, logs, and results only in an allowed
system temporary directory, then remove them when finished. Do not commit test
suites or artifacts. The runtime report audit and rendering tools remain part
of the Skill and validate actual outputs during use.

## Safety, support, and access

The project never bypasses paywalls, CAPTCHAs, robots exclusions, rate limits, or access controls. PDFs, metadata, Markdown, and linked repositories are treated as untrusted input, and paper-linked code is inspected but not executed merely for interpretation. Do not commit real credentials, copyrighted paper corpora, or private laboratory artifacts. Report all defects and security concerns through the repository's public GitHub Issues page.

## License and acknowledgements

Original code and documentation are licensed under the MIT License. The interaction design was informed by the public structure of [Matt Pocock's skills repository](https://github.com/mattpocock/skills), and the evidence workflow was informed by the public [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills) and [ARS-Codex](https://github.com/Imbad0202/academic-research-skills-codex) repositories. No third-party Skill text, prompts, templates, paper reports, or code are copied into this repository. Local laboratory reports were consulted only as read-only design references; their text, private paths, and paper content are not included.
