# 02 — The stack, as built

FastAPI + Firebase + React, deployed on Vercel + Cloud Run. This file is the
as-built version of the original learning path — it reflects what is actually
running at finertia.hulage.in, not the July plan.

---

## C. FastAPI backend (~20h)

- [ ] **REST concepts** — F · 4h
  16 routes in `backend/main.py`: health, plans, me/usage, billing ×2, strategies,
  backtest, validate, portfolio, compare, history ×2, admin ×4.
  Status codes that carry meaning here: 401 bad token · 403 suspended or not
  admin · 402 monthly quota exceeded · 429 rate limited · 422 bad input.
  402 vs 429 is deliberate — quota and rate limit are different failures.

- [ ] **Auth injection (not `Depends`)** — I · 3h
  Routes take `authorization: Optional[str] = Header(None)` and call
  `inject_user()` / `inject_admin()` *inline*. Consequence: FastAPI's
  `dependency_overrides` does not work in tests — patch `main.<name>` instead.
  Code: `main.py`; tests in `tests/test_routes.py`.

- [ ] **Bearer / JWT flow end to end** — I · 4h
  Firebase Auth issues a signed ID token → React attaches `Authorization: Bearer`
  → `firebase_admin_init.verify_token()` checks the signature → route knows the
  uid. Code: `frontend/src/api.js`, `backend/firebase_admin_init.py`.

- [ ] **CORS, and why production does not need it** — F · 2h
  Local: Vite on 5174 → API on 8000, `ALLOWED_ORIGINS` must match exactly (5174 is
  pinned via `strictPort` for this reason). Production: the browser never calls
  `*.run.app` — Vercel rewrites `/api/*` same-origin. See "Deployment" below.

- [ ] **HTTPException and error mapping** — F · 1h
  Every API error reaches the UI; nothing is swallowed. Global 500 handler +
  request-id middleware in `main.py`.

- [ ] **async vs CPU-bound** — I · 3h
  Routes are `async def` but the backtest maths is synchronous pandas. Async
  helps I/O, not numpy. Know the difference before "optimising".

- [ ] **Rate limiting, hand-written** — I · 2h
  `backend/ratelimit.py`: sliding window, stdlib only. Limiters are module
  singletons — clear `_hits` between tests.

- [ ] **Structured logging** — I · 1h
  `logging_config.py` emits JSON with `severity`/`message` keys so Cloud Logging
  parses them.

## D. Firebase (~15h)

- [ ] **Firebase Auth email/password** — F · 3h
  `AuthContext.jsx` listens on `onAuthStateChanged`. Firebase mutates the user
  object *in place* so React cannot see `emailVerified` change — hence
  `refreshUser()` and an explicit `reload()`.

- [ ] **Firestore data model** — F · 4h
  `users/{uid}` (role, plan, quota, isActive) and `runs/{id}` (params + metrics;
  equity/drawdown arrays are NOT stored — recomputed on demand).
  Composite index `runs: uid ASC, createdAt DESC` is required or History 500s.

- [ ] **Admin SDK bypasses rules** — I · 2h
  The fact that makes the whole security model work: the backend uses the Admin
  SDK, which ignores security rules, so client rules can be locked down hard
  without touching backend behaviour.

- [ ] **Security rules and the privilege-escalation bug** — I · 4h
  Original rules gave users blanket write on their own profile doc — which held
  role, plan, quota. Five attacks worked against the emulator (self-promote to
  admin, self-grant Pro, reset quota, un-suspend, forge a run as another user).
  Now: read own profile; create at registration with role/isActive/totalRuns
  pinned; update `displayName` only via `diff().affectedKeys().hasOnly([...])`.
  `runs` closed to clients entirely.
  Tests: `cd firestore-tests && npm test` (20 emulator tests, needs Java).
  Traps: a no-op write yields empty `affectedKeys()` and is correctly allowed;
  the emulator persists between runs — `clearFirestore()` or `setDoc` becomes update.

- [ ] **serverTimestamp** — F · 1h
  Dates stored as Firestore Timestamps; the first live bug was `Invalid Date` in
  History from mishandling that (`18f866c`).

## E. React frontend (~20h)

- [ ] **Components, props, hooks** — F · 6h
- [ ] **useState + useEffect + Context only** — F · 3h
  No Redux/Zustand by constraint. `AuthContext`, `ToastContext`.
- [ ] **React Router v6, ProtectedRoute / AdminRoute** — F · 3h
  Admin is enforced on *both* sides: `AdminRoute.jsx` and `inject_admin`.
- [ ] **No `<form>` tags** — F · 1h
  Controlled inputs + onClick only, by constraint.
- [ ] **React.lazy + Suspense** — I · 2h
  Routes behind login are lazy. Landing JS went 1,087 → 464 kB. Do NOT add
  recharts to `manualChunks` — naming it promotes it into the entry's static
  graph and it downloads on the landing page anyway (verified via network trace).
- [ ] **Vite, env vars, `strictPort`** — F · 2h
- [ ] **Tailwind + the token sheet** — I · 3h
  Tokens in `tailwind.config.js` + component classes in `src/index.css`.
  Two-tone rule: `accent` violet = the value you measured; `check` mint = the
  reference it is tested against. The redesign branch replaces this with the
  "Blue pencil" sheet (HSL CSS vars, shadcn-style) — see planning/DECISIONS.

## F. Charts with Recharts (~8h)

- [ ] **ResponsiveContainer and data shape** — F · 2h
- [ ] **Chart colours live in `chartTheme.js`** — F · 1h
  Recharts cannot read Tailwind classes; every chart imports `CHART` from there.
- [ ] **Custom tooltips (`Tooltip.jsx`, not `title=`)** — I · 2h
  Native `title` never appears on touch, so every phone user lost the metric
  explanations. The one surviving `title` is the heatmap `<td>`.
- [ ] **Data thinning** — I · 1h  1000+ points → ~300 for render speed.
- [ ] **Type scale: `2xs` (11px) floor, `tick` (10px) chart-internals only** — I · 1h
  Test: if a label is the only place a fact appears, it is not a tick.

## G. SaaS patterns (~10h)

- [ ] **RBAC — user vs admin** — I · 2h
- [ ] **Plans and quota (`plans.py`)** — I · 2h
  Free 50 runs/month, 3 holdings, no validation; Pro $12 unlimited, 10 holdings.
  Pure Python, no Stripe/Firebase imports, so it is testable.
- [ ] **Stripe checkout + webhook signature, hand-verified (`billing.py`)** — I · 3h
  The webhook is unauthenticated by necessity — the signature IS the auth. Never
  deploy without `STRIPE_WEBHOOK_SECRET`. Env-gated: unset → SDK never imported.
- [ ] **Email verification as nudge, not gate** — F · 1h
  No route requires it; gating the dashboard would invent a restriction.
- [ ] **Admin stats scan whole collections** — I · 1h  Fine now; counters later.
- [ ] **Share permalinks (`utils/permalink.js`)** — F · 1h  Config mirrored into the URL.

## H. Deployment & ops — as built (~12h)

- [ ] **Docker: non-root, healthcheck, honours `$PORT`** — F · 2h
- [ ] **Cloud Run, asia-south1, cost-capped** — I · 3h
  `--min-instances 0 --max-instances 2 --memory 512Mi --cpu 1 --concurrency 40`.
  Idle = ₹0. asia-south1 has NO domain mappings (501) — that is why there is no
  `api.finertia.hulage.in`.
- [ ] **Same-origin API via Vercel rewrite** — I · 2h
  `frontend/vercel.json` rewrites `/api/*` → Cloud Run. Why: ad blockers block
  `*.run.app`, and every cross-origin call needed a preflight. One origin kills
  both. `VITE_API_BASE_URL` = the site's own origin.
- [ ] **Secret Manager** — I · 1h
  `FIREBASE_SERVICE_ACCOUNT_JSON` → secret `finertia-sa`, injected with
  `--set-secrets`; runtime SA needs `secretmanager.secretAccessor`.
- [ ] **Backend does NOT auto-deploy** — F · 30m
  Vercel auto-deploys `main`; Cloud Run is a manual `gcloud run deploy`. This is
  the step that got skipped once — production showed naked point estimates for 5
  days because the bootstrap merge was never followed by a redeploy.
- [ ] **`.gcloudignore`** — F · 30m  Without it `.env` was uploaded to the build bucket on every deploy.
- [ ] **Pinned requirements** — F · 30m
  Prod runs pandas 3.0.5 / numpy 2.4.6 / fastapi 0.141.1. Local shared python is
  pandas 2.3.1. Suite passes on both. Give the project its own venv (backlog).
- [ ] **GitHub Actions: CI + secret scan** — I · 2h
  `ci.yml` runs backend tests, frontend build, and fails if a `.env` or service
  key is ever tracked. `deploy.yml` is manual (`workflow_dispatch`), uses Workload
  Identity Federation — no long-lived key in secrets.

---

Next: [03-validation-methods.md](03-validation-methods.md) — the part that makes
this a research project and not a CRUD app.
