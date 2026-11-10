# Working rules

Make the smallest sufficient change for the user's goal and existing contracts.
Do not add speculative validation, retries, fallbacks, or compatibility layers.
Preserve existing safety boundaries and report errors directly.

Create all development tests, fixtures, logs, and results only in an allowed
system temporary directory. Remove them after use; do not commit test suites
or artifacts. Preserve runtime validation of actual Skill outputs.
