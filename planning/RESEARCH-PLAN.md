# Research study — "How many Nifty strategies survive honest testing?"

Chosen by the author on 3 Nov 2026 (studies 1 and 2 of the options offered
that day, run as one). Research, not building: no deploys, no production
change, no new product surface until the write-up is done. The output is a
second essay next to `/writeup`, and a script that reproduces every figure in
it, the way `reproduce_writeup.py` does for the first.

## The two questions

1. **Breadth.** Take Finertia's three strategies (momentum, MACD, Bollinger)
   across the Nifty 50, after costs, tuned on one period and judged on years
   they never saw. How many beat buy-and-hold, and how many of those survive
   the luck checks?
2. **Self-deception.** On one stock, try hundreds of parameter combinations
   and pick the best, the way a person tuning by hand would. How good does the
   winner look in-sample, and how much of it do the checks take away?

Question 2 explains the answer to question 1: if most "winners" in 1 vanish,
2 shows the mechanism on one stock where it can be watched.

## Method

Everything below already exists in `backend/`; the study adds a driver
script and the universe list, not new statistics.

| Step | Tool | Reads |
|---|---|---|
| Prices | `data.py` (Yahoo via yfinance, adjusted daily closes) | 2011–2025 |
| Costs | `costs.py`, at the product's default and at 2× and 0.5× | does the answer move with the cost |
| Out of sample | walk-forward (`validation.py`) | tuned years vs unseen years |
| Luck, per stock | permutation test, Deflated Sharpe (`deflated.py`), PBO (`pbo.py`) | is the winner better than chance given how many were tried |
| Trials counted honestly | `trials.py` (effective number of independent trials) | so the Deflated Sharpe bar is not overstated |
| Luck, across the grid | Reality Check and SPA (`snooping.py`) | does *anything* beat buy-and-hold once the whole search is in the test |
| Regimes | `regimes.py` | does a survivor only work in one kind of market |

The headline number is a funnel: **50 stocks × 3 strategies → beat
buy-and-hold in-sample → still ahead out of sample → pass the luck checks**.
Each step is reported with its count, not just the end.

## Survivorship: the trap to state up front

Today's Nifty 50 is the list of companies that did well enough to be in it
today. Testing them back to 2011 tests winners chosen with hindsight, which
flatters buy-and-hold and every long-only rule.

- **Main universe:** the Nifty 50 members as of the start date, from NSE's
  published index changes, held for the whole period.
- **Stocks Yahoo no longer has** (delisted or merged) are listed by name with
  the reason, not silently dropped. If more than a handful are missing, the
  write-up says what that does to the result.
- **Comparison run** on today's list, reported beside the main one, so the
  size of the bias is a measured number rather than a caveat.

## Pre-registration

The thresholds are fixed here, before any run, so the result cannot shape
them:

- "Beats buy-and-hold" means a higher Sharpe after costs.
- "Survives" means ahead out of sample **and** permutation p < 0.05 **and**
  Deflated Sharpe probability > 0.95 **and** PBO < 0.5.
- The parameter grid is the product's existing grid, unchanged. Question 2's
  bigger grid is stated in full before it runs.
- Any change to these after the first run is recorded in DECISIONS.md with
  the reason, and the original reading is reported too.

## Timeline (about 2 weeks part-time)

| Week | Work | Done when |
|---|---|---|
| 1 | Universe list and missing-stock table; driver script; question 1 run, main and comparison universes | the funnel table exists and re-runs identically |
| 1–2 | Question 2 on one stock (chosen before the run, the most liquid on the list) | in-sample vs out-of-sample chart, and what each check said |
| 2 | Write-up draft; reproduce script checks every figure; author reads it | the author's yes to publish |

## What it is not

Not investment advice and not a claim that any rule will work. A null result
("almost nothing survives") is a result, and is published as one. Yahoo's
data is not licensed for commercial use (DECISIONS 13 Oct), which is fine for
a free essay and is stated in it.

## Open for the author

- Publish as a page on finertia.hulage.in, a post elsewhere, or both: decided
  at the draft, not now.
