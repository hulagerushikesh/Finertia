# Roadmap — from project to product

_Drafted 13 Oct 2026 by the PM hat. Direction change recorded in
[DECISIONS.md](DECISIONS.md) (13 Oct). Sprint detail lives in
[NEXT-MILESTONE.md](NEXT-MILESTONE.md); everything unscheduled in
[BACKLOG.md](BACKLOG.md)._

## Vision

**Finertia is the backtester that tells you whether you got lucky.** Every
other retail backtester stops at "this rule made 40%". Finertia goes on to ask
whether that number survives data it was never tuned on, and says so in plain
words. That is the USP. It is real (728 tests, a published write-up whose
every figure is re-run by a script), but today it sits behind a paywall that
nobody has paid through.

Three horizons:

| Horizon | Goal | Done when |
|---|---|---|
| **H1 — Quality foundation** (M11, ~2 weeks) | Stop shipping bugs a friend finds in 5 minutes | Logged-in paths covered by automated E2E; errors in prod are seen before users report them |
| **H2 — Product readiness** (M12, ~4 weeks) | Safe and legal to charge real money | Legal check done, licensed data, Stripe live behind the evidence gate, support + account deletion |
| **H3 — Growth** (M13+) | People find it and come back | Organic sign-ups without the author's network; a measured return rate |

## Team — the hats

One person (the author) plus Claude, working as a full-stack team. Each item
in the plan has an owner hat so nothing falls between roles.

| Hat | Owns |
|---|---|
| **PM** | Vision, roadmap, priorities, what we do *not* build; reads tester evidence |
| **Scrum** | 2-week sprints, the board (NEXT-MILESTONE), Definition of Done, the review |
| **Backend** | FastAPI, engine, validation maths, API contracts |
| **Frontend** | React app, UX, accessibility, bugs |
| **DB** | Firestore model, indexes, rules, backups, data lifecycle |
| **Cloud** | Cloud Run, Vercel, CI/CD, cost, secrets |
| **System** | Architecture, scaling, observability, reliability |

**Ways of working**

- Sprint = 2 weeks. Plan at the start (PM + Scrum), review at the end with the
  author, who signs off on scope and on anything touching production.
- **Definition of Done** (new): code + unit tests + an E2E path for any user
  flow it touches + passes the [release checklist](../RELEASE.md) +
  STATUS updated. "It builds" is no longer done — that is how #84's bugs
  shipped.
- Claude merges its own PRs on green CI (standing rule); backend deploys and
  production data/config changes still need the author's yes.

## Where we are — audit, 13 Oct (rechecked 24 Oct)

What is strong, and what a product would be missing, by hat. The last column
is what has happened to each gap since; the first two are left as written.

| Hat | Strong | Missing / risk | 24 Oct |
|---|---|---|---|
| Backend | 728 tests, mutation-checked; validation suite (walk-forward, permutation, DSR, PBO, whole-grid, Sharpe-difference) | Rate limiter is **in-memory per instance** (`ratelimit.py`) — with `max-instances 2` the real limit is double and not shared | Closed: shared limits in Firestore (M11 #5); 840 backend tests |
| Frontend | Theme and design system solid; accessible contrast | **Zero frontend tests, zero E2E.** Every logged-in bug this month (#58, #71, #74, #84) was found by a human | Closed: 140 vitest, 26 E2E against the emulators (M11 #1–2) |
| DB | Rules tested (20 emulator tests); price cache | No `firestore.indexes.json` in the repo; admin stats **stream whole collections** (`main.py` ~1232) — fine at 6 users, breaks at a few thousand; no backup / point-in-time recovery; no account deletion path | Closed: `firestore.indexes.json`, `count()` aggregations (M11 #6), PITR + backups with a restore drill, deletion on the API (M12 #1, #5) |
| Cloud | One-command deploy (WIF), drift detector, ₹0 idle | Cold start **11.4 s** on the first run (`min-instances 0`) — testers read it as broken | Closed for ₹0: the uptime check keeps an instance warm (M12 #6). B1 (API to us-central1, next to Firestore) on 1 Nov |
| System | JSON logs; Sentry wired but **unset** (env-gated) | No error visibility in prod: we learn about crashes from WhatsApp | Closed: Sentry on both sides, uptime and 5xx alerts to the author (M11 #3, M12 #2) |
| Product | USP proven; /demo shows it logged out | **USP is behind the paywall:** 4 of 4 testers hit the Pro wall, 0 went Pro. A free user never sees the one thing that makes Finertia different | Built, off until the round closes: one free validation a month (`FREE_VALIDATIONS_PER_MONTH`, `free-validation`); switched on 1 Nov with B1 |
| SEO | robots.txt, sitemap (16 URLs), og cards, pre-rendered `/writeup` | Every other route is a client-rendered SPA — crawlers see an empty shell for `/`, `/demo`, `/pricing` | Closed 24 Oct: own title and card per page (#138), the six public pages' content rendered at build time (#139, `scripts/prerender.mjs`). Pricing's plan cards are in the pre-render too (#145). One pre-rendered page per strategy plus `/strategies`; five `/learn` articles plus an index; per-page JSON-LD (BreadcrumbList, and Article on the write-up, strategy and learn pages). 16 URLs in the sitemap |
| Legal | — | Not cleared to charge: **SEBI** positioning (research-analyst / investment-advice lines), **Yahoo data licence** (yfinance is not licensed for commercial use), **DPDP Act 2023** (India: consent, deletion, grievance contact), no Terms / Privacy pages checked | Open: brief deferred until after the build work (DECISIONS 13 Oct); data on ₹0 until the data sprint |

## H1 — M11 "Quality foundation" (next sprint)

No new features. Make what exists trustworthy. Ordered by impact.

| # | Item | Hat | Evidence of done |
|---|---|---|---|
| 1 | ✅ **E2E suite (Playwright) against the Firebase Auth + Firestore emulators** — register, verify banner, run backtest, clear ticker → Validation (the #84 path), Pro wall, History re-run, Profile save, admin Give/Remove Pro | Frontend + System | **Done 13 Oct:** 15 tests, 34 s locally, CI job "E2E (Playwright)"; the Pro-wall test fails on the pre-#84 DashboardPage and passes after |
| 2 | ✅ **Unit tests for the frontend** (Vitest + Testing Library) on DashboardPage state, ConfigPanel validation, permalink encode/decode | Frontend | **Done 13 Oct:** 53 tests in 10 files, ~2 s, run in CI's "Frontend build" job. Mutation-checked: reverting `ranParams` in DashboardPage, or the 422 parsing in `api.js`, fails them |
| 3 | ✅ **Turn on Sentry**, backend and frontend, with release tags | System + Cloud | **Code done 13 Oct:** errors only, no PII (no locals, bodies, query strings, IPs, emails; uid only), releases from K_REVISION / Vercel SHA, browser SDK lazy-loaded. Tests run the real SDKs against a fake transport; a real-browser probe confirmed nothing private leaves. **Open:** the prod proof — deploy, then `POST /api/admin/sentry-test` shows up in Sentry |
| 4 | ✅ **Date input that can't be misread** — presets (1Y / 3Y / 5Y / Max) and the chosen range shown in words ("1 Jan 2024 → 6 Jan 2024") beside the native pickers | Frontend | **Done 13 Oct:** presets 1Y/3Y/5Y/10Y ending today (Max dropped: listing dates differ per ticker, so it would need a data call); the range in words with its length and ~trading days; a backwards range or future end blocks Run before any request. 16 new unit tests; E2E green |
| 5 | ✅ **Shared rate limit** — move per-user limits to Firestore counters (or halve per-instance limits and document) | Backend + DB | **Done 13 Oct:** backtest and validate limits in Firestore (`ratelimits`), one round trip per check, fail-open to in-process. Holds across 2 instances in unit tests and against the Firestore emulator in CI. Optional: a TTL policy on `ratelimits.expires_at` (prod config, ask first) |
| 6 | ✅ **Admin stats via Firestore `count()` aggregation**, not full scans; commit `firestore.indexes.json` | DB | **Done 13 Oct:** `admin_queries.py` — aggregations for counts/averages, DB-side paging, email-prefix search, top tickers over the last 500 runs; `firestore.indexes.json` with the run indexes and index exemptions for price arrays and rate-limit counters. 5 emulator tests in CI. Index deploy is a prod change (ask first) |
| 7 | ✅ **Release checklist (PVT)** as a doc, run before every production deploy | Scrum | **Done 13 Oct:** [RELEASE.md](../RELEASE.md) (before merge / before deploy / deploy / after / rollback), a PR template with part 1, and `scripts/release-check.sh pre\|post` (read-only: CI + Vercel state, what backend/ would ship, new env vars, live rules vs repo, indexes READY, health serving the tagged commit, 401 on admin without a token, CORS, public pages, error logs). `/api/health` now names its commit and revision; the Deploy workflow waits for its own commit. First run found the live Firestore rules behind the repo (#91's `ratelimits` block never deployed) |

## H2 — M12 "Product readiness"

**Sprint 1 (14–27 Oct) is on the board: [NEXT-MILESTONE.md](NEXT-MILESTONE.md).** It covers what testers cannot see while the round runs to 31 Oct; product changes come in sprint 2.

Build what charging requires. **Stripe goes live only when the 8 Oct evidence
rule says so** (two or more clear "would pay") — everything else here is worth
doing anyway.

| Item | Hat | Notes |
|---|---|---|
| Legal review: SEBI positioning, DPDP Act, Terms + Privacy pages | PM | Before any charge; a one-off paid consult, **booked after the build work** (13 Oct) |
| **Licensed market data** replacing yfinance for paid users (EOD provider for NSE + US) | Backend + Cloud | The single biggest product risk; ₹0 until the build work is done, then **a dedicated data sprint** (13 Oct) |
| **One free validation per month** on the free plan | PM + Backend | Lets free users see the USP; Pro = unlimited. Measure conversion |
| Account deletion + data export (DPDP) | Backend + DB | Self-serve from Profile |
| Firestore point-in-time recovery + a scheduled export | DB + Cloud | Restore drill done once |
| Cold start: `min-instances 1` (≈ ₹1–2k/month) or a lighter startup | Cloud | First run < 3 s |
| Support inbox a human reads; status page | PM | `support@` answered within a day |
| Payments live (provider, keys, one real payment and refund) | Backend + Cloud | Gated on evidence. Researched 24 Oct: [PAYMENTS-PLAN.md](PAYMENTS-PLAN.md) recommends a merchant of record (Dodo Payments, then Paddle), since new Stripe India accounts are invite-only |
| Onboarding: first-run tour, sample strategies, empty states | Frontend | A tester finishes unaided, measured |

## H3 — M13+ "Growth"

| Item | Hat | Notes |
|---|---|---|
| **Pre-render public routes** (`/`, `/demo`, `/pricing`, `/docs`) the way `/writeup` already is; per-route titles and meta | Frontend | Crawlers see real content. ✅ Done 24 Oct: titles, descriptions and share cards per route (`src/lib/pageMeta.js`, one HTML shell each), then the page content itself, rendered at build time into each shell (`scripts/prerender.mjs`) and replaced by the live page on load |
| Content SEO: one page per strategy × well-known ticker ("Does momentum work on Reliance?") generated from real, re-checked runs. First step done 24 Oct: one page per strategy (`/strategies/*`) quoting the write-up's AAPL figures, checked against it by a test. Second step 24 Oct: five `/learn` articles on the questions people search before trusting a backtest (walk-forward, overfitting, lookahead, Sharpe, permutation test) | PM + Backend | Long-tail search traffic; every number reproducible like the write-up |
| Shareable result cards (og image per run permalink) | Frontend + Cloud | Every shared run is an ad |
| Education path: class accounts, a course built on the write-up | PM | Only if students engage (8 Oct rule) |
| Strategy builder (user-defined rules) | Backend + Frontend | Biggest feature ask in the space; large; only after H2 |
| Intraday data | Backend | Needs the paid data source first |

## Release checklist (PVT)

Moved to [RELEASE.md](../RELEASE.md), next to the code it checks.

## What we are not doing (and why)

- **No new strategies or indicators in H1** — the bottleneck is trust and
  reach, not features.
- **No charging before the legal check and licensed data** — a paid product
  on unlicensed data is a liability, not revenue.
- **No microservices / Kubernetes** — one Cloud Run service is the right size
  until load says otherwise; the scaling gaps above (rate limit, scans) are
  fixed in place.
