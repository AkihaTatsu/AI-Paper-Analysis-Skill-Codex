#!/usr/bin/env node

import { createRequire } from "node:module";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

const require = createRequire(import.meta.url);
const mermaidVersion = require("mermaid/package.json").version;
const dom = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import("mermaid");

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

export async function validateMermaidBlocks(blocks) {
  const results = [];
  for (const block of blocks) {
    try {
      await mermaid.parse(block.code);
      results.push({ line: block.line, valid: true, message: "", parser_line: null });
    } catch (error) {
      results.push({
        line: block.line,
        valid: false,
        message: compactMessage(error),
        parser_line: parserLine(error),
      });
    }
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
  process.stdout.write(`${JSON.stringify(await validateMermaidBlocks(payload.blocks))}\n`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  await main();
}
