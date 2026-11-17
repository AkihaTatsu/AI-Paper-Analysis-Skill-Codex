#!/usr/bin/env node

import { createRequire } from "node:module";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";
import { renderMermaid } from "@mermaid-js/mermaid-cli";
import puppeteer from "puppeteer";

const require = createRequire(import.meta.url);
const mermaidVersion = require("mermaid/package.json").version;
const dom = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import("mermaid");

export function chooseDirection(sizes, current) {
  const portrait = (size) => size.width <= size.height;
  const a = sizes.TB;
  const b = sizes.LR;
  if (portrait(a) !== portrait(b)) return portrait(a) ? "TB" : "LR";
  const score = (size) => portrait(size)
    ? [size.width, size.height]
    : [size.width / size.height, size.width];
  const left = score(a);
  const right = score(b);
  for (let i = 0; i < left.length; i++) {
    if (left[i] !== right[i]) return left[i] < right[i] ? "TB" : "LR";
  }
  return current;
}

export function launchMermaidBrowser() {
  const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
  return puppeteer.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
}

export async function measureMermaidLayout(code, browser, render = renderMermaid) {
  mermaid.initialize({ startOnLoad: false });
  const diagram = await mermaid.mermaidAPI.getDiagramFromText(code);
  if (!diagram.type.startsWith("flowchart")) return { skipped: "Not a flowchart" };
  // Locate only the first statement after optional comments / Mermaid frontmatter.
  const declaration = /^(?:\s|%%[^\n]*(?:\n|$))*(?:---\r?\n[\s\S]*?\r?\n---\s*)?(?:\s|%%[^\n]*(?:\n|$))*(?:flowchart|graph)(?:[ \t]+(TB|TD|LR|BT|RL)\b)?/.exec(code);
  if (!declaration) throw new Error("Cannot locate the top-level flowchart declaration");
  const original = declaration[1] ?? null;
  if (original && !["TB", "TD", "LR"].includes(original)) {
    return { skipped: `Unsupported direction: ${original}` };
  }
  const offset = original ? declaration[0].length - original.length : declaration[0].length;
  const current = original === "TD" ? "TB" : original;
  const sizes = {};
  let nodeCount = 0;
  let hasSubgraph = false;
  for (const direction of ["TB", "LR"]) {
    const candidate = original
      ? code.slice(0, offset) + direction + code.slice(offset + original.length)
      : code.slice(0, offset) + ` ${direction}` + code.slice(offset);
    // Reset configuration between candidates and diagrams, including init directives.
    mermaid.initialize({ startOnLoad: false });
    const parsed = await mermaid.mermaidAPI.getDiagramFromText(candidate);
    const data = parsed.db.getData();
    nodeCount = data.nodes.filter((node) => !node.isGroup).length;
    hasSubgraph = data.nodes.some((node) => node.isGroup);
    const { data: svg } = await render(browser, candidate, "svg");
    const document = new dom.window.DOMParser().parseFromString(
      Buffer.from(svg).toString("utf8"), "image/svg+xml",
    );
    const root = document.documentElement;
    const bounds = root.getAttribute("viewBox")?.trim().split(/[\s,]+/).map(Number);
    if (root.localName !== "svg" || document.querySelector("parsererror") ||
        bounds?.length !== 4 || !bounds.every(Number.isFinite) ||
        bounds[2] <= 0 || bounds[3] <= 0) {
      throw new Error("Rendered Mermaid SVG has invalid dimensions");
    }
    sizes[direction] = { width: bounds[2], height: bounds[3] };
  }
  const recommended = nodeCount <= 1 ? (current ?? "TB") : chooseDirection(sizes, current ?? "TB");
  return { measured: true, current: original, recommended, sizes,
    node_count: nodeCount, has_subgraph: hasSubgraph, changed: current !== recommended,
    // JSON/JS offsets use UTF-16 code units; Python translates them before patching.
    direction_offset: offset, direction_length: original?.length ?? 0 };
}

function compactMessage(error) {
  const message = error instanceof Error ? error.message : String(error);
  return message.replace(/\s+/g, " ").trim().slice(0, 500);
}

function parserLine(error) {
  const located = error?.hash?.loc?.first_line;
  if (Number.isInteger(located) && located > 0) {
    return located;
  }
  const matched = compactMessage(error).match(/\bline\s+(\d+)\b/i);
  return matched ? Number.parseInt(matched[1], 10) : null;
}

export async function validateMermaidBlocks(blocks, { layout = false } = {}) {
  const results = [];
  const browser = layout && blocks.length ? await launchMermaidBrowser() : null;
  try {
    for (const block of blocks) {
      try {
        mermaid.initialize({ startOnLoad: false });
        await mermaid.parse(block.code);
        const record = { line: block.line, valid: true, message: "", parser_line: null };
        if (layout) {
          try {
            record.layout = await measureMermaidLayout(block.code, browser);
          } catch (error) {
            record.layout_error = compactMessage(error);
          }
        }
        results.push(record);
      } catch (error) {
        results.push({
          line: block.line,
          valid: false,
          message: compactMessage(error),
          parser_line: parserLine(error),
        });
      }
    }
  } finally {
    if (browser) await browser.close();
  }
  return { parser: "mermaid", version: mermaidVersion, results };
}

async function main() {
  let input = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    input += chunk;
  }
  const payload = JSON.parse(input);
  if (!Array.isArray(payload.blocks)) {
    throw new TypeError("Input must contain a blocks array");
  }
  process.stdout.write(`${JSON.stringify(await validateMermaidBlocks(payload.blocks, { layout: payload.layout === true }))}\n`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  await main();
}
