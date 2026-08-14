import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE_URL || "http://localhost:8000";

  return {
    plugins: [react()],
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
