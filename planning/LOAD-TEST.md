# Load test: one API process (Phase 0)

_27 Nov 2026. Script: `backend/scripts/load_test.py`. Re-run it after any change
to the engine, the statistics on the results card, or the response shape._

## How it was measured

- The real app (every route, middleware and the engine) runs in one uvicorn
  process, as one Cloud Run instance does.
- Auth and Firestore are the offline fakes. Prices are synthetic, 10 years per
  ticker, already in memory, so this is the **warm-cache ceiling**. Yahoo is
  never called: load-testing it would break its terms and measure Yahoo, not us.
- Requests are 10-year backtests across 8 tickers and 3 strategies, then
  validations.
- Machine: the author's Mac (Apple silicon, Python 3.12). One Cloud Run vCPU is
  slower, so treat these as an upper bound.

## Results (after the gzip change below)

| Scenario | In flight | Throughput | p50 | p95 |
|---|---|---|---|---|
| Backtest | 1 | 3.3 /s | 0.30 s | 0.32 s |
| Backtest | 5 | 4.3 /s | 1.18 s | 1.29 s |
| Backtest | 20 | 4.1 /s | 4.77 s | 5.44 s |
| Backtest | 40 | 4.0 /s | 9.76 s | 10.39 s |
| Validation | 1 | 2.5 /s | 0.43 s | 0.47 s |
| Validation | 4 | 2.6 /s | 1.42 s | 1.77 s |

No errors in any scenario.

## What it says

1. **One process tops out at about 4 backtests a second.** Past that, more
   concurrent requests only queue: latency grows in a straight line with the
   number in flight. The work is CPU-bound Python, so threads do not add
   throughput.
2. **Production queues up to 40 requests per instance** (`--concurrency 40`).
   At 40 in flight a user waits about 10 s here, and longer on one vCPU. With
   `--max-instances 2` the service tops out near 8 backtests a second.
3. **Where a backtest's CPU goes** (profiled, about 0.3 s each):
   - the bootstrap confidence intervals, about 0.13 s;
   - the Sharpe-difference test, about 0.11 s;
   - turning the result into JSON, about 0.03 s;
   - compressing it, which took 0.025 s and now takes 0.006 s after the change
     below.

   The engine itself is a small share.
4. **Validations are as cheap as a backtest on this data.** The 5–30 s seen in
   production in October was mostly price fetches and the database's distance
   from the server, which B1 removed. A queue for them is not urgent.

## Changes made from it

- **gzip level 9 → 6** (`main.py`). On a 10-year response this cuts the time
  from 25 ms to 6 ms, for 74 KB on the wire instead of 68 KB. Single-request
  p50 went from 0.34 s to 0.30 s.
- **Tried and dropped:** a vectorised bootstrap index generator. It produced
  identical indices, but it was no faster, because generating the random
  numbers is the real cost.

## What would move the ceiling (in order)

1. **A result cache** keyed by the request and the data's last date (Phase 1).
   A backtest is deterministic, so a repeated run skips its 0.3 s of CPU
   entirely. Popular set-ups and the example runs are most of the traffic.
2. **Lower `--concurrency`** (about 8) so Cloud Run starts a second instance
   before queues grow. This is free while `--max-instances` stays at 2. Raising
   the maximum is a spending decision for later.
3. **Fewer bootstrap replicates, or computing them lazily** (for example when
   the confidence intervals are opened). That would be a product decision: the
   intervals are deliberately on every result.
