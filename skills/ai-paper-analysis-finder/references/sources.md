# Source and Credential Rules

Read `references/contracts/provider-registry.json` for the finite built-in
registry. Show the applicable subset before execution and let the user add or
remove sources.

## Provider roles

- Discovery sources return candidates and metadata.
- Identity sources resolve DOI, arXiv, or another authoritative identifier.
- PDF resolvers locate legally accessible versions.
- Citation-graph sources help expand queries and later relationships.

A provider may serve only some roles. Crossref, OpenAlex, and Semantic Scholar
metadata do not by themselves prove that a linked PDF is the required paper.

## Special sources

- Google Scholar: use only a user-configured API endpoint and its documented
  quota. Never directly crawl Scholar search pages.
- Chinese and other commercial databases: require explicit authorization and
  a valid existing browser session or documented API. Never capture passwords
  in prompts or logs.
- Browser-only sources: use the available authorized browser capability. If no
  browser capability exists, mark the source unavailable and return to Plan
  Mode if its omission changes the approved coverage.

## Credentials

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
