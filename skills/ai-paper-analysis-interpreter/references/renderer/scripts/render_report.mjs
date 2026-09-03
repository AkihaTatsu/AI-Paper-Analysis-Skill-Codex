#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { delimiter, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { pathToFileURL } from "node:url";
import { fileURLToPath } from "node:url";

import katex from "katex";
import MarkdownIt from "markdown-it";
import footnote from "markdown-it-footnote";
import taskLists from "markdown-it-task-lists";
import texmath from "markdown-it-texmath";
import { liteAdaptor } from "@mathjax/src/js/adaptors/liteAdaptor.js";
import { RegisterHTMLHandler } from "@mathjax/src/js/handlers/html.js";
import { mathjax } from "@mathjax/src/js/mathjax.js";
import { SVG } from "@mathjax/src/js/output/svg.js";
import { TeX } from "@mathjax/src/js/input/tex.js";

const rendererRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const report = process.argv[2] ? resolve(process.argv[2]) : "";
if (!report || !existsSync(report)) {
  throw new Error("render_report.mjs requires one existing Markdown file");
}

function findExecutable(names) {
  for (const directory of (process.env.PATH || "").split(delimiter)) {
    for (const name of names) {
      const candidate = join(directory, name);
      if (existsSync(candidate)) return candidate;
      if (process.platform === "win32" && existsSync(`${candidate}.exe`)) return `${candidate}.exe`;
    }
  }
  return null;
}

const browserExecutable =
  process.env.PUPPETEER_EXECUTABLE_PATH ||
  findExecutable(["google-chrome", "chromium", "chromium-browser", "chrome", "msedge"]);
const childEnvironment = { ...process.env };
if (browserExecutable) childEnvironment.PUPPETEER_EXECUTABLE_PATH = browserExecutable;

const source = readFileSync(report, "utf8");
const markdown = new MarkdownIt({ html: false, linkify: false, typographer: false })
  .use(footnote)
  .use(taskLists, { enabled: true })
  .use(texmath, { engine: katex, delimiters: "dollars", katexOptions: { throwOnError: true } });
markdown.render(source);

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const mathjaxDocument = mathjax.document("", {
  InputJax: new TeX(),
  OutputJax: new SVG({ fontCache: "none" }),
});
const display = [...source.matchAll(/^\$\$\n([\s\S]*?)\n\$\$$/gm)].map((match) => match[1]);
const withoutDisplay = source.replace(/^\$\$\n[\s\S]*?\n\$\$$/gm, "");
const inline = [...withoutDisplay.matchAll(/(?<!\\)\$([^$\n]+)(?<!\\)\$/g)].map(
  (match) => match[1],
);
for (const expression of display) {
  katex.renderToString(expression, { throwOnError: true, displayMode: true });
  mathjaxDocument.convert(expression, { display: true });
}
for (const expression of inline) {
  katex.renderToString(expression, { throwOnError: true, displayMode: false });
  mathjaxDocument.convert(expression, { display: false });
}

const temporary = mkdtempSync(join(tmpdir(), "ai-paper-analysis-render-"));
try {
  const markdownlint = join(
    rendererRoot,
    "node_modules",
    "markdownlint-cli2",
    "markdownlint-cli2-bin.mjs",
  );
  execFileSync(
    process.execPath,
    [markdownlint, "--config", join(rendererRoot, ".markdownlint-cli2.yaml"), report],
    { env: childEnvironment, stdio: "pipe" },
  );

  const mermaidCli = join(
    rendererRoot,
    "node_modules",
    "@mermaid-js",
    "mermaid-cli",
    "src",
    "cli.js",
  );
  const diagrams = [...source.matchAll(/```mermaid\n([\s\S]*?)\n```/g)].map(
    (match) => match[1],
  );
  for (const [index, diagram] of diagrams.entries()) {
    const input = join(temporary, `diagram-${index}.mmd`);
    const output = join(temporary, `diagram-${index}.svg`);
    writeFileSync(input, diagram, "utf8");
    execFileSync(
      process.execPath,
      [mermaidCli, "--input", input, "--output", output, "--quiet"],
      { env: childEnvironment, stdio: "pipe" },
    );
  }

  const docs = join(temporary, "docs");
  const site = join(temporary, "site");
  const config = join(temporary, "mkdocs.yml");
  await import("node:fs/promises").then(({ mkdir }) => mkdir(docs));
  copyFileSync(report, join(docs, "index.md"));
  writeFileSync(
    config,
    [
      "site_name: AI Paper Analysis Report Audit",
      `docs_dir: ${JSON.stringify(docs)}`,
      `site_dir: ${JSON.stringify(site)}`,
      "strict: true",
      "validation:",
      "  links:",
      "    not_found: ignore",
      "    absolute_links: ignore",
      "    unrecognized_links: ignore",
      "theme:",
      "  name: material",
      "markdown_extensions:",
      "  - tables",
      "  - footnotes",
      "  - pymdownx.arithmatex:",
      "      generic: true",
      "  - pymdownx.tasklist:",
      "      custom_checkbox: true",
      "  - pymdownx.tilde",
      "  - pymdownx.superfences:",
      "      custom_fences:",
      "        - name: mermaid",
      "          class: mermaid",
      "          format: !!python/name:pymdownx.superfences.fence_code_format",
      "",
    ].join("\n"),
    "utf8",
  );
  const python = process.env.APA_PYTHON || findExecutable(["python3", "python"]);
  if (!python) throw new Error("Python is unavailable for the MkDocs strict build");
  execFileSync(python, ["-m", "mkdocs", "build", "--strict", "--config-file", config], {
    env: childEnvironment,
    stdio: "pipe",
  });
  const { default: puppeteer } = await import("puppeteer");
  const browser = await puppeteer.launch({
    headless: true,
    ...(browserExecutable ? { executablePath: browserExecutable } : {}),
  });
  try {
    const page = await browser.newPage();
    const browserErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") browserErrors.push(message.text());
    });
    page.on("pageerror", (error) => browserErrors.push(error.message));
    await page.goto(pathToFileURL(join(site, "index.html")).href, {
      waitUntil: "networkidle0",
    });
    if (browserErrors.length) {
      throw new Error(`browser console errors: ${browserErrors.join("; ")}`);
    }
  } finally {
    await browser.close();
  }
  process.stdout.write("Full Markdown rendering passed.\n");
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
