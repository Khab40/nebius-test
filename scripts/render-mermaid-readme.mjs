#!/usr/bin/env node
/**
 * Render ALL Mermaid blocks in README.md to PNGs for GitHub Mobile fallback.
 *
 * - Finds ALL ```mermaid code blocks in README.md
 * - Renders each block to docs/diagrams/readme-mermaid-<NN>-<hash>.png
 * - Inserts a PNG image markdown line directly above each mermaid block
 * - Uses Puppeteer config with --no-sandbox for GitHub Actions runners
 *
 * Requirements:
 *  - Node 18+ (Actions uses Node 20)
 *  - Mermaid CLI is invoked via npx: @mermaid-js/mermaid-cli
 */

import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";

const README = "README.md";
const OUT_DIR = path.posix.join("docs", "diagrams");
const TMP_DIR = path.posix.join(".mermaid-tmp");
const PUPPETEER_CFG = "scripts/puppeteer-config.json";

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

// FNV-1a 32-bit hash -> hex string (stable across runs)
function fnv1a32(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16);
}

function runMmDc(input, output) {
  execFileSync(
    "npx",
    [
      "-y",
      "@mermaid-js/mermaid-cli",
      "-p",
      PUPPETEER_CFG,
      "-i",
      input,
      "-o",
      output,
      "-b",
      "transparent",
    ],
    { stdio: "inherit" }
  );
}

function main() {
  if (!fs.existsSync(README)) {
    console.error(`❌ ${README} not found`);
    process.exit(1);
  }
  if (!fs.existsSync(PUPPETEER_CFG)) {
    console.error(`❌ ${PUPPETEER_CFG} not found. Create it (see instructions).`);
    process.exit(1);
  }

  ensureDir(OUT_DIR);
  ensureDir(TMP_DIR);

  const readme = fs.readFileSync(README, "utf8");

  // Match all mermaid blocks: ```mermaid ... ```
  const mermaidRe = /```mermaid\s*\n([\s\S]*?)\n```/g;

  const blocks = [];
  let m;
  while ((m = mermaidRe.exec(readme)) !== null) {
    const body = (m[1] ?? "").trim();
    blocks.push({
      full: m[0],
      body,
    });
  }

  if (blocks.length === 0) {
    console.log("ℹ️ No mermaid blocks found in README.md — nothing to render.");
    return;
  }

  // Render
  const rendered = [];
  for (let i = 0; i < blocks.length; i++) {
    const body = blocks[i].body;
    const n = i + 1;
    const hash = fnv1a32(body);
    const base = `readme-mermaid-${String(n).padStart(2, "0")}-${hash}`;

    const mmdPath = path.posix.join(TMP_DIR, `${base}.mmd`);
    const pngPath = path.posix.join(OUT_DIR, `${base}.png`);

    fs.writeFileSync(mmdPath, body + "\n", "utf8");
    runMmDc(mmdPath, pngPath);

    rendered.push({ index: n, pngPath, blockFull: blocks[i].full });
  }

  // Patch README (insert image line above each block, avoid duplicates)
  let patched = readme;
  for (const r of rendered) {
    const imgLine = `![Diagram ${r.index}](${r.pngPath})`;
    const already = `${imgLine}\n\n${r.blockFull}`;
    if (patched.includes(already)) continue;

    patched = patched.replace(r.blockFull, `${imgLine}\n\n${r.blockFull}`);
  }

  if (patched !== readme) {
    fs.writeFileSync(README, patched, "utf8");
    console.log(`✅ Patched ${README} with PNG fallbacks`);
  } else {
    console.log(`ℹ️ ${README} already contained PNG fallbacks for all detected blocks`);
  }

  console.log(`✅ Rendered ${rendered.length} diagram(s) into ${OUT_DIR}`);
}

main();