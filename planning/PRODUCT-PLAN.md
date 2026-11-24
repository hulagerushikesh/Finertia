# Product plan: from portfolio piece to a product for 100,000 users

_24 Nov 2026. Written for the author, as a staff engineer would write it: honest
about where the project is, specific about what a 100k-user product needs, and
phased so nothing gets rewritten twice. Supersedes the "portfolio piece" direction
(DECISIONS 24 Nov). PLAN.md stays the record for the outreach work already running._

## 1. Where we are, honestly

**Strong, and worth keeping:**

- **A correct engine.** It closes lookahead bias by design and charges costs on
  turnover. 856 backend tests back it, and every published figure is re-run by
  a script.
- **Statistics no retail tool has.** Walk-forward testing, a shuffle test for
  timing luck, Deflated Sharpe, PBO, whole-grid tests (Reality Check, SPA,
  Romano-Wolf), and a confidence interval on every number.
- **Sound operations for its size.** CI, a deploy workflow, Sentry, uptime
  alerts, Firestore backups with restore drilled, a dedicated service account,
  and costs of ₹0 when idle.
- **A working front end.** Dashboard, portfolio, comparison, history, sharing,
  a demo, 60 pre-rendered public pages, and six articles.

**Why it reads as a personal project, not a product:**

| Area | Today | What a product needs |
|---|---|---|
| What a user can test | 3 fixed strategies (momentum, MACD, Bollinger), one stock or a small basket | Their own rules: indicators plus conditions, built without code |
| Data | Yahoo via yfinance, free, unlicensed for commercial use, fetched during requests | Licensed end-of-day data for all NSE/BSE stocks, held in our own store, refreshed nightly |
| Compute | Every backtest and every validation runs inside the API request; max 2 instances | API and compute split; heavy jobs queued; repeated results served from a cache |
| Code shape | One 1,686-line `main.py` holds every route | Modules per domain with clear boundaries, and a versioned API |
| Environments | Production only | Staging that mirrors production; preview builds per pull request |
| Money | Pro plan built, Stripe never wired; Vercel Hobby plan (non-commercial terms) | India-first payments (UPI), GST invoices, a host plan that allows charging |
| Knowing users | Page views only | An activation funnel and week-1/week-4 retention, measured |
| Reasons to come back | None: test once, leave | Saved strategies, alerts when a rule fires, watchlists |
| Evidence of demand | 5 testers, **0 of 5 returned**, 0 would pay (DECISIONS 31 Oct) | Retention first, then revenue |

The last row matters most. **Scale is not the hard part. Retention is.** A system
built for 100k users that nobody returns to is still a portfolio piece. So every
phase below has an exit gate measured on real users, not only on code.

## 2. What 100k users means in numbers

A staff engineer's first job is to size the problem before choosing tools.

| Assumption | Value |
|---|---|
| Registered users | 100,000 |
| Active on a given day | 10% → 10,000 |
| Backtests per active user per day | 5 → 50,000 a day |
| Busiest hour (evening, after market close) | 15% of the day → about 2 a second, bursts of 20 |
| Validations | 1 in 10 active users, once a day → 1,000 a day |

| Load | Cost to serve it |
|---|---|
| Backtest, 10 years of one stock, uncached | about 0.5 s of one CPU (measured 14 Oct). A burst of 20 a second is about 10 CPUs, before any caching |
| Validation (hundreds of backtests) | 5–30 s of CPU each; 1,000 a day is about 8 CPU-hours, so it must run on a queue, never inside a request |
| Same request twice | Same answer: a backtest is deterministic. With a cache keyed by inputs and data version, most popular runs cost nothing |
| Storage | Daily bars for 2,500 Indian stocks over 20 years is about 12.5 million rows, under 1 GB. Small |

**Conclusion:** the compute is modest, and Cloud Run plus a queue handles it.
The real work for 100k users is (1) licensed data we own, (2) taking heavy jobs
out of the request path, (3) a product people return to, and (4) payments and
compliance that hold up. That is the order of this plan.

## 3. The product

- **For:** Indian retail traders and investors who want to test an idea before
  putting money on it. There are tens of millions of demat accounts, and no
  local tool tests ideas honestly. Students and quant job candidates come
  second; they bring traffic, not revenue.
- **The job:** "Tell me whether my rule would have worked on Indian stocks, after
  costs and taxes, and whether that was luck."
- **The core loop:** build a rule → test it on one stock → test it across an
  index → validate it → save it → get an alert when it fires → come back.
- **North-star metric:** weekly active testers, people who ran at least one test
  in the past 7 days. Supporting metrics: activation (signed up and finished one
  backtest in the first session) and week-4 retention.
- **Never:** tips, predictions, or "buy this". Finertia tests the user's own
  rules on past data; it does not recommend trades (SEBI rule, see section 7).

## 4. Target architecture

```
Browser / PWA ──► Vercel CDN: static app + pre-rendered public pages (cache all public GETs)
      │
      └─ /api/v1 ──► Cloud Run "api" (stateless FastAPI, autoscaled, min 1 at peak hours)
                        │  auth (Firebase), quotas, entitlements, reads
                        ├─► Redis (Memorystore): result cache, rate limits, hot price slices
                        ├─► Postgres (Cloud SQL): users, plans, strategies, runs, alerts, payments
                        ├─► Price store: Parquet on GCS, versioned per nightly load, read via DuckDB/Polars
                        └─► Cloud Tasks ──► Cloud Run "worker": validations, index-wide scans, alerts
                                               (same engine package, separate scaling, own timeouts)

Nightly (Cloud Scheduler): ingest licensed EOD data → check it → adjust for corporate actions
                           → publish a new data version → evaluate saved alerts → send emails
```

**Decisions behind it (each gets its own short record, an ADR, when it is built):**

1. **Licensed EOD data, held by us.** No vendor calls during a request. Every
   result names the data version it used, so cached results stay valid until
   the next nightly load. Candidates (EODHD, Global Datafeeds, TrueData, NSE's
   own data products) are compared on licence terms, coverage, corporate
   actions and price; the author chooses.
2. **Postgres as the system of record. Firestore stays only where it already
   works (auth-adjacent user documents) until migrated.** Runs, strategies,
   alerts and payments are relational, admin queries need joins, and
   rate-limit counters in Firestore cost money on every request.
3. **Redis for anything hot or short-lived:** result cache, rate limits, quota
   counters.
4. **API and worker are the same code, deployed twice.** The engine becomes a
   package with no web or database imports (mostly true already), so both
   import it.
5. **A cache key = hash(strategy definition, parameters, ticker set, dates,
   cost model, data version).** The demo, the stock pages and popular runs are
   pre-computed after each nightly load.
6. **The modular monolith first, not microservices.** Split `main.py` into
   domain modules (`auth`, `billing`, `backtests`, `validation`, `strategies`,
   `data`, `admin`) behind `/api/v1`. A one-person team cannot run ten services,
   and does not need to at this load.
7. **A typed contract.** OpenAPI generates the front end's client, so a
   backend change that breaks the UI fails in CI, not in production.
8. **Strategies as data, not code.** A rule is stored as JSON (indicators,
   comparisons, entry/exit, sizing) and checked against a schema. The engine
   reads it the way it reads the 3 strategies today. This is what turns the
   product from "3 demos" into "your idea".

**Service levels (SLOs) to hold:**

- API availability 99.9% a month.
- Cached backtest p95 under 300 ms.
- Uncached single-stock backtest p95 under 2 s.
- Validation finished within 2 minutes for 95% of jobs.
- The nightly data load finished by 06:00 IST.

## 5. Roadmap

Each phase ends on a gate. A phase that fails its gate is reworked, not skipped.

### Phase 0: foundations (about 2 weeks; no new features)

- Staging environment (Cloud Run, a separate Firebase project, Vercel preview)
  and a promote-to-production step.
- Split `main.py` into domain modules behind `/api/v1`, keeping old routes as
  aliases. Behaviour unchanged, all tests green.
- Product analytics: a funnel from landing → signup → first backtest →
  validation → return visit (PostHog or similar, cookieless where possible).
- A load-test baseline (k6 or Locust) against staging, with the numbers
  recorded.
- SLO dashboards and alerts for the targets above.
- ADRs written for the data vendor, Postgres and the queue.
- **Gate:** staging deploys automatically, and the load test and funnel both
  report real numbers.

### Phase 1: data and compute platform (about 4–6 weeks)

- Licensed EOD data for every NSE stock and index, ingested nightly to
  versioned Parquet. Index membership history (fixes survivorship bias for
  every user, not only in the study).
- Corporate-action adjustment done by us, tested against the vendor's figures.
- Result cache in Redis; validation and index scans moved to Cloud Tasks +
  worker, with the UI showing job progress.
- Postgres for runs, strategies and quotas; a data migration from Firestore
  with a rollback plan.
- yfinance removed from production.
- **Gate:** the load test holds 20 backtests a second at the p95 targets on
  staging, and no request calls a data vendor.

### Phase 2: the product people come back to (about 6–8 weeks)

- **Strategy builder:** a no-code rule composer (e.g. "RSI(14) < 30 and close
  > SMA(200)", with entry, exit, stop and sizing). Ten to fifteen common
  indicators to start.
- **Index scan:** run one rule across the Nifty 50, 100 or 500 at once and see
  where it held and where it failed. This is the funnel from the study, turned
  into a feature.
- **Indian costs:** brokerage, STT, exchange fees, GST, stamp duty, and
  short-term versus long-term capital gains on results.
- Saved strategies, watchlists, and **end-of-day alerts** when a saved rule
  fires (email first).
- Onboarding: three templates and a guided first test.
- **Payments:** Razorpay (UPI, cards) with GST invoices; entitlements from the
  existing `plans.py`; Vercel moved to a commercial plan.
- **Gate:** 100 weekly active testers who are not friends, week-4 retention of
  at least 15%, and the first paying users. If the gate fails, talk to users
  before building more.

### Phase 3: scale and growth (ongoing)

- Mobile-first polish and an installable app (PWA); Hindi.
- Public strategy pages people can share. The SEO pages already built feed
  into this.
- Raise limits under budget alerts; a read replica; a CDN for heavy public
  results.
- Paper trading against live end-of-day prices, then (only after legal review)
  broker connections for importing a portfolio.
- **Gate:** 10,000 weekly active testers, with cost per active user known and
  covered by revenue.

## 6. Cost, rough (to be confirmed per vendor)

| Item | Now | At Phase 2 | At 100k users |
|---|---|---|---|
| Hosting (Cloud Run, Vercel) | ₹0 | ₹2–4k a month (Vercel Pro included) | ₹10–25k |
| Postgres + Redis | none | ₹4–8k | ₹15–30k |
| Licensed EOD data | ₹0 (unlicensed) | ₹2–15k, depending on vendor and licence | the same, or a redistribution licence (higher) |
| Analytics, email, errors | ₹0 | free tiers | ₹3–8k |
| Legal review (one-off) | none | ₹25–75k | none |

These are estimates, not quotes. At ₹999 a year for Pro, about 300 paying users
cover Phase 2's running costs.

## 7. Risks, worst first

1. **No one returns.** This already happened with the 5 testers. Mitigation:
   the Phase 2 gate, user conversations every week from Phase 0, and alerts as
   the reason to return.
2. **Regulation.** SEBI regulates investment advice and research and has
   tightened rules on showing past or expected returns of trading strategies
   and on "finfluencers". Finertia must stay a tool that tests the user's own
   rules: no recommendations, no tips, no "this strategy returns X%"
   marketing. A lawyer reviews the product and the terms before payments go
   live. The DPDP Act 2023 governs personal data: a privacy notice, consent,
   and deletion (already built).
3. **Data licence.** Displaying or redistributing exchange data can need a
   licence beyond a vendor's API terms. This is checked in the vendor
   decision, not after launch.
4. **One person.** The author's time is the scarcest input (decision 5 says 3
   hours a week). Claude writes and tests the code; the author decides, tests
   by hand, and talks to users. Phases are sized so every week ends with
   something merged and deployable.
5. **A big rewrite.** The plan grows the existing code (modules, then a
   worker, then Postgres) with tests green at every step. Nothing is thrown
   away.

## 8. Decisions from the author

**Decided 24 Nov: all seven defaults, as written below** (DECISIONS 24 Nov).

| # | Decision | Default, now decided |
|---|---|---|
| P1 | Market and user | Indian retail traders first |
| P2 | Monthly budget you can spend from Phase 1 | ₹10k a month, revisited at the Phase 2 gate |
| P3 | Data vendor | Claude compares 3–4 on licence, coverage and price; you choose |
| P4 | Payments | Razorpay first, Stripe later for users outside India |
| P5 | Legal review before charging | Yes, before Phase 2's payments go live |
| P6 | Hours a week you can give | At least 5: decisions, testing, and two user calls a week |
| P7 | Pricing | Free tier kept; Pro at ₹199 a month or ₹999 a year, tested later |

## 9. What stops or changes

- Search and outreach work pauses (DECISIONS 24 Nov). The articles stay live,
  and the 10 Dec counts are still taken for the record.
- "Maintenance only" (DECISIONS 31 Oct) ends.
- Research studies continue only when they feed a feature, as the index scan
  does.
