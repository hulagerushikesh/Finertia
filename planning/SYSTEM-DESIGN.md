# System design review: scale and efficiency

_14 Oct 2026. Measured on the local emulator stack and read from 7 days of
production request logs. Nothing in production was changed to get these
numbers._

## The system today

```
Browser ──► Vercel (static app, CDN)
   │
   └─ /api/* ──► Vercel rewrite ──► Cloud Run finertia-api (asia-south1, Mumbai)
                                       1 vCPU, 512 MiB, concurrency 40, max 2 instances
                                       │
                                       ├─► Firestore (nam5, United States): users, runs,
                                       │     price cache, rate-limit counters
                                       ├─► Firebase Auth (token check, local after key fetch)
                                       └─► Yahoo Finance (yfinance) on a price-cache miss
```

One Python process per instance runs everything: auth, the backtest engine,
validation, history and admin queries.

## What the numbers say

**Production, 7–14 Oct (successful requests; small samples):**

| Route | n | p50 | p95 | max |
|---|---|---|---|---|
| `POST /api/backtest` | 22 | 2.5 s | 11.4 s | 19.1 s |
| `POST /api/portfolio` | 3 | 3.8 s | 6.0 s | 6.0 s |
| `GET /api/me/usage` (auth + one read) | 7 | 1.6 s | 7.9 s | 7.9 s |
| `GET /api/history` | 3 | 2.5 s | 3.5 s | 3.5 s |
| `GET /api/admin/stats` | 4 | 6.7 s | 6.9 s | 6.9 s |
| `GET /api/health` | 860 | 0.00 s | 0.01 s | 8.0 s |

**Local, emulators on the same machine (no network distance), warm:**

| Request | Time | Response |
|---|---|---|
| Backtest, AAPL 2015–2025 | 0.6 s | 447 KB (80 KB gzipped) |
| Validation, same | 0.5 s | 15 KB |
| Portfolio, 3 tickers | 0.3 s | 404 KB (75 KB gzipped) |
| 5 backtests at once | all finish at 2.9 s | |
| 20 backtests at once | p50 6.4 s, slowest 8.6 s | |
| Process memory | 91 MB after 12 requests, 182 MB after 20 concurrent | |

The engine itself is fast. Production is 4–5x slower than local because of
where the time goes, not because of the maths.

## Findings, worst first

### 1. One request at a time per instance

Every route is `async def`, and inside them the engine, the Firestore client
and yfinance are all blocking calls. In FastAPI that runs on the event loop,
so while one backtest computes **or waits on the database**, the instance
serves nothing else: not the health check, not a History page.

- Locally, 20 simultaneous backtests ran strictly one after another (slowest
  waited 8.6 s for 0.4 s of work).
- In production it is worse: each backtest waits on about five database round
  trips (finding 2), and the CPU sits idle during those waits too.
- Cloud Run is set to send up to 40 requests to one instance, so the 40th
  waits behind 39.

### 2. The API and the database are on opposite sides of the world

Cloud Run is in Mumbai; Firestore is nam5 in the United States, roughly a
quarter of a second away per round trip. The code already knows (the rate
limiter was written to need one trip instead of three). A backtest makes
about five trips in sequence:

| Step | Trips |
|---|---|
| Read the user's profile (auth) | 1 |
| Shared rate-limit counter | 1 |
| Price cache, unless in memory | 1 |
| Save the run | 1 |
| Update the usage counters | 1 |

That is about 1.2 s of waiting before any compute, which matches the
production p50. `/api/me/usage` doing one read in 1.6 s points the same way.
Confirming it needs per-step timings from production (plan step 1).

### 3. History reads every run the user has ever made

`GET /api/history` streams all of the user's run documents, counts them and
slices the page in Python. A user with 2,000 runs costs 2,000 reads and a
multi-second wait every time they open History. Firestore bills per document
read, so this one grows with usage in both time and money.

### 4. Responses are sent uncompressed

A backtest is 447 KB of JSON, 80 KB gzipped. The API adds no compression.
Production logs show ~157 KB median, which suggests nothing on the way
compresses it either (not verified end to end). On a phone connection that is
seconds.

### 5. The in-memory price cache never shrinks or expires

`data.py` keeps every (ticker, start, end) frame it has served in a plain dict
for the life of the instance. Every new date range is a new entry, and the
instance has 512 MiB. A busy instance eventually runs out of memory and
restarts. Entries also never expire, so a long-lived instance can serve a
current-year range older than the six-hour freshness rule the L2 cache keeps.

### 6. Many users asking for the same new ticker all call Yahoo

There is no "one fetch in flight per ticker". Ten users opening the same
uncached ticker make ten downloads and ten rewrites of its cache. Yahoo
throttles that pattern. The data sprint replaces Yahoo; this still matters
with a paid provider, which bills per call.

### 7. Smaller issues

- **A run with no profile document returns 500 after the run is saved.**
  `_record_run` uses `update()`, which fails when `users/{uid}` does not
  exist. Registration writes that document first, so users should not hit
  it, but if that write ever fails, every run fails while still being saved.
  Fix: `set(..., merge=True)`. Queued under the round rule (it does not stop a
  tester's run).
- **Admin pages are slow** (stats p50 6.7 s). Admin only, low priority.
- **Hard ceiling of 2 instances.** Deliberate, as a cost cap. Rough capacity:
  about 1–2 backtests a second in total today. That is plenty for the next
  few hundred users, but it is a wall, not a slope.
- **Vercel plan.** If the account is on Hobby, its terms are non-commercial;
  check before charging anyone.

## What to do

Most of the cost is in how requests wait, not in the engine. The fixes are
cheap, and most need no new infrastructure.

### Phase A: code only, no infrastructure change

Each step is its own PR with tests, and goes out in one backend deploy (after
your yes). Users see no change except speed.

| # | Change | Expected effect |
|---|---|---|
| A1 | ✅ (built, not yet deployed) **Measure.** Log per-step timings (auth, each database call, compute) on every request, plus a `Server-Timing` header | Confirms or kills finding 2 with production numbers before anything bigger is decided |
| A2 | ✅ (built, not yet deployed) **Stop blocking.** Run the engine and the blocking database/yfinance calls in worker threads. Concurrency stays at 40 for now: with the 2-instance cap, a lower value turns bursts into 429s instead of short waits; revisit with A1's numbers and when max-instances is raised | Health and History stay fast during a backtest; the CPU computes while other requests wait on the database |
| A3 | ✅ (built, not yet deployed) **Fewer round trips.** Also: a portfolio takes its N rate-limit slots in one check (was N trips) and fetches its legs' prices together; Compare reads its runs with one `get_all`. Save the run and update the counters in one batch; read the profile and hit the rate limiter at the same time | About 5 sequential trips → about 3, roughly 0.5 s off every backtest |
| A4 | **History by page.** Query only the page (`limit`), and get the total from a `count()` aggregation | Reads per visit go from "all runs" to 20 + 1 |
| A5 | **gzip** on JSON responses over 1 KB | Backtest 447 KB → ~80 KB on the wire |
| A6 | **Bounded price cache** (LRU, e.g. 200 entries, six-hour TTL) and one Yahoo fetch per ticker at a time | Memory stays flat; no duplicate downloads |
| A7 | ✅ (built with A3, not yet deployed) `_record_run` with `set(merge=True)` | Removes the 500 in finding 7 |

**Reading A1's numbers.** Every request log line carries `timings_ms` (one
entry per step: `auth`, `profile`, `ratelimit`, `prices_read`,
`prices_fetch`, `prices_write`, `run_write`, `user_write`, `allowance`,
`history_read`, `run_read`, `export_read`, `delete`, `admin_query`),
`timing_counts` for steps that ran more than once, and `instance_request`
(1 = the instance's first request, so a cold start). The same steps come back
to the browser as a `Server-Timing` header, plus `other` (everything outside
a named step, mostly the computation) and `total`. Backtests after a day of
use:

```bash
gcloud logging read 'resource.labels.service_name="finertia-api" AND jsonPayload.message="request" AND jsonPayload.path="/api/backtest"' --freshness=1d --format='value(jsonPayload.duration_ms,jsonPayload.timings_ms)' --project=momentbacktracking
```

### Phase B: put the API and the database in the same place (decision for you, after A1)

| Option | Effect | Cost |
|---|---|---|
| **B1. Move Cloud Run to the US**, next to nam5 | Database trips become ~2 ms each. Users in India pay one long trip per request (Vercel → US) instead of ~five | Small: one deploy to a new region, update the Vercel rewrite, keep Mumbai as rollback. No data moves |
| **B2. New Firestore database in Mumbai**, migrate the data | Best latency for users in India, and their data stays in India (helps the DPDP conversation with counsel) | Bigger: export/import, a short write freeze, rules and indexes redeployed, backups and alerts re-pointed. Firebase Auth is unaffected |
| B3. Leave it | — | Every request keeps ~1 s of trans-Pacific waiting |

Recommendation: do A1–A3 first. If A1 shows the database trips dominate
after A3, pick B1 for speed now, or B2 if data residency in India matters for
the legal side. That second question needs counsel, so B1 is the safer
first move.

### Phase C: when there is real traffic (not now)

- **Cache results by parameters.** A backtest is deterministic: the same
  ticker, dates and parameters give the same answer. Every new user running
  the three example strategies could be served from a cache.
- **Validation off the request path** (a queue and a worker, e.g. Cloud
  Tasks) once free validations are on and heavier checks arrive, so a slow
  validation never holds an API instance.
- **Raise `max-instances`** with a budget alert, instead of the hard cap of 2.
- **Licensed data provider** (the data sprint): Yahoo is the biggest external
  risk to reliability at scale.

## Capacity, rough

| Users active in a day | Status after Phase A |
|---|---|
| Today (single digits) | Fine either way |
| ~100 | Fine; today's blocking would show at busy moments |
| ~1,000 | Needs A2–A4 and probably B1/B2; max-instances raised |
| 10,000+ | Phase C: result cache, worker queue, licensed data |

These are estimates from the measurements above, not load tests against
production. A1 replaces them with real numbers.
