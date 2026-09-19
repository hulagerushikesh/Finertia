// Bundle budget. Fails the build when the shipped JavaScript grows past the
// limits in bundle-budget.json.
//
// Two numbers, both gzip bytes, because that is what a phone downloads:
//   entry  — the script index.html loads synchronously plus every chunk it
//            modulepreloads. This is the landing page's cost before a single
//            byte of app code runs; the 13 Sep redesign took it from 169 to
//            196 kB gz and nobody noticed until a sourcemap was read by hand.
//   total  — every .js under dist/assets. Catches a lazy route swallowing a
//            library it should not have.
//
// Limits are set ~10% above the measurement on the day they were written.
// Growing past one is allowed — raise the number in bundle-budget.json in the
// same PR and say why in the description. That sentence is the whole point.
//
// Usage: node scripts/check-bundle.mjs   (after `vite build`; no dependencies)

import { readFileSync, readdirSync, statSync } from "node:fs";
import { gzipSync } from "node:zlib";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const budget = JSON.parse(readFileSync(path.join(root, "bundle-budget.json"), "utf8"));

const gz = (file) => gzipSync(readFileSync(file), { level: 9 }).length;
const kb = (bytes) => (bytes / 1024).toFixed(1).padStart(6) + " kB";

// Entry = <script type="module" src> + <link rel="modulepreload" href> in index.html.
const html = readFileSync(path.join(dist, "index.html"), "utf8");
const entryFiles = [
  ...html.matchAll(/<script[^>]+type="module"[^>]+src="([^"]+\.js)"/g),
  ...html.matchAll(/<link[^>]+rel="modulepreload"[^>]+href="([^"]+\.js)"/g),
].map((m) => path.join(dist, m[1].replace(/^\//, "")));

if (entryFiles.length === 0) {
  console.error("::error::check-bundle: no module script found in dist/index.html");
  process.exit(2);
}

const assets = path.join(dist, "assets");
const allJs = readdirSync(assets)
  .filter((f) => f.endsWith(".js"))
  .map((f) => path.join(assets, f));

const measured = {
  entry: entryFiles.reduce((sum, f) => sum + gz(f), 0),
  total: allJs.reduce((sum, f) => sum + gz(f), 0),
};

let failed = false;
console.log("bundle budget (gzip)\n");
console.log("  metric   measured      limit    headroom");
for (const key of Object.keys(budget.limits)) {
  const limit = budget.limits[key];
  const got = measured[key];
  const over = got > limit;
  if (over) failed = true;
  const head = (((limit - got) / limit) * 100).toFixed(1).padStart(6) + "%";
  console.log(`  ${key.padEnd(7)} ${kb(got)}  ${kb(limit)}  ${head}${over ? "  ← OVER" : ""}`);
}
console.log("\n  entry =", entryFiles.map((f) => path.basename(f)).join(" + "));

if (failed) {
  console.error(
    "\n::error::Bundle grew past bundle-budget.json. If the growth is intended, " +
      "raise the limit in the same PR and say why in the description.",
  );
  process.exit(1);
}
