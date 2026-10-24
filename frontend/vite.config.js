import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

import { PAGE_META, shellFor } from "./src/lib/pageMeta.js";

/**
 * One copy of index.html per public page, with that page's title, description
 * and share card (src/lib/pageMeta.js says why). vercel.json routes each path
 * to its copy.
 */
function routeShells() {
  return {
    name: "route-shells",
    apply: "build",
    // After Vite's own html plugin, which emits index.html in this same hook.
    enforce: "post",
    generateBundle(_, bundle) {
      const html = bundle["index.html"].source;
      for (const [name, meta] of Object.entries(PAGE_META)) {
        let source;
        try {
          source = shellFor(html, meta);
        } catch (err) {
          this.error(`route-shells: ${err.message}`);
        }
        this.emitFile({ type: "asset", fileName: `${name}.html`, source });
      }
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react(), routeShells()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "src") },
    },
    // Pre-bundle every firebase entry together. If Vite discovers one of them
    // mid-session it re-optimises on its own and ends up with two copies of
    // @firebase/app, and the second reports "Service firestore/lite is not
    // available" at runtime. Listing them up front keeps one registry.
    optimizeDeps: {
      include: ["firebase/app", "firebase/auth", "firebase/firestore/lite"],
    },
    build: {
      outDir: "dist",
      rollupOptions: {
        output: {
          // Only Firebase is named here. It is a genuine static dependency —
          // AuthContext runs on first paint — so splitting it just means a
          // returning visitor keeps it cached across app deploys.
          //
          // Recharts is deliberately NOT listed. Naming a chunk here promotes
          // it into the entry's static graph, which makes Vite emit a
          // modulepreload link for it; it then downloads on the landing page
          // even though only the lazy routes import it. Left alone, Rollup
          // derives the chunk from the dynamic imports and it loads on demand.
          manualChunks: {
            firebase: ["firebase/app", "firebase/auth"],
          },
        },
      },
    },
    // Unit tests (Vitest). jsdom for components; src/test/setup.js adds the
    // jest-dom matchers and unmounts between tests.
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.js"],
      include: ["src/**/*.test.{js,jsx}"],
      css: false,
    },
    server: {
      // /writeup imports planning/write-up.md, which sits outside the Vite root.
      fs: { allow: [".", "../planning"] },
      // Pinned so the origin always matches ALLOWED_ORIGINS on the backend.
      // strictPort makes a clash fail loudly instead of silently sliding to
      // 5175, which would then be blocked by CORS with no obvious cause.
      port: 5174,
      strictPort: true,
      proxy: {
        "/api": {
          target: apiBase,
          changeOrigin: true,
        },
      },
    },
  };
});
