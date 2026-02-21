#!/usr/bin/env node
/**
 * Extract mermaid code blocks from README.md, render to PNGs, and patch README.md
 * to include PNG fallback before each mermaid block.
 *
 * Requirements:
 *  - @mermaid-js/mermaid-cli installed (mmdc)
 *  - Node 18+
 */

import fs from "fs";
import path from "path";
import { execFileSync } from "child_process";

const README = "README.md";
const OUT_DIR = path.posix.join("docs", "diagrams");
const TMP_DIR = path.posix.join(".mermaid-tmp");

if (!fs.existsSync(README)) {
  console.error(`❌ ${README} not found`);
  process.exit(1);
}

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.mkdirSync(TMP_DIR, { recursive: true });

const readme = fs.readFileSync(README, "utf8");

// Find ```mermaid ... ``` blocks
const mermaidBlockRegex = /```mermaid\s*\n([\s\S]*?)\n```/g;

let match;
let index = 0;
let patched = readme;

const hashes = [];
function stableSlug(s) {
  // Deterministic-ish slug based on content
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16);
}

const blocks = [];
while ((match = mermaidBlockRegex.exec(readme)) !== null) {
  blocks.push({
    full: match[0],
    body: match[1],
    startIndex: match.index,
  });
}

if (blocks.length === 0) {
  console.log("ℹ️ No mermaid blocks found in README.md. Nothing to do.");
  process.exit(0);
}

for (const b of blocks) {
  index += 1;
  const slug = stableSlug(b.body.trim());
  const baseName = `readme-diagram-${index}-${slug}`;
  const mmdPath = path.posix.join(TMP_DIR, `${baseName}.mmd`);
  const pngPath = path.posix.join(OUT_DIR, `${baseName}.png`);

  fs.writeFileSync(mmdPath, b.body.trim() + "\n", "utf8");

  // Render PNG (transparent background looks nice on both themes)
  // Using -b transparent; if you prefer white: -b white
  execFileSync(
+    "npx",
+    [
+      "-y",
+      "@mermaid-js/mermaid-cli",
+      "-p",
+      "scripts/puppeteer-config.json",
+      "-i",
+      input,
+      "-o",
+      output,
+      "-b",
+      "transparent"
+    ],
+    { stdio: "inherit" }
+  );

  hashes.push({ baseName, pngPath });

  // Patch README: insert an image line ABOVE the mermaid block,
  // but only if not already present just above it.
  // We look for an existing PNG fallback referencing this exact file.
  const imgLine = `![Diagram ${index}](${pngPath})`;

  // If the full block already has that image line directly above, skip patch insertion
  // We'll do a simple replacement: if "\n![...](png)\n\n```mermaid" already exists.
  const expected = `${imgLine}\n\n${b.full}`;
  if (!patched.includes(expected)) {
    patched = patched.replace(b.full, `${imgLine}\n\n${b.full}`);
  }
}

if (patched !== readme) {
  fs.writeFileSync(README, patched, "utf8");
  console.log(`✅ Patched ${README} with PNG fallbacks`);
} else {
  console.log(`ℹ️ ${README} already contains PNG fallbacks for detected blocks`);
}

console.log(`✅ Rendered ${hashes.length} diagram(s) into ${OUT_DIR}`);