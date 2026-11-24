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

## Question 2, fixed before its run (4 Nov 2026)

- **Stock:** RELIANCE.NS. "Most liquid" means the highest median daily
  traded value (close × volume) over 2011–2025 among the 2011 list; Reliance
  is first at about ₹749 crore a day, ahead of ICICI Bank (₹625 crore) and SBI
  (₹590 crore). Chosen on liquidity alone, before any strategy was run on it
  for this question.
- **Period, cost, split:** as question 1. 2011-01-01 to 2026-01-01, the
  default cost (0.1%), and the first 70% for tuning.
- **Grid, 834 combinations in all** (first written as 830, a miscount of the
  MACD pairs found when the script asserted the sizes; the values below are
  unchanged):
  - Momentum, 480: lookback 5, 10, 15, 20, 30, 40, 60, 80, 100, 120, 150,
    200 × trend average 10, 20, 30, 50, 75, 100, 150, 200, 250, 300 ×
    threshold 0, 0.01, 0.02, 0.05.
  - MACD, 284: fast 3, 5, 8, 10, 12, 15, 19, 25 × slow 10, 15, 20, 26, 30,
    39, 50, 60, 80, 100 (only where fast < slow) × signal 5, 9, 12, 15.
  - Bollinger, 70: window 5, 10, 15, 20, 25, 30, 40, 50, 75, 100 × width
    1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0.
- **The hand-tuner's pick:** the single best in-sample Sharpe across all 834.
  It is scored on the unseen years, its Deflated Sharpe is computed with
  N = 834, and the permutation test is run on the pick's own positions. PBO
  and the whole-grid tests run per strategy, on that strategy's part of the
  grid.
- **Beside it:** the same stock on the product's small grid, from question 1,
  so the effect of trying more is a number.
- Question 1 ran the permutation test the way the product does, on the
  default parameters rather than the walk-forward's pick. Question 2 tests
  the pick. The write-up says so.

## Follow-up, fixed before its run (4 Nov 2026)

The write-up named two flaws in the timing test. This re-run fixes both,
in the study only; the product's own test is unchanged.

- **The pick, not the defaults.** For every row of question 1 (both lists,
  all three costs), the timing test is re-run on the positions of the
  walk-forward's chosen parameters, over the full period, as question 2 did.
- **Shuffling whole holding runs.** Beside the product's day-by-day
  shuffle, a second version cuts the positions into runs of unchanged
  position and shuffles the order of the runs. Each run keeps its length,
  so a shuffle trades about as often as the real strategy (a little less
  when two runs of the same position end up side by side), and higher
  costs no longer penalise the shuffles more than the real one. 500
  shuffles, seed 42, as the product.
- **Survives** is re-counted with the run-shuffle on the pick in place of
  the old timing test; the other checks are as before. Both old and new
  counts are reported.
- **What would show the fix worked:** the number of pairs passing the
  timing test should no longer rise steeply with cost. If it still does,
  the write-up says so.

## Study 3: do the survivors hold on 2026? Fixed before its run (24 Nov 2026)

Chosen by the author on 24 Nov (PLAN part 4, candidate 1; DECISIONS 24 Nov).
The question: the funnel ended on a handful of pairs that passed every check
on 2011–2025. Do they still beat holding the stock on 2026, which no part of
the study has seen?

- **What was seen before this was written.** Only a data check: Yahoo has
  220 daily bars from 2026-01-01 to 2026-11-23 for each of the five stocks,
  and their counts of zero-volume days. No strategy, Sharpe or price change
  for 2026 was computed or looked at.
- **Data.** Yahoo adjusted daily closes, through the close of 2026-11-23,
  the last close before this plan. Later days are not added. Signals are
  built over 2011-01-01 to 2026-11-24 so the indicators have their history,
  and only 2026 returns are scored (equity rebased at the first 2026 close).
- **Settings frozen.** Each pair uses the parameters its walk-forward chose
  in the published funnel (`nifty-funnel.json`). Nothing is re-tuned.
- **Main pairs, five:** the four 2011-list survivors at the default cost
  (Reliance Communications momentum and MACD, Reliance Infrastructure MACD,
  Reliance Power MACD) and today's list's one survivor (Adani Enterprises
  momentum).
- **"Held"** means a higher 2026 Sharpe after costs than holding the same
  stock over 2026, at the default cost (0.1%).
- **How to read the count.** With no edge at all, each pair is a coin flip
  against holding. All four 2011 survivors ahead would happen by luck about
  1 time in 16; 3 of 4 happens about 1 time in 3. So the result reads "the
  survivors held" only if all four 2011 survivors are ahead; anything less
  reads "no sign that they held". The two Reliance Communications pairs share
  one stock, so they are not two independent flips, and the write-up says
  so. Adani Enterprises is reported beside them, not counted in.
- **The mechanism, stated before the run.** The study found that the 2011
  survivors won by being out of the market while their stocks collapsed. If a
  stock rose in 2026, a rule that is often in cash should lag holding it. Each
  stock's 2026 buy-and-hold return is reported next to its result so this can
  be checked.
- **Tradeability.** Zero-volume days in 2026 are counted per stock. A pair
  with more than 20 is flagged as not tradeable as tested (Reliance
  Infrastructure has 74 in the data check), and its result is reported but
  marked.
- **Reported beside, not part of "held":**
  - the run-shuffle timing test (500 shuffles, seed 42, as in the
    follow-up) on the 2026 positions alone, at p < 0.05;
  - the five pairs at half and double cost.
- **Breadth check, all 129 pairs on the 2011 list at the default cost.**
  Each pair is scored on 2026 with its frozen settings. Two numbers: how many
  are ahead of holding in 2026, and the rank correlation (Spearman) between
  each pair's lead over holding in the unseen years (2021–2025) and its lead
  in 2026. The p-value is one-sided, from 10,000 shuffles of the 2026 leads,
  seed 42. p < 0.05 with a positive correlation reads "the funnel's ranking
  carried over into 2026"; otherwise it did not.
- **Sample size, said now.** About 0.9 of a year is a short window: a
  single pair's Sharpe over 220 days has a standard error near 1. One
  pair's result is weak evidence either way, and the write-up says so.
- **Output.** `backend/scripts/nifty_2026.py` writes
  `planning/research/nifty-2026.json`, and `--check` re-runs it. Whether the
  result goes on the site as a section of `/writeup/nifty-50` or as its own
  page is the author's call at the draft. It is not advice, and a null result
  is published as one.

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
