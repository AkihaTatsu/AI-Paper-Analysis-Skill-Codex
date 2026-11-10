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

During planning, inspect only sources relevant to the request within the
host's permissions and the settled access and search bounds. Use temporary
files only when the host permits planning writes. During execution, validate
the accepted run specification before starting its source work. Reuse the one
workspace described in [../contracts/execution-plan.md](../contracts/execution-plan.md)
for discovery records, downloads, and audits. The coordinator creates formal run
state during execution and cleans this workspace after its consumers finish.

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
Accept or reject cases supported by full-text evidence and the planned criteria.
Return unresolved borderline cases to the coordinator; it asks only when a
necessary inclusion decision cannot be resolved within the plan.

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
`identity_status=inconclusive`. Return it to the coordinator for resolution;
never mark it verified or use it for comparison without identity evidence.
Apply the agreed exclusion or source-limitation policy when it remains unresolved.

If text is sparse, follow the planned OCR policy. Use already authorized OCR
on a temporary copy for text recovery and retain the original PDF as the formal
artifact. Ask only if needed OCR was not authorized. Formula verification always
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
ambiguous identity or version evidence, resolve it from evidence or return
that specific conflict to the coordinator. Never overwrite the ambiguous file
or invent an automatic `-v2` suffix; continue independent work.

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
  browser capability exists, mark the source unavailable and apply the planned
  limitation policy. Ask only if the missing coverage requires a new decision.

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
