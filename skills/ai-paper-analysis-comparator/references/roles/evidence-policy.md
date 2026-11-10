# Semantic Evidence Policy

This is the shared semantic contract for writers and reviewers. Source readers
handle acquisition and full-text coverage; writers and reviewers use verified
packets and reopen exact original locators when a claim is disputed, high risk,
numerical, or formula dependent. Abstracts, metadata, snippets, generated
reports, and evidence packets are not citable substitutes for originals.

Separate these source classes in the report:

- **Target paper, supplement, and official code:** the paper and verified
  supplement support what the work says, assumes, derives, and reports. Pinned
  author-controlled code supports code behavior. If these disagree, show the
  conflict and block affected conclusions instead of choosing a winner.
- **Novelty comparison originals:** what earlier or concurrent work actually
  establishes. Use them for novelty comparisons, not the target paper's own
  characterization of competitors.
- **Benchmark originals:** dataset or benchmark provenance, design, metrics,
  and scope. Distinguish these facts from the target paper's results on them.
- **Relationship originals:** evidence for cross-paper dependency, extension,
  contrast, or chronology in category reports.

Every externally checkable factual claim needs a source marker tied to a precise
locator. Cite a coherent factual paragraph once at its end and reuse a locator
ID when the same bundle recurs. Keep inference visibly separate from source
statements. Formal evidence links may point only to target/supplement PDFs,
pinned official-code files, and verified external PDFs. Never cite run files,
extractions, renders, audits, packets, or drafts. Verify every report formula
visually on its original PDF page and preserve its conditions and symbol meanings.

The novelty-comparison set contains every named work the target uses to support
a substantive claim about a baseline's setting, assumptions, method, guarantee,
or difference, including every member of a grouped claim. Support the target
authors' novelty framing with the target and each baseline's own facts with that
baseline original; label a derived comparison and cite both sides. If a legal
original remains unavailable, use only the target's account and label it exactly
`target paper's characterization only; no independent full-text comparison`.

The Benchmark-source set contains each independently published original needed
to explain a dataset, environment, or Benchmark's provenance, construction,
native setting, or defining properties. Use the target/supplement for adopted
settings, results, and author conclusions. A result-table method name alone does
not add a source, and a Benchmark fully defined by the target needs no duplicate
external original. When its defining original remains unavailable, use only the
target and label the affected subsection exactly `target paper's
characterization only; Benchmark source not independently verified`.

Future-work papers require the initial plan's separate search budget and verified
full text. Keep all external claims visibly external. State missing, unreadable,
conflicting, or weak evidence as a limitation instead of completing a claim from
memory.
