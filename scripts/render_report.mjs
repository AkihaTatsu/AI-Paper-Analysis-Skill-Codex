#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import {
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
import "@mathjax/src/js/util/asyncLoad/esm.js";
import "@mathjax/src/js/input/tex/ams/AmsConfiguration.js";
import "@mathjax/src/js/input/tex/newcommand/NewcommandConfiguration.js";
import "@mathjax/src/js/input/tex/textmacros/TextMacrosConfiguration.js";
import "@mathjax/src/js/input/tex/configmacros/ConfigMacrosConfiguration.js";
import { renderMermaid } from "@mermaid-js/mermaid-cli";

const rendererRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));

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

function escapedAt(text, position) {
  let preceding = position;
  while (preceding && text[preceding - 1] === "\\") preceding--;
  return (position - preceding) % 2 === 1;
}

function inlineMathPipes(line) {
  // Match report_prepare's conservative single-dollar/code-span boundary.
  // This diagnoses a table split; it never rewrites the report or its TeX.
  const code = new Set();
  const ticks = [...line.matchAll(/`+/g)];
  for (let cursor = 0; cursor < ticks.length; cursor++) {
    const opening = ticks[cursor];
    if (escapedAt(line, opening.index)) continue;
    const closing = ticks.findIndex((tick, index) => index > cursor && tick[0] === opening[0]);
    if (closing < 0) continue;
    for (let i = opening.index; i < ticks[closing].index + ticks[closing][0].length; i++) code.add(i);
    cursor = closing;
  }
  const dollars = [...line.matchAll(/\$/g)].map((match) => match.index)
    .filter((position) => !code.has(position) && !escapedAt(line, position));
  if (dollars.length % 2) return null;
  const pipes = [];
  const escaped = [];
  for (let pair = 0; pair < dollars.length; pair += 2) {
    const opening = dollars[pair];
    const closing = dollars[pair + 1];
    const content = line.slice(opening + 1, closing);
    if (!content || /^\s|\s$/.test(content) || line[opening - 1] === "$" ||
        /[$\d]/.test(line[closing + 1] || "") ||
        [...code].some((position) => opening <= position && position <= closing)) return null;
    for (let i = opening + 1; i < closing; i++) {
      if (line[i] === "|") (line[i - 1] === "\\" ? escaped : pipes).push(i);
    }
  }
  if (/\]\(|\]\[|:\/\/|\[[^\]]*\]:/.test(line)) return null;
  return { unescaped: pipes, escaped };
}

function tableColumnCount(line) {
  const cells = line.trim().split(/(?<!\\)\|/);
  if (cells[0] === "") cells.shift();
  if (cells.at(-1) === "") cells.pop();
  return cells.length;
}

function validateTableMath(source, tokens) {
  const lines = source.split("\n");
  const broken = [];
  const ambiguous = [];
  for (const token of tokens) {
    if (token.type !== "table_open" || token.level !== 0 || !token.map) continue;
    const [start, end] = token.map;
    const columns = tableColumnCount(lines[start]);
    for (let index = start; index < end; index++) {
      if (index === start + 1) continue;
      const line = lines[index];
      const pipes = inlineMathPipes(line);
      if (!pipes) continue;
      // MarkdownIt removes a table pipe escape, but Python-Markdown's
      // arithmatex path preserves it as TeX's double bar. Require an explicit
      // TeX command instead of choosing the intended single/double bar here.
      if (pipes.escaped.length) {
        ambiguous.push(index + 1);
        continue;
      }
      const positions = new Set(pipes.unescaped);
      if (!positions.size) continue;
      const explicit = line.split("").map((char, i) => positions.has(i) ? "\\vert{}" : char).join("");
      if (tableColumnCount(explicit) === columns) broken.push(index + 1);
    }
  }
  const errors = [];
  if (broken.length) errors.push(`table.math-pipe-unescaped at line(s) ${broken.join(", ")}: ` +
    "unescaped pipes inside inline mathematics split table cells; run prepare-report before rendering");
  if (ambiguous.length) errors.push(`table.math-pipe-ambiguous at line(s) ${ambiguous.join(", ")}: ` +
    "escaped literal math pipes differ between Markdown renderers; specify \\vert{} for a single bar " +
    "or \\Vert{} for a double bar explicitly");
  return errors;
}

export function parseReport(input, { strict = true } = {}) {
  const source = input.replace(/\r\n?/g, "\n");
  const markdown = new MarkdownIt({ html: false, linkify: false, typographer: false })
    .use(footnote)
    .use(taskLists, { enabled: true })
    .use(texmath, { engine: katex, delimiters: "dollars", katexOptions: { throwOnError: strict } });
  const tokens = markdown.parse(source, {});
  const errors = validateTableMath(source, tokens);
  if (strict && errors.length) throw new Error(errors.join("; "));
  const diagrams = [];
  const display = [];
  const inline = [];
  function collect(items) {
    for (const token of items) {
      if (token.type === "fence" && token.info.trim().toLowerCase() === "mermaid") {
        diagrams.push(token.content);
      } else if (token.type.startsWith("math_block") || token.type === "math_inline_double") {
        display.push(token.content);
      } else if (token.type === "math_inline") {
        inline.push(token.content);
      }
      if (token.children) collect(token.children);
    }
  }
  collect(tokens);
  try {
    markdown.renderer.render(tokens, markdown.options, {});
  } catch (error) {
    errors.push(`Markdown rendering: ${error.message || error}`);
  }
  if (strict && errors.length) throw new Error(errors.join("; "));
  return { source, diagrams, display, inline, errors };
}

function compactError(error) {
  const detail = error?.stderr?.toString?.() || error?.stdout?.toString?.() || error?.message || error;
  return String(detail).replace(/\s+/g, " ").trim().slice(0, 1000);
}

function auditFailure(errors) {
  const failure = new Error(`report audit failed:\n${errors.map((item) => `- ${item}`).join("\n")}`);
  failure.diagnostics = errors;
  return failure;
}

export async function renderReport(report, overrides = {}) {
  if (!report || !existsSync(report)) {
    throw new Error("render_report.mjs requires one existing Markdown file");
  }
  const browserExecutable = process.env.PUPPETEER_EXECUTABLE_PATH;
  const childEnvironment = { ...process.env };
  const { source, diagrams, display, inline, errors: parsingErrors } = parseReport(
    readFileSync(report, "utf8"), { strict: false },
  );
  const errors = [...parsingErrors];
  const execute = overrides.execute || execFileSync;
  const adaptor = liteAdaptor();
  RegisterHTMLHandler(adaptor);
  const mathjaxDocument = mathjax.document("", {
    InputJax: new TeX({
      packages: ["base", "ams", "newcommand", "textmacros", "configmacros"],
      formatError(_jax, error) { throw error; },
    }),
    OutputJax: new SVG({ fontCache: "none" }),
    compileError(_document, _math, error) { throw error; },
    typesetError(_document, _math, error) { throw error; },
  });
  for (const [expressions, displayMode] of [[display, true], [inline, false]]) {
    for (const [index, expression] of expressions.entries()) {
      try {
        katex.renderToString(expression, { throwOnError: true, displayMode });
      } catch (error) {
        errors.push(
          `KaTeX ${displayMode ? "display" : "inline"} formula ${index + 1} (${expression}): ` +
          `${error.message || error}`,
        );
      }
      try {
        // MathJax 4 loads additional font data from its installed packages on
        // demand. Its ESM loader and promise API must both be used so retries
        // finish before validation proceeds to the next expression.
        const node = await mathjaxDocument.convertPromise(expression, { display: displayMode });
        const svg = adaptor.outerHTML(node);
        if (/data-mjx-error=|data-mml-node="merror"/.test(svg)) {
          throw new Error("MathJax returned an error node");
        }
      } catch (error) {
        errors.push(
          `MathJax ${displayMode ? "display" : "inline"} formula ${index + 1} (${expression}): ` +
          `${error.message || error}`,
        );
      }
    }
  }

  const temporary = mkdtempSync(join(tmpdir(), "ai-paper-analysis-render-"));
  try {
    const markdownlint = join(
      rendererRoot,
      "node_modules",
      "markdownlint-cli2",
      "markdownlint-cli2-bin.mjs",
    );
    const normalizedReport = join(temporary, "report.md");
    writeFileSync(normalizedReport, source, "utf8");
    try {
      execute(
        process.execPath,
        [markdownlint, "--config", join(rendererRoot, ".markdownlint-cli2.yaml"), normalizedReport],
        { env: childEnvironment, stdio: "pipe", cwd: temporary },
      );
    } catch (error) {
      errors.push(`markdownlint: ${compactError(error)}`);
    }

    const docs = join(temporary, "docs");
    const site = join(temporary, "site");
    const config = join(temporary, "mkdocs.yml");
    await import("node:fs/promises").then(({ mkdir }) => mkdir(docs));
    writeFileSync(join(docs, "index.md"), source, "utf8");
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
    if (!python) {
      errors.push("MkDocs: Python is unavailable for the strict build");
    } else {
      try {
        execute(python, ["-m", "mkdocs", "build", "--strict", "--config-file", config], {
          env: childEnvironment,
          stdio: "pipe",
        });
      } catch (error) {
        errors.push(`MkDocs: ${compactError(error)}`);
      }
    }
    if (errors.length) throw auditFailure(errors);
    const { default: puppeteer } = await import("puppeteer");
    const browser = await (overrides.launch || puppeteer.launch.bind(puppeteer))({
      headless: true,
      ...(browserExecutable ? { executablePath: browserExecutable } : {}),
    });
    try {
      for (const [index, diagram] of diagrams.entries()) {
        try {
          const { data } = await (overrides.renderMermaid || renderMermaid)(browser, diagram, "svg");
          writeFileSync(join(temporary, `diagram-${index}.svg`), data);
        } catch (error) {
          errors.push(`Mermaid diagram ${index + 1}: ${compactError(error)}`);
        }
      }
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
        errors.push(`browser console errors: ${browserErrors.join("; ")}`);
      }
    } finally {
      await browser.close();
    }
    if (errors.length) throw auditFailure(errors);
    return { valid: true, mermaid_count: diagrams.length, display_formula_count: display.length };
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  try {
    const result = await renderReport(process.argv[2] ? resolve(process.argv[2]) : "");
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({
      valid: false,
      errors: Array.isArray(error.diagnostics) ? error.diagnostics : [compactError(error)],
    })}\n`);
    process.exitCode = 1;
  }
}
