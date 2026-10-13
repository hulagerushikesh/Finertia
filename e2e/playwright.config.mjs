// End-to-end suite: the real React app, the real FastAPI app and the real
// Firestore security rules, wired to local Firebase emulators. No real
// project, no Yahoo — prices are seeded by backend/scripts/seed_e2e.py.
//
//   cd e2e && npm test
//
// Ports are off the usual dev ones (5174 / 8000) so a running dev server
// does not collide with the suite.
import { defineConfig, devices } from "@playwright/test";

const APP = "http://127.0.0.1:5175";
const API = "http://127.0.0.1:8001";

export default defineConfig({
  testDir: "./tests",
  // One shared emulator and one API process: tests run in order, not in
  // parallel, so rate limits and counts stay predictable.
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: APP,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "e2e/node_modules/.bin/firebase emulators:start --only auth,firestore --project demo-finertia",
      cwd: "..",
      url: "http://127.0.0.1:9099",
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      stdout: "ignore",
      // Playwright's default is SIGKILL, which orphans the emulators' Java
      // process and leaves port 8080 taken for the next run. SIGTERM lets the
      // CLI shut them down.
      gracefulShutdown: { signal: "SIGTERM", timeout: 15_000 },
    },
    {
      command: "./scripts/start-backend.sh",
      url: `${API}/api/health`,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "npm --prefix ../frontend run dev -- --host 127.0.0.1 --port 5175 --strictPort",
      url: APP,
      timeout: 120_000,
      reuseExistingServer: !process.env.CI,
      env: {
        VITE_FIREBASE_EMULATORS: "1",
        VITE_FIREBASE_API_KEY: "demo-key",
        VITE_FIREBASE_AUTH_DOMAIN: "demo-finertia.firebaseapp.com",
        VITE_FIREBASE_PROJECT_ID: "demo-finertia",
        VITE_FIREBASE_APP_ID: "demo-app",
        VITE_API_BASE_URL: API,
      },
    },
  ],
});
