# Execution Plan and Temporary Instructions

The coordinator maintains one plan from planning through delivery and cleanup.
Follow [../roles/intake.md](../roles/intake.md) for startup, confirmation, and
scope decisions. A plan does not switch the host's collaboration mode.

## Progress

Use `update_plan` when available, with short verifiable steps and the statuses
`pending`, `in_progress`, and `completed`; at most one step is in progress.
Otherwise maintain a concise Step/Status table in the conversation. Resume the
existing checklist rather than creating one for each role or workflow stage.

Update progress at meaningful transitions and before handing back. Complete a
step only when its output and required checks pass. Explain genuine blockers,
continue independent work, and leave unfinished steps pending. A checklist
update is not a request for the user to authorize the next step.

## One temporary workspace

Use `create-temp` for one workspace under an allowed system temporary directory.
Planning downloads, extraction, renders, and notes are permitted only when the
host's mode and filesystem rules allow them. Otherwise defer their creation to
execution. Keep the workspace across planning and execution and reuse its files.
Create formal project run state with `init-run` only during authorized execution.

When needed, write `instructions.md` in that workspace for task-specific
constraints and decisions that would crowd the visible plan. Link its absolute
path from the plan and pass it to relevant workers. Keep it consistent with the
accepted scope; it neither adds authorization nor replaces the shared content
rules. Do not create it for a task whose plan already contains everything needed.

Publish requested originals and final outputs at their intended destinations,
using stable source paths for report links and content reviews. After all
consumers finish, use `cleanup-temp` to remove this task's entire workspace,
including notes, downloads, extraction, renders, and review intermediates. Also
remove completed hidden run state with `cleanup-run`. Apply the same cleanup
when the task is explicitly abandoned; keep files needed by an ongoing task.
Preserve formal outputs, existing user files, approved retained material, and
the existing reusable evidence cache. Never clean a whole temporary root or
another task's workspace.
