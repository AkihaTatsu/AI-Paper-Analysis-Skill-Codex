import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { chooseDirection, validateMermaidBlocks } from "../scripts/check_mermaid.mjs";

async function estimate(code) {
  const { results: [record] } = await validateMermaidBlocks([{ line: 3, code }], { layout: true });
  assert.equal(record.valid, true, record.message);
  assert.equal(record.layout_error, undefined);
  return record.layout;
}

const pair = (tw, th, lw, lh) => ({ TB: { width: tw, height: th }, LR: { width: lw, height: lh } });
assert.equal(chooseDirection(pair(300, 100, 100, 300), "TB"), "LR");
assert.equal(chooseDirection(pair(80, 300, 100, 150), "LR"), "TB");
assert.equal(chooseDirection(pair(100, 300, 100, 150), "TB"), "LR");
assert.equal(chooseDirection(pair(400, 100, 600, 300), "TB"), "LR");
assert.equal(chooseDirection(pair(400, 200, 200, 100), "TB"), "LR");
assert.equal(chooseDirection(pair(100, 100, 100, 100), "LR"), "LR");
assert.equal(chooseDirection(pair(100, 100, 100, 100), "TB"), "TB");

const fixture = readFileSync(new URL("./fixtures/mermaid-disconnected.md", import.meta.url), "utf8");
const code = fixture.split("```mermaid\n")[1].split("```")[0];
const example = await estimate(code);
assert.equal(example.node_count, 17);
assert.equal(example.recommended, "LR");
assert.ok(example.sizes.TB.width > example.sizes.TB.height);
assert.ok(example.sizes.LR.width < example.sizes.LR.height);
assert.equal((await estimate(code.replace("flowchart TB", "flowchart LR"))).changed, false);
const implicit = await estimate("flowchart\n A --> B --> C");
assert.equal(implicit.current, null);
assert.equal(implicit.changed, true);
assert.equal(implicit.direction_length, 0);
assert.match(implicit.recommended, /^(TB|LR)$/);

const chain = await estimate("flowchart LR\n A --> B --> C --> D --> E --> F --> G");
assert.equal(chain.node_count, 7);
assert.equal(chain.recommended, "TB");
for (const direction of ["TB", "TD", "LR"]) {
  assert.equal((await estimate(`flowchart ${direction}\n A[Single]`)).changed, false);
  assert.equal((await estimate(`flowchart ${direction}`)).changed, false);
}
const short = await estimate("flowchart TB\n A[A] --> B[B]");
const long = await estimate("flowchart TB\n A[A much longer label] -->|a long edge label| B[B]");
assert.ok(long.sizes.LR.width > short.sizes.LR.width);
const cjk = await estimate("flowchart TB\n A[\u4e2d\u6587] --> B[B]");
const latin = await estimate("flowchart TB\n A[ab] --> B[B]");
assert.ok(cjk.sizes.TB.width > latin.sizes.TB.width);
const wrap = await estimate('flowchart TB\n A["`' + 'label '.repeat(30) + '`"] --> B');
assert.ok(wrap.sizes.TB.height > long.sizes.TB.height);

for (const graph of [
  "A --> B --> C --> A",
  "A --> A",
  "A --> B & C & D\n B --> E\n C --> E\n D --> E",
  "A((A)) --> B{B} --> C([C]) --> D[(D)] --> E[[E]]",
  "subgraph Outer\n subgraph Inner\n direction LR\n A --> B\n end\n C --> D\n end\n E --> F",
  "subgraph S[Module]\n direction LR\n A --> B\n end\n B --> C",
]) {
  const result = await estimate(`flowchart TB\n${graph}`);
  for (const size of Object.values(result.sizes)) {
    assert.ok(Number.isFinite(size.width) && size.width > 0);
    assert.ok(Number.isFinite(size.height) && size.height > 0);
  }
}
const explicit = "flowchart TB\n subgraph S[Module]\n direction LR\n A --> B\n end";
const explicitResult = await estimate(explicit);
assert.deepEqual(explicitResult.sizes.TB, explicitResult.sizes.LR);
const external = "flowchart TB\n subgraph S\n direction LR\n A --> B\n end\n B --> C";
assert.deepEqual((await estimate(external)).sizes,
  (await estimate(external.replace("direction LR", "direction TB"))).sizes);
const comment = "%% \ud83d\udd0e flowchart LR\n\nflowchart TD; A --> B";
const offset = (await estimate(comment)).direction_offset;
assert.equal(comment.slice(offset, offset + 2), "TD");
assert.deepEqual((await estimate("---\nconfig:\n  flowchart:\n    nodeSpacing: 100\n---\n" + code)).recommended, "LR");

for (const unsupported of [
  "---\nconfig:\n  layout: elk\n---\nflowchart TB\n A --> B",
  "flowchart TB\n A --> B\n style A font-size:40px",
  "flowchart TB\n A@{shape: cloud, label: Cloud} --> B",
]) {
  const audit = await validateMermaidBlocks([{ line: 1, code: unsupported }], { layout: true });
  assert.equal(audit.results[0].valid, true);
  assert.ok(audit.results[0].layout_error);
}
const mixed = await validateMermaidBlocks([
  { line: 1, code: "sequenceDiagram\n A->>B: Hello" },
  { line: 5, code: "flowchart TB\n A -- B" },
  { line: 9, code },
], { layout: true });
assert.equal(mixed.results[0].layout.skipped, "Not a flowchart");
assert.equal(mixed.results[1].valid, false);
assert.equal(mixed.results[2].layout.recommended, "LR");
assert.deepEqual((await estimate(code)).sizes, example.sizes);
console.log("Pure Mermaid layout checks passed (no browser required).");
