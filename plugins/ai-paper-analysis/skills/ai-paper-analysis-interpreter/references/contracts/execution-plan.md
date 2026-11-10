# Execution Plan and Progress

After the current work's scope is confirmed and execution is permitted by the
active collaboration mode, create a visible plan before its first execution
action. Use Codex's native `update_plan` tool when it is available. This is an
execution checklist, separate from the proposal discussed in Plan Mode; it
does not switch modes or grant permission to acquire sources or publish files.

## Create and share one plan

- Write short, verifiable stages in the user's requested language. Usually
  three to six stages suffice; adapt to the actual task rather than padding
  small tasks or listing every command. Include required verification,
  delivery, and cleanup within the authorized scope.
- With two-stage authorization, the first plan covers only approved target
  acquisition and source inspection. After full-execution approval, extend
  that same plan with the approved downstream work and retain completed steps.
- The calling Skill's coordinator owns one plan across all shared roles and
  prerequisites. Workers return progress to that coordinator rather than
  creating separate checklists. A directly invoked entrypoint creates the plan
  when this task has none. On resumption, continue the existing plan and preserve
  verified progress. The coordinator need not read every role's instructions
  or source corpus to maintain the plan.

## Maintain accurate status

Call `update_plan` with the full current `plan` list, using `step` and `status`
for each item and an optional `explanation` for changes. Use only `pending`,
`in_progress`, and `completed`; at most one item may be `in_progress`. Mark
the first stage in progress only when starting it and leave later stages
pending.

Update the plan at meaningful stage transitions, after a necessary revision
to the remaining work, and before the final response. Mark a stage completed
only when its outcome and required checks are satisfied. Do not mark a failed
audit, unfinished report, or publication awaiting approval as completed.

When waiting for clarification, approval, or an external prerequisite, explain
the dependency and leave unfinished stages pending. Resume the relevant stage
when work restarts. For a changed scope, obtain any confirmation required by
the existing workflow before adding execution work; explain removed or
cancelled steps instead of labeling them completed. Before handing back,
reconcile the checklist with actual outcomes and state any unfinished work.

## Tool unavailable

If `update_plan` is not exposed or cannot be used in the current session,
briefly say so, then display and maintain a Markdown table with Step and Status
columns, localized to the user's language. Apply the same timing, ownership,
and status rules. Continue authorized work without asking for an extra
confirmation solely because the plan tool is missing. Never claim that a
text table was created through the native tool or invoke an invented tool.

The checklist remains in the conversation. Do not create a permanent plan
file, add a CLI command, install a tool provider, or change the approved
run specification to supply it. Existing confirmation, source, publication,
and cleanup gates remain in force.
