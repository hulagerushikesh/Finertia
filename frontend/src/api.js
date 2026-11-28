import { auth } from "./firebase";

// The production site always calls its own origin, which vercel.json rewrites
// to the production API — whatever the build was given. On 28 Nov a value
// meant for Preview builds (the staging API) reached a production build, and
// the live site sent every request to staging, where its origin is refused.
// Preview builds and local development still use VITE_API_BASE_URL.
export const PRODUCTION_HOSTS = ["finertia.hulage.in"];

export function apiBase(env = import.meta.env.VITE_API_BASE_URL, loc = globalThis.location) {
  if (loc && PRODUCTION_HOSTS.includes(loc.hostname)) return loc.origin;
  return env || "http://localhost:8000";
}

const BASE = apiBase();

/**
 * Turn FastAPI's `detail` into something a person can read.
 *
 * It arrives in two shapes. `HTTPException(detail="...")` gives a string, and
 * that has always worked. Every 422 — which is what a request becomes the
 * moment a parameter combination fails validation — gives an ARRAY of
 * `{loc, msg}` objects instead, and `new Error(array)` stringifies it to
 * "[object Object]". So the backend's written-out messages ("Date range is too
 * short: ~21 trading days available, but the momentum strategy needs 50 bars
 * to warm up") never reached the screen, and the errors the user could
 * actually fix were the only ones rendered as noise.
 */
function describeDetail(detail, status) {
  if (typeof detail === "string" && detail) return detail;

  const items = Array.isArray(detail) ? detail : detail && typeof detail === "object" ? [detail] : [];
  const lines = items
    .map((item) => {
      // Pydantic prefixes anything raised by a custom validator with
      // "Value error, ", which is machinery, not information.
      const msg = String(item?.msg || "").replace(/^Value error,\s*/, "");
      // loc is ["body"] for a whole-model check and ["body", "field"] for a
      // single field. Only the second has a name worth naming.
      const field = Array.isArray(item?.loc) ? item.loc.slice(1).join(".") : "";
      return field && msg ? `${field}: ${msg}` : msg;
    })
    .filter(Boolean);

  return lines.length ? lines.join("\n") : `HTTP ${status}`;
}

async function apiFetch(path, options = {}) {
  const token = await auth.currentUser?.getIdToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    // fetch only rejects when the request never reached the server — the API is
    // down, or the origin was blocked by CORS. The browser's own message is
    // "Failed to fetch", which tells the user nothing actionable.
    throw new Error(
      `Cannot reach the API at ${BASE}. Check that the backend is running and that this origin is listed in ALLOWED_ORIGINS.`
    );
  }

  const data = await res.json().catch(() => ({ detail: "Unknown error" }));

  if (!res.ok) {
    const error = new Error(describeDetail(data.detail, res.status));
    error.status = res.status;
    // Present on 500s so a bug report can quote the id that keys the server
    // traceback; on 429s so the UI can say how long to wait.
    error.requestId = data.request_id || res.headers.get("X-Request-Id");
    error.retryAfter = Number(res.headers.get("Retry-After")) || null;
    throw error;
  }

  return data;
}

export const runBacktest = (params) =>
  apiFetch("/api/backtest", { method: "POST", body: JSON.stringify(params) });

export const validateStrategy = (params) =>
  apiFetch("/api/validate", { method: "POST", body: JSON.stringify(params) });

export const getPlans = () => apiFetch("/api/plans");

export const getUsage = () => apiFetch("/api/me/usage");

export const exportMyData = () => apiFetch("/api/me/export");

// The server deletes only when `confirm` is the account's own email address.
export const deleteMyAccount = (confirm) =>
  apiFetch("/api/me", { method: "DELETE", body: JSON.stringify({ confirm }) });

/** One strategy across a tracked index (backend/scan.py). */
export const runScan = (params, universe) =>
  apiFetch("/api/scan", { method: "POST", body: JSON.stringify({ ...params, universe }) });

export const runPortfolio = (params) =>
  apiFetch("/api/portfolio", { method: "POST", body: JSON.stringify(params) });

export const validatePortfolio = (params) =>
  apiFetch("/api/portfolio/validate", { method: "POST", body: JSON.stringify(params) });

export const compareRuns = (runIds) =>
  apiFetch("/api/compare", { method: "POST", body: JSON.stringify({ run_ids: runIds }) });

export const getHistory = (limit = 20, offset = 0) =>
  apiFetch(`/api/history?limit=${limit}&offset=${offset}`);

export const getHistoryRun = (runId) =>
  apiFetch(`/api/history/${runId}`);

export const getAdminStats = () => apiFetch("/api/admin/stats");

export const getAdminUsers = (limit = 50, offset = 0, search = "") =>
  apiFetch(`/api/admin/users?limit=${limit}&offset=${offset}${search ? `&search=${encodeURIComponent(search)}` : ""}`);

export const updateUser = (uid, patch) =>
  apiFetch(`/api/admin/users/${uid}`, { method: "PATCH", body: JSON.stringify(patch) });

export const getAdminRuns = (limit = 50, offset = 0, filters = {}) => {
  const params = new URLSearchParams({ limit, offset });
  if (filters.uid) params.append("uid", filters.uid);
  if (filters.ticker) params.append("ticker", filters.ticker);
  return apiFetch(`/api/admin/runs?${params}`);
};
