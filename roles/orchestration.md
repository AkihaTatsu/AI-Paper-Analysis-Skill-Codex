# Shared Role Dispatch

The calling Skill owns the run. Shared roles and `scripts/apa.py` supply its
prerequisites directly; never invoke a sibling Skill. The coordinator reads
[intake.md](intake.md), this routing file, and
[report-lifecycle.md](report-lifecycle.md) when a report is requested. Workers
read only their assigned role and its directly linked content references.

## Bounded assignments

| Work | Role | Output boundary |
| --- | --- | --- |
| Find or validate exact papers | [sources.md](sources.md) | Verified identities and staged originals |
| Read external originals | [evidence-reader.md](evidence-reader.md) | Complete concise coverage packets |
| Verify assigned equations | [formula-verifier.md](formula-verifier.md) | Original-page formula results |
| Write a whole paper report | [paper-writer.md](paper-writer.md) | One prepared seven-section candidate |
| Classify eligible papers | [classification.md](classification.md) | Proposed rows under the confirmed taxonomy |
| Establish relationships | [relationships.md](relationships.md) | Supported directed pair records |
| Write a category report | [category-writer.md](category-writer.md) | One prepared three-section candidate |
| Review a candidate | [semantic-review.md](semantic-review.md) | One issue set and one normal diff continuation |
| Revise automatic residuals | [report-reviser.md](report-reviser.md) | One bounded residual edit |

The paper report owner reads the target original and writes the report in the
same context. Do not insert a separate target-evidence worker and large handoff
on the normal path. External originals, independent formula batches, source
acquisition, and relationship pairs remain suitable bounded work.

## Authorization, model choice, and worker brief

Ask once per run before using subagents. After authorization, run independent
evidence work concurrently within available slots and shared provider limits.
No authorization means the same roles execute sequentially.

For the first paper draft, follow `execution_preferences.draft_model_policy`.
Under `fastest_suitable`, choose the fastest available subagent model whose
published description clearly supports the needed tools and context; do not
hard-code a model name. If suitability is uncertain, inherit the current model.
Use a high-capability reviewer for the one whole-candidate semantic review.
An explicit user model choice overrides these defaults. Do not call an external
model API.

Spawn fresh workers with `fork_turns="none"`. Give each worker only:

- run ID, its role path, calling Skill path, and approved slice of scope;
- exact source/input versions, required coverage objects, language or scenario
  when relevant, temporary output path, and read/write boundary;
- required return fields and a ban on further delegation, user questions,
  publication, or scope expansion.

Pass file paths instead of full papers, report bodies, role bundles, or chat
history. Shared filesystem access is not a sandbox, so boundaries remain explicit.
Return artifact path/version, coverage outcome, counts, and blockers. Reference
existing records rather than restating them in conversation. In an evidence
assignment, state that a successful `record-evidence-cache` result is the final
cache verification and must not be followed by another lookup.

## Coordinator responsibilities

Maintain the one approved run specification and one visible plan. Check that
role results cover each assigned source, formula, term, Benchmark, paper, and
relationship. Preserve source classes, conflicts, inaccessible evidence, and
limitations. A bare `passed` result or worker inference is insufficient.

Keep one whole-report writer and one normal semantic reviewer. The writer
completes automatic coverage preparation before review. Apply exact review
patches automatically; only when residuals remain, give one fresh reviser their
IDs and affected evidence. Then continue the same reviewer with the baseline
and diff. Add another
review only for a concrete unresolved question or user-requested scope. The
coordinator owns timing, publication, replacement, state, and cleanup.
