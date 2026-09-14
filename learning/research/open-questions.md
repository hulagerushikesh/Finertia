# Open questions

The research frontier of the project — what is known to be unsolved, in rough
priority order. Each says what "done" would look like.

## 1. Effective number of trials (roadmap item 5 of 5)

**Problem.** `deflated.py` sets N = raw grid size (16/4/12). Neighbouring
parameters (lookback 20 vs 25) produce nearly identical return series, so the
true number of *independent* trials is smaller. Overstating N inflates SR* and
raises the bar — safe direction, but unmeasured, and it can call a real edge
noise.

**Candidates.**
- Eigenvalue method (Nyholt 2004 / Li & Ji 2005): N_eff from the spectrum of the
  candidate-return correlation matrix. Cheap; matrix already exists (§1 of 03).
- Clustering (López de Prado & Lewis 2019): cluster candidates by return
  correlation, N_eff = number of clusters. More faithful, more code.

**Done when.** `deflated.py` accepts `n_trials_effective`, the validation
response reports both raw and effective N with the DSR under each, a test pins
that a grid of identical candidates gives N_eff ≈ 1, and the panel shows the gap.

## 2. Validation for portfolios

Walk-forward and permutation are defined on a single position series, so the
tab is hidden in portfolio mode. What is a portfolio-level permutation — shuffle
each leg's timing independently, or shuffle the weight path? Each answers a
different null. Needs a definition before code.

## 3. Regime awareness

Walk-forward uses one split; CSCV cannot see a regime break by construction; the
vol CI fails coverage because regimes do not resample. Three symptoms, one cause.
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

Items 1 and 3 are the ones that change what the product can *claim*. Start there.
