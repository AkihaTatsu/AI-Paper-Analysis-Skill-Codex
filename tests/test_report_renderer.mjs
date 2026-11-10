import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { parseReport, renderReport } from "../scripts/render_report.mjs";

const source = [
  "# Report", "", "> ~~~~mermaid", "> flowchart TB", "> A --> B", "> ~~~~", "",
  "```mermaid", "flowchart LR", "B --> C", "```", "",
  "> $$", "> x + y", "> $$", "", "`$not-math$` and $z$.", "",
  // Multi-letter double-struck glyphs need MathJax 4's dynamic font modules.
  // Keep actual math conversion enabled while browser/process work is stubbed.
  "$$", String.raw`\mathbb{abc}+\mathbb{xyz}=\operatorname{rank}(A)`, "$$", "",
  String.raw`Greek identifiers $α+β$ and $\mathbb{def}_{\text{干预}}$.`, "",
  "```text", "$also-not-math$", "```", "",
].join("\n");
for (const newline of ["\n", "\r\n"]) {
  const parsed = parseReport(source.replaceAll("\n", newline));
  assert.equal(parsed.diagrams.length, 2);
  assert.equal(parsed.display.length, 2);
  assert.deepEqual(parsed.inline, ["z", "α+β", String.raw`\mathbb{def}_{\text{干预}}`]);
  assert.equal(parsed.source.includes("\r"), false);
}

const tableHeader = "| Symbol | Meaning |\n| --- | --- |\n";
for (const expression of [String.raw`C\in\mathbb R^{|S|}`, String.raw`|\mathcal{TS}(G_\theta)|`, String.raw`|G_\theta|`]) {
  const row = `| $${expression}$、$C$ | 说明 |\n`;
  assert.throws(() => parseReport(tableHeader + row), /table.math-pipe-unescaped.*3/);
  const escaped = expression.replaceAll("|", String.raw`\|`);
  assert.throws(() => parseReport(tableHeader + `| $${escaped}$、$C$ | 说明 |\n`),
    /table.math-pipe-ambiguous.*3/);
  const explicit = expression.replaceAll("|", String.raw`\vert{}`);
  assert.deepEqual(parseReport(tableHeader + `| $${explicit}$、$C$ | 说明 |\n`).inline, [explicit, "C"]);
}
assert.deepEqual(parseReport(tableHeader + "| `$x\\|y$` | 中文 |\n").inline, []);
assert.deepEqual(parseReport(tableHeader + String.raw`| \$x\|y\$ | 中文 |` + "\n").inline, []);
assert.deepEqual(parseReport("```text\n" + tableHeader + "| $|x|$ | 文本 |\n```\n").inline, []);
assert.deepEqual(parseReport(String.raw`Outside a table $|x|$、$y$ and $\text{中文}$.`).inline,
  ["|x|", "y", String.raw`\text{中文}`]);
assert.deepEqual(parseReport(String.raw`Outside a table $\|x\|$ and $\Vert x\Vert$.`).inline,
  [String.raw`\|x\|`, String.raw`\Vert x\Vert`]);
assert.deepEqual(parseReport(tableHeader + String.raw`| $\Vert{}x\Vert{}$ | 中文 |` + "\n").inline,
  [String.raw`\Vert{}x\Vert{}`]);

const workspace = mkdtempSync(join(tmpdir(), "apa-含 空格-"));
const report = join(workspace, "报告.md");
writeFileSync(report, source);
let launches = 0;
let closed = 0;
let rendered = 0;
let temporary;
const browser = {
  async newPage() { return { on() {}, async goto() {} }; },
  async close() { closed++; },
};
const overrides = {
  execute(executable, args) {
    if (args.includes("--config")) temporary = args.at(-1);
  },
  async launch() { launches++; return browser; },
  async renderMermaid(instance) {
    assert.equal(instance, browser);
    rendered++;
    return { data: new Uint8Array([60, 115, 118, 103, 47, 62]) };
  },
};
try {
  const result = await renderReport(report, overrides);
  assert.equal(result.valid, true);
  assert.equal(result.mermaid_count, 2);
  assert.equal(launches, 1);
  assert.equal(closed, 1);
  assert.equal(rendered, 2);
  assert.equal(existsSync(temporary), false);
  await assert.rejects(renderReport(report, {
    ...overrides,
    async renderMermaid() { throw new Error("diagram failure"); },
  }), /diagram failure/);
  assert.equal(closed, 2);
  assert.equal(existsSync(temporary), false);

  const launchesBeforeInvalid = launches;
  writeFileSync(report, "# Invalid math\n\n$$\n\\frac{1}{\n$$\n");
  await assert.rejects(renderReport(report, overrides), /KaTeX parse error/);
  // KaTeX accepts its own logo command. MathJax rejects it, normally by
  // returning merror rather than throwing: passing the first engine is not
  // sufficient for this cross-renderer gate.
  writeFileSync(report, "# MathJax error\n\n$$\n\\KaTeX\n$$\n");
  await assert.rejects(renderReport(report, overrides), /Undefined control sequence.*KaTeX/);
  assert.equal(launches, launchesBeforeInvalid);

  let preflightLaunches = 0;
  writeFileSync(report, "# Several failures\n\n$$\n\\frac{1}{\n$$\n\n$\\KaTeX$\n");
  await assert.rejects(renderReport(report, {
    ...overrides,
    execute(executable, args) {
      if (args.some((value) => value.includes("markdownlint-cli2"))) {
        throw new Error("lint failure");
      }
      throw new Error("mkdocs failure");
    },
    async launch() { preflightLaunches++; return browser; },
  }), (error) => {
    assert.ok(error.diagnostics.length >= 4);
    assert.match(error.message, /KaTeX/);
    assert.match(error.message, /MathJax/);
    assert.match(error.message, /markdownlint/);
    assert.match(error.message, /MkDocs/);
    return true;
  });
  assert.equal(preflightLaunches, 0);
} finally {
  rmSync(workspace, { recursive: true, force: true });
}
console.log("Report token extraction, shared browser, and cleanup passed.");
