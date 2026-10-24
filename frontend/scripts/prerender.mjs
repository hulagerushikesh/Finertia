// Writes each public page's content into its HTML shell, after `vite build`.
//
// Crawlers that do not run JavaScript otherwise see an empty <div id="root">
// on every route. This renders src/prerender.jsx's pages through Vite (same
// aliases, ?raw imports and env as the build) and puts the markup inside
// #root, tagged with the page's name so main.jsx can load that page before
// replacing it. index.html carries the landing page; every other route gets
// app.html, the untouched shell (vercel.json).
//
// Fails the build when a page renders without its heading: a silent empty
// copy would be worse than none.
//
// Usage: node scripts/prerender.mjs   (after `vite build`)

import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(root, "dist");
const firebase = path.join(root, "src", "firebase.js");
const ROOT_DIV = '<div id="root"></div>';

process.env.NODE_ENV = "production";

const vite = await createServer({
  root,
  mode: "production",
  appType: "custom",
  logLevel: "warn",
  server: { middlewareMode: true, hmr: false, watch: null },
  // react-router 7 lists its ESM build under the "module-sync" condition and
  // its CommonJS build as the Node default, whose named exports ESM cannot
  // see. Which one Node picks depends on its version, so Vite bundles the
  // package itself and is told to take the ESM build.
  ssr: { noExternal: ["react-router", "react-router-dom"], resolve: { conditions: ["module-sync"] } },
  plugins: [
    {
      // The CI build has no Firebase config, and getAuth() throws without an
      // API key. Nothing here signs in, so the module is replaced outright.
      name: "prerender-no-firebase",
      enforce: "pre",
      load(id) {
        if (id === firebase) return "export const app = null; export const auth = null; export const db = null;";
      },
    },
  ],
});

let failed = false;
try {
  const { PAGES, render } = await vite.ssrLoadModule("/src/prerender.jsx");
  for (const name of Object.keys(PAGES)) {
    const file = path.join(dist, name === "landing" ? "index.html" : `${name}.html`);
    const html = readFileSync(file, "utf8");
    if (!html.includes(ROOT_DIV)) throw new Error(`${path.basename(file)} has no empty ${ROOT_DIV}`);
    const markup = await render(name);
    if (!/<h1[\s>]/.test(markup)) throw new Error(`${name} rendered without an <h1>`);
    writeFileSync(file, html.replace(ROOT_DIV, `<div id="root" data-prerendered="${name}">${markup}</div>`));
    console.log(`prerender: ${path.basename(file).padEnd(24)} ${(markup.length / 1024).toFixed(1).padStart(6)} kB`);
  }
} catch (err) {
  console.error(`::error::prerender: ${err.message}`);
  failed = true;
} finally {
  await vite.close();
}
process.exit(failed ? 1 : 0);
