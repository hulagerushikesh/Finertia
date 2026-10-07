import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

/**
 * Link-preview crawlers (LinkedIn, X, WhatsApp, Slack) read the HTML and never
 * run the app, so every route shares index.html's card. /writeup is the page
 * people will share, so the build also writes dist/writeup.html: the same
 * shell with its own title, description and image. vercel.json routes
 * /writeup to it; the app inside is identical.
 */
const WRITEUP_META = {
  title: "The best-looking strategy was the worst on new data · Finertia",
  ogTitle: "The best-looking strategy was the worst on new data.",
  description:
    "Three trading rules on Apple, 2018–2024. The one that looked best on the years it was tuned on lost money on the years it never saw. Every figure re-run and checked by a script.",
  url: "https://finertia.hulage.in/writeup",
  image: "https://finertia.hulage.in/og-writeup.png",
  imageAlt:
    "Sharpe ratios on AAPL 2018–2024. Momentum 0.95 tuned, −0.30 on new data; MACD 0.51, −0.30; Bollinger 0.56, 1.17.",
};

function writeupShell() {
  const attr = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
  const m = WRITEUP_META;
  const swaps = [
    [/<title>[^<]*<\/title>/, `<title>${m.title}</title>`],
    [/(<link rel="canonical" href=")[^"]*/, `$1${m.url}`],
    [/(name="description"\s+content=")[^"]*/, `$1${attr(m.description)}`],
    [/(property="og:type" content=")[^"]*/, "$1article"],
    [/(property="og:title" content=")[^"]*/, `$1${attr(m.ogTitle)}`],
    [/(property="og:description"\s+content=")[^"]*/, `$1${attr(m.description)}`],
    [/(property="og:url" content=")[^"]*/, `$1${m.url}`],
    [/(property="og:image" content=")[^"]*/, `$1${m.image}`],
    [/(property="og:image:alt" content=")[^"]*/, `$1${attr(m.imageAlt)}`],
    [/(name="twitter:image" content=")[^"]*/, `$1${m.image}`],
    [/(name="twitter:title" content=")[^"]*/, `$1${attr(m.ogTitle)}`],
    [/(name="twitter:description"\s+content=")[^"]*/, `$1${attr(m.description)}`],
  ];
  return {
    name: "writeup-shell",
    apply: "build",
    // After Vite's own html plugin, which emits index.html in this same hook.
    enforce: "post",
    generateBundle(_, bundle) {
      let html = bundle["index.html"].source;
      for (const [re, to] of swaps) {
        // A tag that stops matching would silently ship the landing card.
        if (!re.test(html)) this.error(`writeup-shell: no match for ${re} in index.html`);
        html = html.replace(re, to);
      }
      this.emitFile({ type: "asset", fileName: "writeup.html", source: html });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react(), writeupShell()],
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
