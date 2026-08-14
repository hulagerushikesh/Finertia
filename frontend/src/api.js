import { auth } from "./firebase";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
    const error = new Error(data.detail || `HTTP ${res.status}`);
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

export const startCheckout = () =>
  apiFetch("/api/billing/checkout", { method: "POST" });

export const runPortfolio = (params) =>
  apiFetch("/api/portfolio", { method: "POST", body: JSON.stringify(params) });

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
