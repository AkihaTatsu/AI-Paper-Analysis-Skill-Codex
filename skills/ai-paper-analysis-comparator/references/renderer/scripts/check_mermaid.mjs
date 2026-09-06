#!/usr/bin/env node

import { createRequire } from "node:module";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";
import { graphlib } from "dagre-d3-es";
import { layout as dagreLayout } from "dagre-d3-es/src/dagre/index.js";

const require = createRequire(import.meta.url);
const mermaidVersion = require("mermaid/package.json").version;
const dom = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import("mermaid");

// Pure layout estimates: no browser, canvas, SVG measurement, or font downloads.
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

function textSize(label, fontSize, wrappingWidth) {
  const plain = String(label ?? "");
  if (/<[^>]*>|\$/.test(plain)) {
    throw new Error("Layout estimation does not support HTML or mathematical labels");
  }
  let width = 0;
  let lineWidth = 0;
  let lines = 1;
  for (const character of plain) {
    if (character === "\n") {
      width = Math.max(width, lineWidth);
      lineWidth = 0;
      lines++;
      continue;
    }
    const units = /\p{Mark}|\u200d|\ufe0f/u.test(character) ? 0
      : /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Extended_Pictographic}\uff01-\uff60]/u.test(character) ? 1 : 0.5;
    const advance = fontSize * units;
    if (wrappingWidth && lineWidth && lineWidth + advance > wrappingWidth) {
      width = Math.max(width, lineWidth);
      lineWidth = 0;
      lines++;
    }
    lineWidth += advance;
  }
  return { width: Math.max(width, lineWidth, fontSize / 2), height: lines * fontSize * 1.5 };
}

function nodeSize(node, config) {
  const fontSize = Number.parseFloat(config.themeVariables.fontSize ?? 16);
  if (!(fontSize > 0)) throw new Error("Cannot estimate the configured font size");
  const wrapping = node.labelType === "markdown" && config.markdownAutoWrap !== false
    ? config.flowchart.wrappingWidth : 0;
  const size = textSize(node.label, fontSize, wrapping);
  const padding = node.padding ?? config.flowchart.padding;
  size.width += 2 * padding;
  size.height += 2 * padding;
  switch (node.shape) {
    case "rect": case "squareRect": case "rounded": case "round":
      break;
    case "circle": case "doublecircle":
      size.width = size.height = Math.max(size.width, size.height)
        + (node.shape === "doublecircle" ? 10 : 0);
      break;
    case "diamond":
      size.width = size.height = size.width + size.height;
      break;
    case "stadium": case "hexagon": case "lean-l": case "lean-r":
    case "trapezoid": case "inv-trapezoid": case "subroutine":
      size.width += size.height / 2;
      break;
    case "cylinder":
      size.height += size.width / 4;
      break;
    default:
      throw new Error(`Cannot estimate node shape: ${node.shape}`);
  }
  return size;
}

function estimateData(data, direction) {
  const config = data.config;
  const flow = config.flowchart;
  if (!['dagre-wrapper', 'dagre-d3'].includes(flow.defaultRenderer)
      || (config.layout && config.layout !== "dagre")) {
    throw new Error("Layout estimation supports only Dagre flowcharts");
  }
  const styleText = JSON.stringify(data.nodes.map((node) => [
    node.cssStyles, node.cssCompiledStyles, node.labelStyle,
  ]).concat(data.edges.map((edge) => [edge.style, edge.cssCompiledStyles, edge.labelStyle])));
  if (config.themeCSS || /font|width|height|padding|white-space|letter-spacing/i.test(styleText)) {
    throw new Error("Cannot estimate custom CSS affecting diagram dimensions");
  }
  const nodes = new Map(data.nodes.map((node) => [node.id, node]));
  const descendants = (id) => {
    const found = new Set();
    const visit = (parent) => {
      for (const node of nodes.values()) {
        if (node.parentId === parent) {
          found.add(node.id);
          visit(node.id);
        }
      }
    };
    visit(id);
    return found;
  };
  const fontSize = Number.parseFloat(config.themeVariables.fontSize ?? 16);
  const measure = (members, edges, rankdir) => {
    const g = new graphlib.Graph({ multigraph: true, compound: true });
    g.setGraph({ rankdir, nodesep: flow.nodeSpacing, ranksep: flow.rankSpacing,
      marginx: flow.diagramPadding, marginy: flow.diagramPadding });
    g.setDefaultEdgeLabel(() => ({}));
    const collapsed = new Set();
    const included = new Set(members.map((node) => node.id));
    const sizes = new Map();
    for (const node of members) {
      if (!node.isGroup || collapsed.has(node.id)) continue;
      const children = descendants(node.id);
      const external = edges.some((edge) => children.has(edge.start) !== children.has(edge.end));
      if (!external && children.size) {
        const childMembers = members.filter((child) => children.has(child.id));
        const childEdges = edges.filter((edge) => children.has(edge.start) && children.has(edge.end));
        // Mermaid extracts disconnected clusters and defaults their direction
        // perpendicular to the parent unless an explicit/inherited dir is set.
        const childDir = node.dir || (rankdir === "TB" ? "LR" : "TB");
        const size = measure(childMembers, childEdges, childDir);
        const title = textSize(node.label, fontSize, 0);
        const margin = flow.subGraphTitleMargin;
        sizes.set(node.id, {
          width: Math.max(size.width, title.width) + 2 * node.padding,
          height: size.height + title.height + 2 * node.padding + margin.top + margin.bottom,
        });
        children.forEach((id) => collapsed.add(id));
      }
    }
    for (const node of members) {
      if (collapsed.has(node.id)) continue;
      g.setNode(node.id, sizes.get(node.id) ?? nodeSize(node, config));
    }
    for (const node of members) {
      if (!collapsed.has(node.id) && included.has(node.parentId) && !collapsed.has(node.parentId)) {
        g.setParent(node.id, node.parentId);
      }
    }
    for (const edge of edges) {
      if (collapsed.has(edge.start) || collapsed.has(edge.end)) continue;
      const label = edge.label ? textSize(edge.label, fontSize,
        edge.labelType === "markdown" ? flow.wrappingWidth : 0) : { width: 0, height: 0 };
      // Dagre cannot connect compound containers directly. Fail explicitly
      // rather than silently dropping these edges or changing their endpoints.
      if (g.children(edge.start)?.length || g.children(edge.end)?.length) {
        throw new Error("Cannot estimate edges attached to externally connected subgraph containers");
      }
      g.setEdge(edge.start, edge.end, { ...label, minlen: edge.minlen ?? 1, labelpos: "c" }, edge.id);
    }
    if (!g.nodeCount()) return { width: 0, height: 0 };
    dagreLayout(g);
    // Compound-node titles are not measured by Dagre; include them in bounds.
    let extraHeight = 0;
    let extraWidth = 0;
    for (const node of members) {
      if (!collapsed.has(node.id) && g.children(node.id)?.length) {
        const title = textSize(node.label, fontSize, 0);
        extraWidth = Math.max(extraWidth, title.width + 2 * node.padding - g.node(node.id).width);
        extraHeight += title.height + flow.subGraphTitleMargin.top + flow.subGraphTitleMargin.bottom;
      }
    }
    const size = { width: g.graph().width + extraWidth, height: g.graph().height + extraHeight };
    if (!Object.values(size).every((value) => Number.isFinite(value) && value > 0)) {
      throw new Error("Layout estimation produced invalid dimensions");
    }
    return size;
  };
  return measure(data.nodes, data.edges, direction);
}

async function estimateLayout(code) {
  const diagram = await mermaid.mermaidAPI.getDiagramFromText(code);
  if (!diagram.type.startsWith("flowchart")) return { skipped: "Not a flowchart" };
  // Locate only the first statement after optional comments / Mermaid frontmatter.
  const declaration = /^(?:\s|%%[^\n]*(?:\n|$))*(?:---\r?\n[\s\S]*?\r?\n---\s*)?(?:\s|%%[^\n]*(?:\n|$))*(?:flowchart|graph)[ \t]+(TB|TD|LR|BT|RL)\b/.exec(code);
  if (!declaration) throw new Error("Cannot locate the top-level flowchart direction");
  const original = declaration[1];
  if (!["TB", "TD", "LR"].includes(original)) return { skipped: `Unsupported direction: ${original}` };
  const offset = declaration[0].length - original.length;
  const current = original === "TD" ? "TB" : original;
  const sizes = {};
  let nodeCount = 0;
  let hasSubgraph = false;
  for (const direction of ["TB", "LR"]) {
    const candidate = code.slice(0, offset) + direction + code.slice(offset + original.length);
    // Reset configuration between candidates and diagrams, including init directives.
    mermaid.initialize({ startOnLoad: false });
    const parsed = await mermaid.mermaidAPI.getDiagramFromText(candidate);
    const data = parsed.db.getData();
    nodeCount = data.nodes.filter((node) => !node.isGroup).length;
    hasSubgraph = data.nodes.some((node) => node.isGroup);
    sizes[direction] = estimateData(data, direction);
  }
  const recommended = nodeCount <= 1 ? current : chooseDirection(sizes, current);
  return { estimated: true, current: original, recommended, sizes,
    node_count: nodeCount, has_subgraph: hasSubgraph, changed: current !== recommended,
    // JSON/JS offsets use UTF-16 code units; Python translates them before patching.
    direction_offset: offset };
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
  for (const block of blocks) {
    try {
      mermaid.initialize({ startOnLoad: false });
      await mermaid.parse(block.code);
      const record = { line: block.line, valid: true, message: "", parser_line: null };
      if (layout) {
        try {
          record.layout = await estimateLayout(block.code);
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
