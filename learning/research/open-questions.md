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
Options: rolling (anchored) walk-forward with multiple splits; report OOS per
calendar year; a simple regime label (realised-vol tercile) with per-regime Sharpe.

## 4. Whole-grid inference instead of winner inference

DSR corrects the *winner*. White's Reality Check / Hansen's SPA / Romano-Wolf
test the *whole grid* against the benchmark in one bootstrap. Would replace the
permutation test with something that handles N candidates and gives "which
cells survive" rather than "does the best cell survive".

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

Item 3 is the one that changes what the product can *claim* — the flip above is the evidence. Start there.
