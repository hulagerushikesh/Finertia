# Open questions

The research frontier of the project — what is known to be unsolved, in rough
priority order. Each says what "done" would look like.

## 1. ~~Effective number of trials~~ — done 15 Sep 2026 (`backend/trials.py`)

Both candidates built: eigenvalue (Li & Ji) and clustering (LdP & Lewis).
Headline takes the larger; both reported with the DSR under each. What is
left of this question: the two disagree by 2–3× on the shipped grids with
silhouettes ~0.25. Sharper grids (more cells, wider ranges) would let the
clustering speak; that is a grid-design question now, not a statistics one.

## 2. Validation for portfolios

Walk-forward and permutation are defined on a single position series, so the
tab is hidden in portfolio mode. What is a portfolio-level permutation — shuffle
each leg's timing independently, or shuffle the weight path? Each answers a
different null. Needs a definition before code.

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

Still open, narrower: the label is one-dimensional (vol). A trend/range label
(e.g. sign and strength of a 60-day return) would separate "calm and rising"
from "calm and flat", which is where momentum's calm-regime beta hides. And
the vol-CI coverage failure (§5) shares the cause — regimes do not resample.

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
(c) not surfaced in the UI yet (BACKLOG).

## 5. Max-drawdown interval

79% coverage at nominal 95%. Resamples preserve order only within a block.
Options: longer blocks specifically for path statistics; parametric drawdown
distribution (AFML ch. 15); or report it honestly as a one-sided bound.

## 6. Survivorship-free data

Not fixable on yfinance. If a paid or point-in-time source is ever added, the
first research task is re-running the canonical AAPL demo on a delisted-inclusive
universe and reporting how much of the buy-and-hold benchmark was survivorship.

## 7. Transaction-cost realism

Costs are a constant rate on turnover. Real costs scale with volatility and
inverse with liquidity. A vol-scaled cost model is one line; deciding the
coefficient is the research.

---

Item 3 is done as scoped (rolling folds + vol label). Next: whole-grid inference (4) or the max-drawdown interval (5).
