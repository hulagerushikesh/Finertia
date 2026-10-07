# The best in-sample strategy was the worst out-of-sample one — and then the window moved

_Draft 4, 7 Oct 2026. Every number below is reproducible on
https://finertia.hulage.in (Validate tab), and all 174 of them are re-run and
checked by `backend/scripts/reproduce_writeup.py`, last run 7 Oct 2026. The
main text is the argument; the appendices hold the per-check detail._

Most backtesting tools show you a winning strategy and let you believe it.
Finertia was built to argue back: every result goes through walk-forward
validation, a timing test, multiple-testing corrections and bootstrap
intervals. This is what happened when those checks were pointed at three
ordinary strategies on one stock — and the answer turned out to depend less
on the strategies than on where the test drew its line.

## The setup

One ticker, AAPL. Three strategies with nothing exotic about them: momentum
(price above its N-day moving average and rising over a lookback), MACD
crossover, and a Bollinger-band mean-reverter. Transaction cost 10 bp on
turnover. Each strategy has a small parameter grid — 16 cells for momentum,
4 for MACD, 12 for Bollinger.

Walk-forward validation optimises the grid on the first 70 % of the period,
then scores the winning cell on the remaining 30 %. A purge-and-embargo gap
(16 bars here) is cut around the split so the trade that straddles it cannot
earn on both sides. Only the out-of-sample number is evidence; the in-sample
number is what a backtest normally shows you.

## What the first window said

AAPL, 2018-01-01 → 2024-01-01, 1,509 bars. In-sample ends 16 Feb 2022;
out-of-sample runs 5 Apr 2022 → end 2023.

| Strategy | Best cell | In-sample Sharpe | Out-of-sample Sharpe | Verdict |
|---|---|---|---|---|
| Momentum | lookback 20 / MA 200 | **0.949** | −0.303 | failed |
| MACD | 16 / 34 / 9 | 0.511 | −0.300 | failed |
| Bollinger | window 50 / 2.5σ | 0.558 | **1.169** | held up |

Ranking on the data the strategies were tuned on gives exactly the wrong
order. Momentum was the clear in-sample winner and had no edge at all on data
it had not seen. That is the headline the `/demo` page leads with.

## Five checks, and they disagree

A single 70/30 split is one number, and one number can be wrong in several
distinct ways. Each check below was built because the one before it was
caught lying in a specific way. The interesting result is not that they all
condemn momentum. They do not.

| Check | What it asks | Momentum | Bollinger |
|---|---|---|---|
| Walk-forward | Did it work on unseen data? | failed (−0.30) | held up (1.17) |
| Deflated Sharpe | Does the winner beat the best of N lucky draws? | yes, 0.81 | no, 0.37 |
| Effective N | How many genuinely different cells were tried? | 6 of 16 | 7 of 12 |
| PBO | Is selecting in-sample better than picking at random? | yes, 0.23 | yes, 0.13 |
| Permutation | Does the timing beat shuffled timing? | yes, p 0.022 | no, p 0.066 |

Read across the momentum column: walk-forward says failed; DSR says the
in-sample edge was real; PBO says the selection was not overfit; permutation
says the timing mattered. Four checks say the edge was genuine and one says
it did not persist. Those are compatible — the edge was there in 2018–2021
and was not there in 2022–2023. Bollinger is the reverse: it held up
out-of-sample with entries that cannot be told apart from shuffled ones.

Bootstrap intervals widen the picture rather than change it. Momentum's
out-of-sample Sharpe of −0.30 has a 95 % interval of [−1.4, +1.4], which
contains zero and contains Bollinger's 1.17. "Failed" and "held up" are the
right labels, but the gap between them is smaller than two point estimates
make it look. Appendix A has each check in full.

## Then the window moved

Extend the end date by one year, to 2025-01-01, and rerun. Nothing about the
strategies, grids, costs, or split ratio changes. The in-sample end moves
from 16 Feb 2022 to 26 Oct 2022 because 70 % of a longer period is later.

| Strategy | In-sample Sharpe | Out-of-sample Sharpe | Verdict | PBO |
|---|---|---|---|---|
| Momentum | 0.766 | **0.547** | held up | 0.19 |
| MACD | 0.656 | −0.114 | failed | **0.77 — overfit** |
| Bollinger | 0.686 | −0.157 | failed | 0.11 |

It inverts. Momentum holds up; Bollinger fails; MACD's PBO jumps from 0.30 to
0.77. Momentum's winning cell changes from MA 200 to MA 20.

The mechanism is not subtle once you see the dates. The first window's
out-of-sample half is April 2022 → December 2023: a drawdown into late 2022
and a choppy recovery. Mean reversion earns in chop; trend following gets
whipsawed. The second window's out-of-sample half is December 2022 → December
2024: a sustained uptrend, where trend following earns and mean reversion
sells every rally. The split moved eight months and landed on the other side
of a regime boundary.

## Walking the split forward

The obvious fix is to stop treating the split as fixed. In `rolling.py` the
in-sample stretch starts at 40 % of the period and the rest is tiled into four
segments. At each fold the grid is re-optimised on everything before it and
the winner is scored only on the segment that follows — anchored, because
that is what a live re-fit does. Every bar after the first split is scored
out-of-sample exactly once, by parameters chosen before it.

AAPL 2018-01-01 → 2024-01-01, out-of-sample Sharpe per segment:

| Segment | Market | Momentum | MACD | Bollinger |
|---|---|---|---|---|
| Jun 2020 → Apr 2021 | +54 % | 0.27 | −0.32 | 0.57 |
| May 2021 → Mar 2022 | +30 % | **1.10** | 0.58 | −0.60 |
| Apr 2022 → Feb 2023 | −15 % | **−0.80** | 0.06 | **1.90** |
| Feb 2023 → Dec 2023 | +31 % | 0.88 | −0.60 | −1.73 |
| Stitched | | 0.12 [−0.8, 1.3] | −0.08 | 0.44 [−0.4, 1.2] |
| Winning parameters changed | | 4 of 4 folds | 2 sets | never |

Now the first window's headline reads differently. Momentum "failed" in the
one segment where the market fell, and earned in the three where it rose.
Bollinger "held up" because its +1.90 segment was followed by a −1.73 one and
the single split scored both together. Momentum's winning parameters were
different at every re-fit, so the thing being validated was never one
strategy; it was "whatever fit the last stretch".

All three strategies, on both windows, read `regime_dependent`: at least one
fold positive, at least one not. The stitched intervals all contain zero.
That is the honest verdict, and it is not the verdict either single split
gave.

## Naming the regime

The folds are calendar segments, so label the regime directly
(`regimes.py`): every bar gets the market's trailing 21-day realised
volatility, the period is cut into terciles, and the stitched out-of-sample
return is broken down by label.

| Regime | Market | Momentum | MACD | Bollinger |
|---|---|---|---|---|
| Low vol (≤ 22 %) | 2.49 | 2.26 | 0.66 | −1.83 |
| Mid | 0.70 | 0.70 | 2.61 | 0.80 |
| High vol (> 32 %) | 0.60 | **−0.76** | **−1.76** | **1.31** |

Momentum's entire out-of-sample return came from the calm third, where the
market itself had a Sharpe of 2.49. In the turbulent third the market was
still positive and momentum lost. A second label, the direction of the
trend, says what that loss was: −1.88 in turbulent *flat* bars against +1.29
when turbulence had a direction. It is chop, not a bear market (Appendix B).
Bollinger is the mirror image. Neither is a good or a bad strategy. Each is a
bet on a regime, and the single-split walk-forward was scoring which regime
the split happened to land in.

## Against the market, with the search inside the test

Every check so far judges the winner. None asks the question a reader
actually has: across everything the grid tried, does *anything* beat simply
holding the stock, once you account for having tried all of it? White's
Reality Check, Hansen's SPA and the Romano-Wolf stepdown answer that in one
joint bootstrap.

| Ticker, window | Grid | Best cell vs buy-and-hold | p alone | p, whole grid (RC / SPA) | Survivors |
|---|---|---|---|---|---|
| AAPL 2018→2024 | Momentum, 16 | −6.4%/yr | 0.63 | 0.89 / 1.00 | 0 |
| AAPL 2018→2024 | Bollinger, 12 | −25.0%/yr | 0.98 | 0.99 / 1.00 | 0 |
| AAPL 2018→2025 | Momentum, 16 | −9.6%/yr | 0.76 | 0.96 / 1.00 | 0 |
| BABA 2018→2024 | Bollinger, 12 | +15.4%/yr | 0.17 | 0.33 / 0.33 | 0 |
| PYPL 2018→2024 | Bollinger, 12 | +8.8%/yr | 0.31 | 0.47 / 0.47 | 0 |
| INTC 2018→2024 | Bollinger, 12 | +5.7%/yr | 0.37 | 0.52 / 0.53 | 0 |

Not one cell beats buy-and-hold at 5 % once the search is in the test. The
gap between "p alone" and "p, whole grid" is the size of the data snooping:
BABA's best cell looks like a one-in-six fluke on its own and a one-in-three
fluke inside the grid that found it. And AAPL momentum on the 2025 window
reads *held up* on walk-forward while trailing buy-and-hold by 9.6 % a year.
"Held up" was always a statement against zero, not against the market.

The paired Ledoit-Wolf test of each strategy's Sharpe against buy-and-hold's
says the same thing from another side: across AAPL, SPY and BABA, the one
significant gap is AAPL Bollinger over 2015→2020, and it is a loss (p 0.038).
Six years of daily bars pins a Sharpe *difference* to about ±0.5, so most
gaps that look settled on a results page are not (Appendix C).

## The same questions, asked of a basket

A 2–10-ticker basket runs one parameter set across every leg, so the grid is
scored on the book, the benchmark is holding the basket, and the timing null
re-times each leg independently. AAPL + MSFT + GOOGL, 2018→2024, equal weight:

| Strategy | Walk-forward | Timing p (book) | Legs beating random timing | Best cell vs holding the basket | SPA p |
|---|---|---|---|---|---|
| Momentum | failed, 0.42 → −0.51 | 0.134 | 1 of 3 | −23.9%/yr | 1.00 |
| Bollinger | **held up**, 0.83 → 0.77 | **0.002** | **3 of 3** | −18.7%/yr | 1.00 |

Bollinger on the mega-cap basket is the cleanest two-verdict result in the
piece: it survived the split, every leg beat random timing, and it still
trails simply holding the three stocks by nineteen points a year. The timing
is real. It was not worth doing.

## What this actually shows

Not that mean reversion beats trend following on AAPL — the second window
says the opposite. Not that momentum is overfit — PBO across 70 splits says
it is not. What it shows is narrower and more useful:

1. **The in-sample ranking is not evidence.** The best in-sample cell was the
   worst out-of-sample cell once, and the best once, and nothing in the
   in-sample numbers distinguished the two cases.
2. **A single walk-forward split is one draw from a distribution of splits.**
   Reporting a walk-forward result without the window and the split date is
   reporting a coin flip without saying which side came up.
3. **The checks disagree, and the disagreement is the information.** DSR and
   PBO measure selection luck, walk-forward measures persistence, permutation
   measures timing. Which one a strategy fails says *why*. A tool that prints
   a single "robust / not robust" label has thrown that away.
4. **"Beat zero" and "beat the market" are different questions.** Every
   strategy here that held up out-of-sample still trailed buy-and-hold, and
   nothing survived the whole-grid test.

## What is still open

A rolling walk-forward for a basket is not built. The bootstrap intervals do
not resample by regime, so the volatility-interval coverage gap stands.

## Reproduce it

- Live: https://finertia.hulage.in → Dashboard → Validate, AAPL, 2018-01-01,
  end 2024-01-01 then 2025-01-01, default parameters, split 0.7.
- Check every figure: `cd backend && .venv/bin/python scripts/reproduce_writeup.py runs.json`
  re-runs each call through the production route handlers (auth faked, fresh
  yfinance prices, nothing written) and prints each quoted figure beside its
  fresh value; it exits non-zero if any no longer matches at the precision
  printed.
- Source: `backend/validation.py`, `rolling.py`, `regimes.py`, `deflated.py`,
  `trials.py`, `pbo.py`, `snooping.py`, `sharpe_test.py`,
  `portfolio_validation.py`, `purge.py`, `bootstrap.py`. Pure pandas + numpy;
  no backtesting or statistics library.
- Tests: 723 in `backend/tests/`, including reproductions of the DSR paper's
  worked example and Lo (2002) to 1e-12, and mutation checks on every check.
- Figures were first taken 15–23 Sep 2026 and re-run on 7 Oct 2026: every
  deterministic figure reproduced to the digit. The bootstrap figures had been
  taken in research runs with a different random seed than the product's, so
  they were replaced with the seeded values the site prints; no conclusion
  changed. Yahoo re-adjusts on corporate actions, so the third decimal can
  still drift.

---

## Appendix A — The five checks in detail

**Deflated Sharpe Ratio** (`deflated.py`, Bailey & López de Prado 2014). The
walk-forward winner is the *maximum* of N grid cells, and the maximum of N
draws from zero-edge noise is well above zero. DSR asks whether the in-sample
Sharpe clears that bar. Momentum's does — DSR 0.81. Bollinger's does not —
DSR 0.37. So the check designed to catch selection luck passes the strategy
that failed out-of-sample and fails the one that held up. That is not a bug.
DSR tests whether an in-sample number is distinguishable from picking the best
of 16 coin flips; it says nothing about whether the edge persists. A real
in-sample edge that then vanishes is a regime story, not a luck story.

**Effective number of trials** (`trials.py`, Li & Ji 2005; López de Prado &
Lewis 2019). N in the DSR is not the grid size: a 20-day and a 25-day lookback
are nearly the same trial, so 16 cells over-deflate. Measured two ways from
the candidates' in-sample returns — eigenvalue count and correlation
clustering — momentum's 16 is really 6 (clusters say 3), MACD's 4 is 2,
Bollinger's 12 is 7 (clusters say 2). The headline takes the larger estimate,
because lowering N is the direction that flatters. DSR moves by +0.07 to
+0.12; no verdict changes. The check corrects the bar. It rescues nothing.

**Probability of Backtest Overfitting** (`pbo.py`, CSCV). Instead of one
split, all 70 balanced splits of the period: how often does the cell that won
in-sample land in the bottom half out-of-sample? Momentum 0.23, MACD 0.30,
Bollinger 0.13 — all acceptable. Across splits, momentum's ranking mostly
survives; the one split we happened to look at is unkind to it. PBO was the
most stable check across the two windows for momentum (0.23 → 0.19) and
Bollinger (0.13 → 0.11), and the least stable for MACD (0.30 → 0.77).

**Signal permutation** (`validation.py`). Shuffle the position series 500
times, holding the number of long, short and flat days fixed, so only
*timing* changes. Momentum's real Sharpe sits at the 98th percentile of the
shuffles (p = 0.022); MACD at the 99th (p = 0.008). Bollinger sits at the
94th (p = 0.066) — indistinguishable from random timing at the 5 % level.

**Block-bootstrap confidence intervals** (`bootstrap.py`, stationary block
bootstrap, BCa) sit under every metric on every plan. Momentum's
out-of-sample Sharpe of −0.30 comes from 437 bars and its 95 % interval is
[−1.4, +1.4]. Bollinger's is [0.2, 2.2], which does exclude zero. Endpoints
are printed to one decimal on purpose: at 1,000 resamples an endpoint moves
by up to 0.3 between random seeds, so a second decimal would be noise.

## Appendix B — Trend crossed with volatility

Every bar also gets a trend label: the t-statistic of the market's trailing
60-day mean return, `up` above +1σ, `down` below −1σ, `flat` between (a fixed
cut, not a tercile, so flat means flat). Crossed with the volatility terciles
on momentum's out-of-sample bars, AAPL 2018 → 2024-01-01:

| Momentum OOS Sharpe | Flat | Rising |
|---|---|---|
| Low vol | 2.40 (124 bars) | 2.29 (135) |
| Mid | 0.81 (195) | 0.45 (81) |
| High vol | **−1.88** (199) | **+1.29** (84) |

Momentum's calm edge is there whether the market was rising or not. What the
grid separates is the turbulent third — the −0.76 of the volatility table is
−1.88 in turbulent flat bars and +1.29 when turbulence had a direction.
Bollinger reads the same cells the other way round (+2.19 turbulent-flat,
−1.01 turbulent-rising). "Down" is left off because AAPL hardly had any: 5 %
of bars, nearly all turbulent, too few per cell for a Sharpe worth printing.

## Appendix C — Is the gap to buy-and-hold real?

Every result page prints the strategy's Sharpe beside buy-and-hold's. The
two series share most of their bars, and nothing on the page says how wide the
gap would have to be to mean anything. Ledoit and Wolf (2008) is the test for
exactly this — paired, because the strategy trades the benchmark's own asset;
HAC, because daily returns are neither independent nor homoskedastic; and a
studentised bootstrap rather than a normal approximation. Two-sided, because
a strategy significantly *worse* than holding is the more common finding.
Sharpe here is mean over standard deviation, annualised; the geometric figure
on the results card sits 0.05 to 0.19 lower on these runs.

| Ticker, window | Strategy | Sharpe | Buy-and-hold | Gap | Std. error | p |
|---|---|---|---|---|---|---|
| AAPL 2018→2024 | Momentum | 0.59 | 0.98 | −0.39 | 0.51 | 0.36 |
| AAPL 2018→2024 | Bollinger | 0.06 | 0.98 | −0.91 | 0.54 | 0.13 |
| AAPL 2018→2024 | MACD | 0.53 | 0.98 | −0.44 | 0.54 | 0.39 |
| AAPL 2015→2020 | Bollinger | −0.46 | 0.99 | −1.45 | 0.60 | **0.038** |
| SPY 2018→2024 | Momentum | −0.26 | 0.65 | −0.91 | 0.62 | 0.080 |
| BABA 2018→2024 | Bollinger | 0.13 | −0.08 | +0.21 | 0.57 | 0.73 |

The standard error is the column to read. A strategy trailing the market by
four tenths of a Sharpe, which looks like a settled verdict on the page, is
not distinguishable from one that matches it. This cuts both ways: against a
benchmark it correlates with, the test needs roughly a full point of Sharpe
over five years before it will reject at 5 % (74 % power at +0.92, 28 % at
+0.47). So a p of 0.36 is not evidence that the gap is zero; it is the honest
statement that five years of one stock cannot resolve it.
