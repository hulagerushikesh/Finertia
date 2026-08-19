# Finertia — Strategy Backtesting SaaS

Production-grade backtesting platform for momentum, MACD, and Bollinger mean-reversion strategies. All signal, position, and metric logic is hand-written pure Python (pandas + numpy). Zero external backtesting libraries — you can read the exact lines that produce your Sharpe ratio.

Beyond a single backtest, Finertia answers the two questions that decide whether a result means anything:

- **Walk-forward validation** — optimises parameters on the first 70% of the period and scores them on the remaining 30%. Only the out-of-sample number is evidence.
- **Signal permutation test** — reshuffles the position series 500 times, holding market exposure identical, so only *timing* changes. Separates genuine edge from simply being in the market.

### What it found

Those two checks are only worth building if they change the answer. Run against
AAPL, 2018–2024, they do — ranking the three strategies on the data they were
tuned on gives you exactly the wrong order.

| Strategy | In-sample Sharpe | Out-of-sample Sharpe | Verdict |
|---|---|---|---|
| Momentum | 0.889 | −0.242 | Failed |
| MACD | 0.554 | −0.281 | Failed |
| Bollinger | 0.553 | **1.367** | Held up |

The best in-sample result was the worst out-of-sample one. Momentum looked like
the clear winner and had no edge at all on data it had not been fitted to.

This is one ticker over one period, so it demonstrates the method rather than
proving mean reversion beats trend following. That is the point: a single
backtest is one draw from a distribution, and the number that survives
out-of-sample is the only one worth quoting. The `/demo` page leads with a
losing strategy for the same reason.

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python · FastAPI · pandas · numpy |
| Data | yfinance (OHLCV, auto-cached) |
| Frontend | React 18 · Vite · Tailwind CSS · Recharts |
| Auth | Firebase Authentication (email/password) |
| Database | Cloud Firestore |
| Hosting | Firebase Hosting (frontend) · Cloud Run / any container host (backend) |

---

## Firebase Setup (one-time)

1. Go to [console.firebase.google.com](https://console.firebase.google.com) and create a project.
2. **Authentication** → Sign-in method → Enable **Email/Password**.
3. **Firestore Database** → Create database → Start in **production mode**.
4. **Project Settings** → **Your apps** → Register a **Web app** → copy the config object into your `.env`.
5. **Project Settings** → **Service Accounts** → **Generate new private key** → download the JSON and paste its entire content (on one line) into `FIREBASE_SERVICE_ACCOUNT_JSON`.

---

## First Admin User

After registering your account through the app UI:

1. Firebase Console → **Firestore** → `users` collection → find your document (doc ID = your UID).
2. Edit the `role` field → change from `"user"` to `"admin"`.
3. Reload the app — the Admin nav link will appear.

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # fill in FIREBASE_SERVICE_ACCOUNT_JSON + ALLOWED_ORIGINS
uvicorn main:app --reload --port 8000
```

API will be live at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env        # fill in VITE_FIREBASE_* vars; VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

App will be live at `http://localhost:5174`. The port is pinned in `vite.config.js` so it always matches `ALLOWED_ORIGINS` on the backend — otherwise requests fail CORS with no obvious cause.

---

## Deploy

### Frontend → Firebase Hosting

```bash
cd frontend
npm run build
cd ..
firebase deploy --only hosting
```

### Backend → Cloud Run (or any container host)

```bash
cd backend
# Build and push your Docker image, or deploy directly via Cloud Run source deploy
gcloud run deploy finertia-api \
  --source . \
  --region us-central1 \
  --set-env-vars FIREBASE_SERVICE_ACCOUNT_JSON='...' \
  --set-env-vars ALLOWED_ORIGINS='https://your-app.web.app' \
  --allow-unauthenticated
```

After deploying the backend, set `VITE_API_BASE_URL` in `frontend/.env` to the Cloud Run URL, rebuild, and redeploy the frontend.

---

## Project Structure

```
Finertia/
├── backend/
│   ├── main.py              # FastAPI app + all routes
│   ├── schemas.py           # request models + validation (no Firebase dependency)
│   ├── data.py              # yfinance fetch + cache
│   ├── signals.py           # momentum, MACD, and Bollinger signal generation
│   ├── strategies.py        # strategy registry — dispatch, warm-up, param grids
│   ├── engine.py            # position logic + equity curve
│   ├── metrics.py           # all performance metrics
│   ├── analytics.py         # monthly, annual, and rolling views
│   ├── validation.py        # walk-forward + permutation test
│   ├── risk.py              # stop-loss / take-profit + volatility sizing
│   ├── portfolio.py         # alignment, weighting, aggregation, attribution
│   ├── plans.py             # subscription tiers + monthly quota accounting
│   ├── billing.py           # Stripe checkout + webhook signature verification
│   ├── ratelimit.py         # sliding-window rate limiter
│   ├── logging_config.py    # structured JSON logging
│   ├── firebase_admin_init.py  # Firebase Admin SDK init + auth helpers
│   ├── tests/               # pytest suite (no credentials required)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # LandingPage, Login, Register, Dashboard, History, Profile, Admin/*
│   │   ├── components/      # ConfigPanel, MetricsGrid, charts, ValidationPanel, Toast
│   │   ├── context/         # AuthContext, ToastContext
│   │   ├── hooks/           # useAuth, useToast
│   │   ├── utils/           # csv export, permalink encode/decode
│   │   ├── api.js           # typed API client (auto-injects Firebase token)
│   │   └── firebase.js      # Firebase client SDK init
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── firestore.rules
├── firebase.json
├── .env.example
└── README.md
```

---

## Strategies

Every generator ends with `.shift(1)` — a signal derived from a bar's close can only be acted on at the next bar. Doing that shift in one place is what keeps lookahead bias out of the whole engine. Transaction costs are deducted in proportion to turnover — see [Risk overlays](#risk-overlays) for why.

### Momentum (trend following)

| Condition | Signal |
|-----------|--------|
| `momentum > threshold` AND `close > MA` | **+1 Long** |
| `momentum < -threshold` AND `close < MA` | **−1 Short** |
| Otherwise | **0 Flat** |

### MACD (trend following)

Holds the crossover *state* rather than trading only the crossing bar, so the position series stays continuous.

| Condition | Signal |
|-----------|--------|
| MACD line above signal line | **+1 Long** |
| MACD line below signal line | **−1 Short** |
| Within the warm-up period | **0 Flat** |

### Bollinger (mean reversion)

The opposite stance to the other two — it fades extremes instead of following them, and is flat most of the time.

| Condition | Signal |
|-----------|--------|
| `close < lower band` | **+1 Long** |
| `close > upper band` | **−1 Short** |
| Inside the envelope | **0 Flat** |

### Risk overlays

`backend/risk.py` sits between signals and the engine: signals decide *direction*, the overlays decide *whether to stay in* and *how large*. Every strategy gets both for free.

**Stop-loss / take-profit.** Genuinely path-dependent — whether you are still in a trade on Tuesday depends on Monday — so this is an explicit loop rather than a vectorised expression. Two properties worth knowing:

- **Exits are evaluated at the close.** A bar that moves −10% against a 5% stop realises the full −10%, then exits. Filling at exactly −5% would need intraday data and would flatter every result; a backtest that fills stops at the trigger price is one of the most common ways to manufacture an edge that doesn't exist.
- **A stopped-out trade does not re-enter on the same signal.** It stays flat until the underlying signal changes, otherwise the next bar re-enters and the stop achieves nothing but extra costs.

**Volatility targeting.** Sizes each position at `target_vol / trailing_realised_vol`, capped by `max_leverage`. The trailing window is shifted one bar, exactly like the signals — sizing today may only use volatility measured to yesterday's close. Warm-up bars and flat price runs size to zero rather than to infinity.

Because sizing produces fractional positions, transaction cost is charged on **turnover** (`|Δposition| × cost`) rather than as a flat fee per change. For plain 0 → ±1 signals this is identical; for a −1 → +1 flip it correctly charges two trades' worth, and it stops a 2% size adjustment being billed as a full round trip.

### Adding a strategy

Write a generator in `signals.py`, then add one entry to `STRATEGIES` in `strategies.py` with its build function, warm-up calculation, and walk-forward grid. Routes, engine, and validation all dispatch through `build_positions` / `longest_window` / `param_grid`, so nothing else changes.

---

## Performance Metrics

All computed from scratch — no TA-Lib, no quantstats:

- Total Return, Annualised Return, Annualised Volatility
- Sharpe Ratio, Calmar Ratio
- Max Drawdown
- Win Rate, Profit Factor
- Number of Trades, Best Day, Worst Day, Avg Daily Return

Plus time-sliced views: monthly returns heatmap, annual returns against buy-and-hold, and rolling 60-day Sharpe. Equity curve, trades, and metrics all export to CSV from the dashboard.

---

## Multi-ticker portfolios

Switch the config panel's **Universe** to Portfolio, add 2–10 holdings, and `POST /api/portfolio` runs the selected strategy on each name and combines the legs. Each leg is a complete backtest — its own signals, stops, sizing, and transaction costs — so the portfolio aggregates honest single results rather than being a separate model with its own assumptions.

**Alignment is an inner join.** Only days every holding traded are used. The alternatives are worse: forward-filling a missing bar invents a flat return on a day the asset didn't trade, which lowers measured volatility and flatters every risk metric; a union with gaps lets a leg contribute NaN to a weighted sum, and a NaN portfolio return silently becomes zero.

The cost is real — one holding that listed late truncates the whole portfolio — so the response reports `dropped_bars` and the `limiting_ticker`, and the UI names both. That's measured against the longest-history leg, **not** against the requested start date; comparing to the request would fire the warning whenever a start date landed on a weekend or a holiday, and a warning that shows on nearly every run is one nobody reads.

| Weighting | Behaviour |
|-----------|-----------|
| `equal` | 1/N in each name, rebalanced every bar back to target |
| `inverse_vol` | Weight ∝ 1 / trailing volatility, so no single volatile name dominates the portfolio's risk |

Inverse-vol weights shift the trailing window one bar, like everything else in the engine. Warm-up bars fall back to equal weight rather than to zero exposure, which would silently shorten the period being measured. `max_weight` caps concentration by pushing freed weight out to the holdings that still have room and repeating — clipping and renormalising would scale the capped asset straight back up and achieve nothing.

Reported alongside the usual metrics: each leg's **average weight**, its **contribution** (arithmetic, so the column sums to the total), its **standalone return**, and a **diversification ratio** — weighted average leg volatility over portfolio volatility. 1.0 means the holdings move as one and you bought no diversification; it reports as undefined rather than 0.0 when the portfolio has no volatility, since perfectly offsetting legs are maximally diversified, not minimally.

Walk-forward and the permutation test are defined on a single position series, so validation is not offered for portfolios yet.

## Comparing runs

Tick two to four runs in History and hit Compare. `POST /api/compare` reloads each run's config and **recomputes** its equity curve — curves are never stored, since they are a few thousand floats derivable from the config. Documents stay small, and an engine fix retroactively corrects every historical chart.

Runs may cover different tickers and periods, so the merged series is keyed on date and a run with no bar for a date is simply absent rather than zero. The response reports `overlapping_days`, and the UI says so plainly when two runs never overlap — otherwise the chart would imply a comparison that isn't there.

## Sharing a config

The dashboard mirrors the active configuration into the URL query string, and **Share config** copies a link that reopens it. Only the selected strategy's parameters are written, so a link stays readable rather than carrying all fourteen fields. Unknown keys and unparseable numbers are dropped on read — a truncated link still opens the app with defaults filled in.

---

## Operations

### Rate limiting

Two layers, both sliding-window and both hand-written (`backend/ratelimit.py`) so they are unit-testable without a running server:

| Limit | Default | Keyed on | Why |
|-------|---------|----------|-----|
| `RATE_LIMIT_IP_PER_MIN` | 120 | client IP | Stops an unauthenticated flood before token verification, which is itself a network call |
| `RATE_LIMIT_BACKTEST_PER_MIN` | 20 | user id | A backtest fetches market data |
| `RATE_LIMIT_VALIDATE_PER_MIN` | 5 | user id | A validation run sweeps a parameter grid and then runs 500 permutations |

Compute limits are per **account**, not per address — otherwise an office behind one NAT would share a single budget. A rejected request is not recorded against the window, so a client that keeps retrying does not lock itself out indefinitely.

Counters live in the process. On Cloud Run with N instances the effective ceiling is N × limit, which is right for abuse protection but is not a billing quota; per-user run quotas belong in Firestore.

### Logging

Every line is JSON on stdout, using the `severity` and `message` keys Cloud Logging parses (`backend/logging_config.py`). Each request gets an id, echoed as `X-Request-Id` and included in the body of any 500. A user reporting a failure can quote that id and it leads straight to the traceback:

```json
{"severity": "INFO", "message": "request", "logger": "finertia", "request_id": "d011d05ae7c3", "method": "POST", "path": "/api/backtest", "status": 200, "duration_ms": 412}
```

Unhandled exceptions return a generic message rather than a stack trace, with the request id attached.

### Error tracking

Optional. With `SENTRY_DSN` set, unhandled exceptions are reported; without it the SDK is never imported and nothing changes. `send_default_pii` is off deliberately — request bodies here contain users' strategy parameters, which do not belong in a third-party error tracker. The startup log line reports whether it is enabled.

### Billing and quotas

`backend/plans.py` holds the tiers and quota rules, free of any Stripe or Firebase import so entitlements are testable without credentials or a network.

| | Free | Pro |
|---|---|---|
| Backtests / month | 50 | Unlimited |
| Walk-forward + permutation tests | — | ✓ |
| Portfolio holdings | 3 | 10 |

Quotas count per calendar month in UTC — not local time, or a user crossing a date line could reset their own. A counter stamped with a previous month reads as zero rather than being reset by a write, so nothing has to run at midnight on the first. Exceeding a quota returns **402**, distinct from the rate limiter's 429, so the client can tell "slow down" apart from "upgrade".

Billing is entirely optional. With no `STRIPE_SECRET_KEY` the app runs unchanged: the pricing page renders, the upgrade button says billing is not enabled, and every account stays free.

The webhook is necessarily unauthenticated — Stripe cannot present a Firebase token — so **the signature check is the authentication**. Without it, anyone who learned the URL could POST a completed-checkout event and upgrade themselves. It is implemented in `billing.py` rather than taken from the SDK so the constant-time comparison and the 5-minute replay window are visible and testable. Events that are valid but unrecognised return 200; a non-2xx would make Stripe retry them forever.

### Email verification

Registration sends a Firebase verification email, and signed-in users with an unconfirmed address see a dismissible banner on the app pages with a resend button on a one-minute cooldown.

It is deliberately a nudge and not a gate. No API route requires a verified address, so blocking the dashboard would invent a restriction the backend does not enforce. What verification actually protects is the password-reset path, which is useless if the address is wrong.

A failed send does not fail registration — the account and its profile document already exist by that point, and reporting an error there would read as "your account was not created". The banner is where it surfaces instead, since it appears precisely when the address is unverified.

### Support page

`/support` is public and lists the errors the API actually returns alongside what causes each one — a bad ticker suffix, a date range shorter than the indicator warm-up, a 402 quota vs a 429 burst limit. Quoted messages use `N` rather than real numbers so the page cannot drift out of step with `plans.py`; the pricing page reads the live allowance from `/api/plans`.

Set `VITE_SUPPORT_EMAIL` at build time. Unset, it shows an obviously fake placeholder rather than a plausible wrong address.

### Firestore security rules

The API is not the only door into the database. A signed-in browser holds a real Firebase token and can talk to Firestore directly, so any check that exists only in FastAPI is advisory — the rules are what actually enforce it.

The client's sole legitimate access is its own profile document: it reads that one doc, creates it at registration, and may change `displayName`. Nothing else. `role`, `plan`, `isActive`, `totalRuns`, and the quota counters are server-owned, and the `runs` collection is closed to clients entirely — runs are created and read through the API.

Locking this down costs the backend nothing: the Firebase Admin SDK **bypasses security rules**, so every server-side write still works, and admin tooling needs no client-side grant.

Fields are also pinned at creation. Registration is a browser write, so without constraints the very first document is a free hand — a new account could name itself an admin or arrive already on the Pro plan.

```bash
cd firestore-tests && npm install && npm test
```

20 tests against the Firestore emulator, covering both directions: that registration, profile reads, and display-name edits still work, and that privilege escalation, cross-account access, and run forgery do not. `emulators:exec` starts and stops the emulator itself, so the only prerequisite is Java.

### CI and deploys

`.github/workflows/ci.yml` runs on every push and PR: backend tests, frontend build, and a secret scan that fails if a `.env` or service-account key is ever tracked. None of them need credentials — a pipeline that requires secrets is one that silently stops running.

`deploy.yml` is manual (`workflow_dispatch`) rather than push-triggered, so shipping is always a decision. It runs the tests first, authenticates to GCP by Workload Identity Federation rather than a long-lived key in a repo secret, polls `/api/health` afterwards (a deploy that "succeeded" but serves 500s is not a successful deploy), and fails the frontend build if the bundle still points at localhost.

---

## Tests

```bash
cd backend
pytest tests/ -q
```

404 tests covering signals, engine, metrics, analytics, strategies, validation, request schemas, risk overlays, portfolio construction, plan entitlements, Stripe webhook verification, the rate limiter, the log formatter, and the HTTP layer. No Firebase credentials needed, so they run in CI unmodified.

`test_routes.py` covers the part that decides who may call everything else: token handling, suspended accounts, admin gating, quota and entitlement enforcement, rate limiting, and how failures become status codes. `verify_token`, the profile lookup, the Firestore client, and the price fetch are all replaced, so no network or credentials are involved.

Two distinctions it pins down, because getting either wrong puts the wrong message in front of a user: **402 means upgrade and 429 means wait**, and **role is read from the Firestore profile, never from the token** — a token claiming `role: admin` is refused.

The suite includes an explicit lookahead-bias guard: a position must not be open on a price-spike bar.
