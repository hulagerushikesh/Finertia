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
  flow it touches + passes the [release checklist](#release-checklist-pvt) +
  STATUS updated. "It builds" is no longer done — that is how #84's bugs
  shipped.
- Claude merges its own PRs on green CI (standing rule); backend deploys and
  production data/config changes still need the author's yes.

## Where we are — audit, 13 Oct

What is strong, and what a product would be missing, by hat.

| Hat | Strong | Missing / risk |
|---|---|---|
| Backend | 728 tests, mutation-checked; validation suite (walk-forward, permutation, DSR, PBO, whole-grid, Sharpe-difference) | Rate limiter is **in-memory per instance** (`ratelimit.py`) — with `max-instances 2` the real limit is double and not shared |
| Frontend | Theme and design system solid; accessible contrast | **Zero frontend tests, zero E2E.** Every logged-in bug this month (#58, #71, #74, #84) was found by a human |
| DB | Rules tested (20 emulator tests); price cache | No `firestore.indexes.json` in the repo; admin stats **stream whole collections** (`main.py` ~1232) — fine at 6 users, breaks at a few thousand; no backup / point-in-time recovery; no account deletion path |
| Cloud | One-command deploy (WIF), drift detector, ₹0 idle | Cold start **11.4 s** on the first run (`min-instances 0`) — testers read it as broken |
| System | JSON logs; Sentry wired but **unset** (env-gated) | No error visibility in prod: we learn about crashes from WhatsApp |
| Product | USP proven; /demo shows it logged out | **USP is behind the paywall:** 4 of 4 testers hit the Pro wall, 0 went Pro. A free user never sees the one thing that makes Finertia different |
| SEO | robots.txt, sitemap (6 URLs), og cards, pre-rendered `/writeup` | Every other route is a client-rendered SPA — crawlers see an empty shell for `/`, `/demo`, `/pricing` |
| Legal | — | Not cleared to charge: **SEBI** positioning (research-analyst / investment-advice lines), **Yahoo data licence** (yfinance is not licensed for commercial use), **DPDP Act 2023** (India: consent, deletion, grievance contact), no Terms / Privacy pages checked |

## H1 — M11 "Quality foundation" (next sprint)

No new features. Make what exists trustworthy. Ordered by impact.

| # | Item | Hat | Evidence of done |
|---|---|---|---|
| 1 | **E2E suite (Playwright) against the Firebase Auth + Firestore emulators** — register, verify banner, run backtest, clear ticker → Validation (the #84 path), Pro wall, History re-run, Profile save, admin Give/Remove Pro | Frontend + System | Runs in CI on every PR; reproduces #84's bug on the pre-fix commit |
| 2 | **Unit tests for the frontend** (Vitest + Testing Library) on DashboardPage state, ConfigPanel validation, permalink encode/decode | Frontend | Added to CI; covers the `ranParams` snapshot |
| 3 | **Turn on Sentry**, backend and frontend, with release tags | System + Cloud | A forced test error shows up in Sentry from prod. Needs the author's Sentry DSN |
| 4 | **Date input that can't be misread** — presets (1Y / 3Y / 5Y / Max) and the chosen range shown in words ("1 Jan 2024 → 6 Jan 2024") beside the native pickers | Frontend | The dd/mm vs mm/dd mix-up from 12 Oct is impossible to reach without seeing the words |
| 5 | **Shared rate limit** — move per-user limits to Firestore counters (or halve per-instance limits and document) | Backend + DB | A limit holds across 2 instances in a test |
| 6 | **Admin stats via Firestore `count()` aggregation**, not full scans; commit `firestore.indexes.json` | DB | Admin overview reads O(1) documents |
| 7 | **Release checklist (PVT)** as a doc, run before every production deploy | Scrum | Checked off in the PR of each deploy |

## H2 — M12 "Product readiness"

Build what charging requires. **Stripe goes live only when the 8 Oct evidence
rule says so** (two or more clear "would pay") — everything else here is worth
doing anyway.

| Item | Hat | Notes |
|---|---|---|
| Legal review: SEBI positioning, DPDP Act, Terms + Privacy pages | PM | Before any charge; probably a one-off paid consult |
| **Licensed market data** replacing yfinance for paid users (EOD provider for NSE + US) | Backend + Cloud | The single biggest product risk; cost per month decides pricing |
| **One free validation per month** on the free plan | PM + Backend | Lets free users see the USP; Pro = unlimited. Measure conversion |
| Account deletion + data export (DPDP) | Backend + DB | Self-serve from Profile |
| Firestore point-in-time recovery + a scheduled export | DB + Cloud | Restore drill done once |
| Cold start: `min-instances 1` (≈ ₹1–2k/month) or a lighter startup | Cloud | First run < 3 s |
| Support inbox a human reads; status page | PM | `support@` answered within a day |
| Stripe live (keys + webhook secret + one real test payment) | Backend + Cloud | Gated on evidence |
| Onboarding: first-run tour, sample strategies, empty states | Frontend | A tester finishes unaided, measured |

## H3 — M13+ "Growth"

| Item | Hat | Notes |
|---|---|---|
| **Pre-render public routes** (`/`, `/demo`, `/pricing`, `/docs`) the way `/writeup` already is; per-route titles and meta | Frontend | Crawlers see real content |
| Content SEO: one page per strategy × well-known ticker ("Does momentum work on Reliance?") generated from real, re-checked runs | PM + Backend | Long-tail search traffic; every number reproducible like the write-up |
| Shareable result cards (og image per run permalink) | Frontend + Cloud | Every shared run is an ad |
| Education path: class accounts, a course built on the write-up | PM | Only if students engage (8 Oct rule) |
| Strategy builder (user-defined rules) | Backend + Frontend | Biggest feature ask in the space; large; only after H2 |
| Intraday data | Backend | Needs the paid data source first |

## Release checklist (PVT)

Run before every production deploy and tick it in the PR. Until the E2E suite
(M11 #1) exists, by hand.

- [ ] Logged out: `/`, `/demo` (Results + Validation tabs), `/pricing`, `/writeup` load, no console errors, 375 px no horizontal scroll
- [ ] Register a new account (emulator or test project) → banner shows → can run
- [ ] Run a backtest; clear the ticker box; open Validation → Pro wall (free) / verdict (Pro)
- [ ] Too-short date range → error names the ISO range
- [ ] History: re-run opens the config; Profile: display name saves
- [ ] Admin: Give Pro → "pro · comp"; Remove Pro → free; columns aligned, text readable in both themes
- [ ] Light **and** dark theme on the pages touched
- [ ] `/api/health` 200; `backend-deployed` tag == deployed commit

## What we are not doing (and why)

- **No new strategies or indicators in H1** — the bottleneck is trust and
  reach, not features.
- **No charging before the legal check and licensed data** — a paid product
  on unlicensed data is a liability, not revenue.
- **No microservices / Kubernetes** — one Cloud Run service is the right size
  until load says otherwise; the scaling gaps above (rate limit, scans) are
  fixed in place.
