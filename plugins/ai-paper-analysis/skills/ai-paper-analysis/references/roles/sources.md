# Source Acquisition and Validation Role

Read only the confirmed identity/provider batch and this role. Use the calling
Skill's shared CLI; a missing original never requires a sibling Skill. Ask no
user questions: return ambiguity, OCR needs, access problems, and scope changes
to the coordinator. The coordinator holds the global accepted-count/candidate
budget, per-host concurrency, and publication authority. Workers cannot expand
queries, exceed their assigned share, or race to publish duplicate identities.

Use `tools list`/`tools doctor` and command `--help` to discover the shared
provider, PDF, staging, and validation operations. `read-pdf` supplies source
text; `render-pdf-pages` supplies original-page images. Readability and tool
success alone never prove identity, relevance, or semantic verification.

Return a temporary result path and concise completion summary. The result must
include each assigned identity, normalized identifiers, version, legal source
chain, staged PDF path, structural and relevance outcomes, exact supporting
locators, unavailable/ambiguous cases, and exhausted provider bounds. Preserve
all assigned items, including failures. A full-text evidence packet is prepared
by [evidence-reader.md](evidence-reader.md) when substantive claims require it.

## 1. Build the approved run

The coordinator validates the confirmed run specification before any external
call and creates minimal hidden run state only after Plan Mode ends. Create one randomly named
system temporary directory for discovery records, downloads, detailed audits,
and any one-off scripts with the runtime's `create-temp` command. Do not copy
this operational workspace into `.ai-paper-analysis`, and run `cleanup-temp`
when its dependent work ends.

## 2. Discover and normalize

Search every confirmed provider within its role and bounds. Record the exact
query, pagination cursor, timestamp, and provider outcome.
Keep these operational records temporary unless the user requested a formal
audit output in a confirmed visible directory. Normalize DOI and arXiv IDs
before deduplication.

Group records by normalized DOI, arXiv base ID, other authoritative ID, then
high-confidence title/author/year similarity. Never merge a fuzzy group without
review. Preserve source records and version relations while making the current
run's decisions, but do not retain them as hidden run history by default.

Apply hard inclusion/exclusion rules first. Use title, abstract, and metadata
for early triage, but validate accepted candidates against available full text.
Automatically accept or reject only clear cases. Put all borderline cases in a
question-tool review batch.

## 3. Resolve the primary PDF

Prefer, in order:

1. A legally accessible version of record.
2. An author manuscript from an official or institutional source.
3. The latest preprint.

Store `same_work`, `is_version_of`, and source-preference evidence in temporary
decision notes. Publish only one primary PDF. Do not treat metadata APIs as PDF
hosts.

For a confirmed novelty-comparison set, resolve each named bibliography entry
as an exact identity target and obtain one verified legal original full-text
PDF per work. Do not substitute a survey, review, related work, or another paper
from the same research route. A grouped comparison is complete only when every
named work has a verified original, or the confirmed source set has been
exhausted and each unavailable work is reported explicitly.

For a confirmed Benchmark-source set, resolve every independently published
work that defines the named Benchmark, dataset, or environment as an exact
identity target. Obtain one verified legal original full-text PDF per work; do
not substitute a survey, nearby paper, website, or code documentation. The set
is complete only when every required original is verified, or the confirmed
source set has been exhausted and each unavailable work is reported explicitly.

## 4. Stage and validate

Download to the run's system temporary directory. Enforce the confirmed size,
timeout, retry, and provider rate limits. Respect `Retry-After` and stop a
provider rather than evading a block.

Validate:

- PDF header and non-HTML response.
- Parser readability, encryption state, page count, and file size.
- Title, authors, year, DOI, arXiv ID, and source-chain identity.
- Full-text relevance and every confirmed inclusion/exclusion rule.
- Duplicate identity and version relationship.

If the PDF is readable but none of the available signals can establish its
bibliographic identity, retain it only as a candidate with
`identity_status=inconclusive`. Return the identity to the coordinator for user confirmation before
marking it verified or using it for any comparison. Readability alone is never
identity evidence.

If text is sparse, return an OCR decision to the coordinator before OCR. OCR a temporary copy for text recovery and
retain the original PDF as the formal artifact. Formula verification always
uses rendered original pages.

## 5. Return validated files for coordinator publication

Workers return staged paths and decisions; only the coordinator performs the
publication operations below. Create the stable paper ID before the filename. Use the ID digest, not a raw DOI
or URL, in the filename. Publish with the runtime's atomic operation.

Publish ordinary corpus papers directly under `papers/`. When the confirmed
search is for novelty comparisons, Benchmark sources, or later related work for
`papers/<target-stem>.pdf`, instead publish each
verified external PDF as
`papers/<target-stem>_references/<external-paper-stem>.pdf`. Use the external
paper's normal artifact stem, keep only PDFs in this directory, and create an
independent verified copy for every target paper it supports.

Reuse an existing file only when its bibliographic identity, version, and PDF
structure match the confirmed work. If the same stable destination has
ambiguous identity or version evidence, pause for a Plan Mode decision. Never
add an automatic `-v2` suffix and never overwrite.

After atomic publication, use `record-state` to keep only stable path, run ID,
and publication status. At run completion, delete rejected files with
`cleanup-temp` and remove completed hidden run state with scoped `cleanup-run`. If
retained staging was explicitly approved, copy only the requested material to
the confirmed visible destination before cleanup. A failed provider does not
erase results from successful providers, and the completion summary must
disclose incomplete source coverage. Persist a detailed audit only when the
user requested it as a formal output outside `.ai-paper-analysis`.

## Provider and Credential Rules

Read [../contracts/provider-registry.json](../contracts/provider-registry.json) for the finite built-in
registry. Show the applicable subset before execution and let the user add or
remove sources.

### Provider roles

- Discovery sources return candidates and metadata.
- Identity sources resolve DOI, arXiv, or another authoritative identifier.
- PDF resolvers locate legally accessible versions.
- Citation-graph sources help expand queries and later relationships.

A provider may serve only some roles. Crossref, OpenAlex, and Semantic Scholar
metadata do not by themselves prove that a linked PDF is the required paper.

### Special sources

- Google Scholar: use only a user-configured API endpoint and its documented
  quota. Never directly crawl Scholar search pages.
- Chinese and other commercial databases: require explicit authorization and
  a valid existing browser session or documented API. Never capture passwords
  in prompts or logs.
- Browser-only sources: use the available authorized browser capability. If no
  browser capability exists, mark the source unavailable and return to Plan
  Mode if its omission changes the approved coverage.

### Credentials

Resolve credentials in this order:

1. Temporary environment value.
2. Existing authorized browser session.
3. SOPS+age encrypted project configuration supplied explicitly or found at
   `<target-root>/.ai-paper-analysis/credentials.sops.yaml`.

Record only the credential name and source. Never write the value. Keep age
private keys outside the project. Encrypted files are ignored by Git unless a
separate risk confirmation explicitly authorizes tracking ciphertext.

Environment values override encrypted configuration. When the SOPS source is
selected, require both `sops` and `age`; if either is missing, emit one concise
setup error and stop that source without falling through to another credential
location or exposing secret material.

Do not install SOPS, age, OCR software, or browser automation implicitly. If a
required dependency is absent, provide English setup guidance and stop the
affected provider or operation.
