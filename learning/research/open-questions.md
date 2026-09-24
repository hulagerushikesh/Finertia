# Open questions

The research frontier of the project — what is known to be unsolved, in rough
priority order. Each says what "done" would look like.

## 1. ~~Effective number of trials~~ — done 15 Sep 2026 (`backend/trials.py`)

Both candidates built: eigenvalue (Li & Ji) and clustering (LdP & Lewis).
Headline takes the larger; both reported with the DSR under each. What is
left of this question: the two disagree by 2–3× on the shipped grids with
silhouettes ~0.25. Sharper grids (more cells, wider ranges) would let the
clustering speak; that is a grid-design question now, not a statistics one.

## 2. ~~Validation for portfolios~~ — decided and built 21 Sep 2026

~~Walk-forward and permutation are defined on a single position series, so the
tab is hidden in portfolio mode. What is a portfolio-level permutation — shuffle
each leg's timing independently, or shuffle the weight path? Each answers a
different null. Needs a definition before code.~~

**Decided**: shuffle each leg independently, weight path fixed — null = "no leg
can time its own market" (DECISIONS.md, 21 Sep). `backend/portfolio_validation.py`,
`POST /api/portfolio/validate`, 03-validation-methods §10. What is left: the
weight-path null (only meaningful for inverse-vol) is not built; rolling
walk-forward and regimes for a book are not built. The tab shows in portfolio
mode since 21 Sep.

## 3. Regime awareness

Walk-forward uses one split; CSCV cannot see a regime break by construction; the
vol CI fails coverage because regimes do not resample. Three symptoms, one cause.

**Measured 15 Sep 2026:** AAPL 2018→2024-01-01 says momentum fails, Bollinger
holds up. AAPL 2018→2025-01-01 — one more year, split moves from Feb to Oct
2022 — says the opposite. Same strategies, same grid. The single-split verdict
is a draw from a distribution of splits, and the product currently prints one
draw as if it were the distribution.
**Built 16 Sep 2026 — `backend/rolling.py`, learning/03 §7.** Anchored
rolling walk-forward, four folds, market return and realised vol beside each
fold, stitched OOS curve with a bootstrap interval, parameter-stability count.
On both AAPL windows every strategy reads `regime_dependent`; momentum's
"failed" was the one fold where the market fell (−15%, Apr 2022→Feb 2023)
and its winning parameters changed at every re-fit.

**Label built 16 Sep — `backend/regimes.py`, learning/03 §8.** Per-bar
realised-vol terciles, Sharpe per regime on every backtest and on the stitched
OOS record. AAPL OOS: momentum 2.26 calm / −0.76 turbulent, Bollinger the
mirror. Item closed as scoped.

~~Still open, narrower: the label is one-dimensional (vol). A trend/range label
(e.g. sign and strength of a 60-day return) would separate "calm and rising"
from "calm and flat", which is where momentum's calm-regime beta hides.~~
**Built 21 Sep — `label_trend` / `trend_breakdown` / `joint_breakdown` in
`regimes.py`, DECISIONS 21 Sep.** Trend = t-statistic of the trailing 60-day
mean return, cut at ±1σ (`down` / `flat` / `up`), crossed with the vol
tercile into a 3 × 3 grid. The hypothesis was wrong in an instructive way:
momentum's calm-regime Sharpe on AAPL out-of-sample is 2.40 in calm-*flat*
bars and 2.29 in calm-rising — the calm edge is not beta in disguise. What the
grid does separate is the turbulent third: momentum reads −1.88 in
turbulent-flat (whipsaw, 199 bars) and +1.29 in turbulent-rising (84). The
vol label alone blamed all turbulence; the loss is chop, not volatility.
Bollinger's turbulent edge is the same cell read the other way: +2.19 in
turbulent-flat, −1.01 in turbulent-rising. Still open: the vol-CI coverage
failure (§5) — regimes do not resample.

## 4. ~~Whole-grid inference instead of winner inference~~ — done 20 Sep 2026 (`backend/snooping.py`)

All three built on the candidate matrix walk-forward already has: Reality
Check, SPA (lower / consistent / upper), Romano-Wolf stepdown with a
per-cell adjusted p. Benchmark is buy-and-hold on the same bars. On every
run tried (AAPL both windows, INTC, BABA, T, PYPL; three grids) not one cell
survives at 5%, and the snooping gap is visible in every table. What is left
of this question: (a) the benchmark — against *zero* rather than buy-and-hold
the test would say whether the grid makes money at all, a different and
weaker claim; (b) it did not replace the permutation test, it sits beside
it — permutation is about timing at fixed exposure, this is about level;
(c) surfaced in the UI on 21 Sep (PR #40: a sixth verdict check and the per-cell stepdown table).

## 5. ~~Max-drawdown interval~~ — **closed 23 Sep 2026**

79% coverage at nominal 95%. All three options listed here — longer blocks for
path statistics, a parametric drawdown distribution (AFML ch. 15), or an honest
one-sided bound — were attempts to fix a band that was too NARROW. It was not.
Measured against the true sampling distribution the band was the right width
(0.2204 against a central-95% range of 0.2255, 98%) and the estimator was
unbiased. The defect was BCa's own bias correction: `z0` reads the share of
replicates below the observed statistic as estimator bias, and for a drawdown
that share is set by the block scheme rather than by the estimator.

The damage is mostly noise rather than drift — `z0` has mean ≈ 0 but sd
0.44–0.63, so each run got a large *random* shift. Suppressing it and keeping
the acceleration takes coverage 79% → 95.0%, holding on Gaussian GARCH, GARCH
t(5) and Markov regime-switching. `calmar_ratio` is treated the same way.
DECISIONS 23 Sep; `NO_BIAS_CORRECTION` in `backend/bootstrap.py`.

Worth recording how the original note went wrong, because it is the failure this
file exists to prevent: it named a real mechanism (blocks cannot rebuild long
declines) and asserted a consequence nobody measured (the band is "optimistic
about long, slow declines"). The band was in fact *pessimistic* — dragged deep.
A plausible mechanism is not a measurement.

## 6. Survivorship-free data

Not fixable on yfinance. If a paid or point-in-time source is ever added, the
first research task is re-running the canonical AAPL demo on a delisted-inclusive
universe and reporting how much of the buy-and-hold benchmark was survivorship.

## 7. ~~Transaction-cost realism~~ — **closed 24 Sep 2026**

"A vol-scaled cost model is one line; deciding the coefficient is the
research." The research says there is no coefficient to decide, and that it
would not matter if there were.

It cannot be measured. With only daily OHLCV the coefficient has to come from
a high-low spread estimator, and on a simulation whose true spread is CONSTANT
those estimators report a vol slope of 0.23 to 1.07 — because when the spread
is small next to daily vol they return their own noise floor, which is itself
proportional to vol. Real tickers give 0.73-1.03, inside the range a constant
spread produces. Corwin-Schultz yields no number at all in 69-96% of months.

It would not matter. Holding the TOTAL cost paid fixed and changing only where
the charge lands moves Sharpe by at most 0.015 across three strategies and
eight tickers, even at k=3 or with a 5x crisis multiplier. The cost LEVEL
moves it by 0.16-0.32 per 10bps — about thirty times more. Redistributing a
fixed budget leaves the mean untouched by construction, so it can only reach
Sharpe through variance, which is second order. Pushed to the extreme it
finally bites, and in the wrong direction: concentrating cost inflates
variance and shrinks |Sharpe| toward zero.

So the level shipped instead: `costs.py` reports the breakeven cost and how
far the user's assumption is from it. See DECISIONS 24 Sep.

The item had the same shape as §5. It named a real mechanism — spreads do
widen with vol — and then asserted a consequence for the backtest that nobody
had measured. The mechanism was real; the consequence was not there.

## 8. Is the Sharpe gap on the page significant? — **closed 23 Sep 2026**

~~The dashboard prints the strategy's Sharpe beside buy-and-hold's and leaves
the reader to judge the gap by eye.~~ Built: `sharpe_test.py`, Ledoit-Wolf
(2008) on the paired series, HAC standard error and a studentised bootstrap,
two-sided, on every backtest and every portfolio run. What it found is the
part worth keeping: **none of the three strategies on AAPL, BABA or SPY has a
Sharpe gap against buy-and-hold that six years of daily bars can distinguish
from noise** — standard errors of 0.5 to 0.7, and the one significant result
(AAPL 2015→20 Bollinger, p 0.031) is a *loss*. The power table says why: about
a full point of Sharpe is needed over five years before the test will call it.
Still open beside it — the same test on the *rolling* stitched record rather
than the full period, where the sample is shorter still.

---

Item 3 is done as scoped (rolling folds + vol label); 2, 4, 5, 7 and 8 are
closed. 6 needs a paid survivorship-free source. Next: nothing unblocked at
zero cost — the queue is empty until 6 gets a data budget or a new question
arrives.
