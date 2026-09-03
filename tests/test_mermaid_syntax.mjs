import assert from "node:assert/strict";

import { validateMermaidBlocks } from "../scripts/check_mermaid.mjs";

const audit = await validateMermaidBlocks([
  { line: 4, code: "flowchart TB\n  A --> B" },
  { line: 12, code: "flowchart TB\n  A -- B" },
]);

assert.equal(audit.parser, "mermaid");
assert.equal(audit.results[0].valid, true);
assert.equal(audit.results[1].valid, false);
assert.match(audit.results[1].message, /parse error/i);

console.log("Official Mermaid syntax parser checks passed.");
