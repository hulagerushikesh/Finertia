# Product plan: build it like a product, stay a personal project

_24 Nov 2026, revised the same day after the author's correction (DECISIONS 24 Nov,
"Personal project, Yahoo data, engineering first"). Written for the author, as a
staff engineer would write it: honest about where the project is, built to an
engineering standard that could carry many users, and kept inside the law for
what it is today, a free, non-commercial personal project._

## 0. The frame, set by the author

- **Status: personal project, not an enterprise application.** Free to use, no
  money taken, no paid plan offered.
- **Data: Yahoo Finance via yfinance**, US stocks first, Indian stocks (NSE
  `.NS`, BSE `.BO`) as Yahoo carries them. Yahoo's data is for personal,
  non-commercial use, which is the reason the project stays non-commercial.
- **No budget decisions yet.** Running cost stays about ₹0 while idle. Spending,
  licensed data, payments and a lawyer are for later, when the project is in a
  strong position and the author decides.
- **Focus: engineering and building.** The author's own part (decisions, money,
  outreach) comes once the product is strong.
- **Never break a law or a data provider's terms.** Section 6 is the standing
  checklist.

## 1. Where we are, honestly

**Strong, and worth keeping:**

- **A correct engine.** It closes lookahead bias by design and charges costs on
  turnover. 859 backend tests back it, and every published figure is re-run by
  a script.
- **Statistics no retail tool has.** Walk-forward testing, a shuffle test for
  timing luck, Deflated Sharpe, PBO, whole-grid tests (Reality Check, SPA,
  Romano-Wolf), and a confidence interval on every number.
- **Sound operations for its size.** CI, a deploy workflow, Sentry, uptime
  alerts, Firestore backups with restore drilled, a dedicated service account.
- **A working front end.** Dashboard, portfolio, comparison, history, sharing,
  a demo, 60 pre-rendered public pages, and six articles.
- **Code split by domain since 24 Nov** (#214): ten routers behind `/api/v1`.

**What still reads as a personal project, and is engineering work:**

| Area | Today | Target |
|---|---|---|
| What a user can test | 3 fixed strategies | Their own rules: indicators plus conditions, no code |
| Data path | Yahoo fetched during requests, cached in Firestore | Yahoo data kept in our own store, refreshed by a nightly job; requests never wait on Yahoo |
| Compute | Every backtest and validation inside the request; max 2 instances | Heavy jobs on a queue and a worker; repeated results from a cache |
| Environments | Production only | A staging copy and a promote step |
| Contract | Hand-written client | OpenAPI-generated client; a breaking change fails CI |
| Reasons to come back | None | Saved strategies, watchlists, end-of-day alerts |
| Knowing what works | Page views only | A cookieless funnel: visit → signup → first test → return |

## 2. What many users would mean, in numbers

| Assumption | Value |
|---|---|
| Active on a busy day | 10,000 |
| Backtests per active user | 5 → 50,000 a day; bursts of about 20 a second |
| Validations | about 1,000 a day |

- An uncached backtest is about 0.5 s of one CPU, so a burst of 20 a second is
  about 10 CPUs before caching. A backtest is deterministic, so a cache keyed by
  inputs and data date removes most of that.
- A validation is 5–30 s of CPU. It belongs on a queue, never in a request.
- Daily bars for a few thousand US and Indian stocks over 20 years are well
  under 1 GB.

**Conclusion:** compute is not the hard part. The engineering work is a data
path that never waits on Yahoo, heavy jobs off the request path, and a product
people come back to. Yahoo's informal limits are the real ceiling. They are a
reason to cache hard and pre-fetch at night, and a reason the project stays
small and personal until it moves to licensed data.

## 3. The product

- **For:** people who want to test a trading idea on US or Indian stocks before
  risking money; students and quant candidates who want to learn honest
  testing.
- **The job:** "Tell me whether my rule would have worked, after costs, and
  whether that was luck."
- **Core loop:** build a rule → test it on one stock → test it across an index
  (S&P 500 names, Nasdaq-100, Nifty 50) → validate it → save it → come back
  when something changes.
- **Never:** tips, predictions, "buy this", or claims of future returns. It
  tests the user's own rules on past data.

## 4. Target architecture (no paid services required)

```
Browser ──► Vercel CDN: static app + pre-rendered public pages
   └─ /api/v1 ──► Cloud Run "api" (stateless FastAPI)
                    ├─► Firestore: users, runs, strategies, alerts (as today)
                    ├─► Price store: Parquet files on Cloud Storage, one set per
                    │     nightly load, read with DuckDB/Polars in the instance
                    ├─► Result cache: in-instance LRU first, Firestore-backed later
                    └─► Cloud Tasks ──► Cloud Run "worker": validations, index scans
Nightly (Cloud Scheduler): fetch the day's Yahoo closes for the tracked universe
   → check them → write a new data version → pre-compute popular results
```

Decisions behind it:

1. **One data version per night.** Every result names the data date it used, so
   a cached result stays valid until the next load, and requests never call
   Yahoo for the tracked universe. Tickers outside it still fall back to a live
   fetch with today's limits.
2. **Firestore stays the database.** It is free at this size and already
   backed up. Postgres is a later decision with its own cost.
3. **API and worker are the same code, deployed twice.** The engine stays a
   package with no web or database imports.
4. **A modular monolith, not microservices.** One person cannot run ten
   services, and this load does not need them.
5. **Strategies as data.** A rule is JSON (indicators, comparisons, entry/exit,
   sizing), checked against a schema, read by the engine the way it reads the 3
   strategies today.
6. **Typed contract.** OpenAPI generates the front end's client.

## 5. Roadmap: engineering first

### Phase 0: foundations (in progress)

- ✅ `main.py` split into domain routers behind `/api/v1` (#214).
- Non-commercial mode: no paid plan shown anywhere; charging blocked in code;
  disclaimers, data attribution, privacy notice and terms on the site
  (section 6).
- Staging: a second Cloud Run service and Vercel previews pointed at it, on the
  free tiers.
- OpenAPI-generated front-end client.
- A load-test script (Locust) run against staging, numbers recorded.
- **Gate:** staging deploys automatically and the load test reports real
  numbers.

### Phase 1: data and compute platform

- Nightly Yahoo load for a tracked universe (S&P 500, Nasdaq-100, Nifty 50,
  Nifty Next 50) into versioned Parquet; checks for gaps and bad splits.
- Result cache; validations and index scans on Cloud Tasks with a worker, and
  progress shown in the UI.
- **Gate:** no request for a tracked ticker calls Yahoo, and a burst of 20
  backtests a second holds on staging.

### Phase 2: the product people come back to

- No-code strategy builder (10–15 common indicators to start).
- Index scan: one rule across an index, where it held and where it failed.
- Costs per market: US (commission-free, SEC and FINRA fees) and India
  (brokerage, STT, exchange fees, GST, stamp duty).
- Saved strategies, watchlists, end-of-day email alerts.
- Onboarding with templates.
- **Gate:** people who are not friends return in week 4.

### Later, only on the author's decision

- Licensed data, payments, a legal review, a budget, mobile app, broker links.
  Going commercial needs all four of the first items together.

## 6. Legal and terms: the standing checklist

Not legal advice. This is what the code and the site must keep true, and it is
re-checked whenever a feature touches money, data or advice.

| Rule | What it means here | Status |
|---|---|---|
| Yahoo / yfinance terms: personal, non-commercial use | No fees, no paid plan, no ads, no selling of data. Show results derived from prices; no bulk download of raw price data. Say where the data comes from and that we are not affiliated with Yahoo | Fixed by the non-commercial change (Phase 0) |
| Vercel Hobby plan: non-commercial only | Same as above | Kept while nothing is sold |
| India, SEBI (investment advisers, research analysts) | No advice, no recommendations, no tips, no claims of future returns; say "not SEBI-registered". Hypothetical past results always labelled as such | Footer and research notes say so; extended to every page |
| US, SEC and FINRA (investment advisers) | Same posture: a general-purpose educational tool, not personalised advice; say "not a registered investment adviser" | Added to the footer |
| India, DPDP Act 2023 (personal data) | A privacy notice saying what is stored and why; access and deletion | Export and deletion built; privacy notice added |
| Other users' privacy (GDPR/CCPA-style expectations) | Minimal data: email, runs, usage counts; no tracking cookies; analytics cookieless | Kept |
| Payments | No payment code reachable. Charging needs licensed data, a lawyer, and the author's decision first | Blocked in code |

## 7. Decisions

**Settled on 24 Nov by the author:** a personal, non-commercial project; Yahoo
data, US first and then Indian; budget, payments, licensed data and legal
review deferred; engineering first. The first version of this plan's P1–P7
choices (Indian retail first, ₹10k a month, Razorpay, ₹199 Pro) are withdrawn.

**Open, and not needed now:** when (and whether) to go commercial.
