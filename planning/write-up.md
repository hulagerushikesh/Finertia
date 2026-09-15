# The best in-sample strategy was the worst out-of-sample one — and then the window moved

_Draft 1, 15 Sep 2026. Every number below is reproducible on
https://finertia.hulage.in (Validate tab) or from `backend/` with
`walk_forward` + `permutation_test`; the source for each check is named._

## The setup

One ticker, AAPL. Three strategies with nothing exotic about them:
momentum (price above its N-day moving average and rising over a lookback),
MACD crossover, and a Bollinger-band mean-reverter. Transaction cost 10 bp on
turnover. Each strategy has a small parameter grid — 16 cells for momentum,
4 for MACD, 12 for Bollinger.

Walk-forward validation optimises the grid on the first 70 % of the period,
then scores the winning cell on the remaining 30 %. A purge-and-embargo gap
(1 % of the period, 16 bars here) is cut around the split so the trade that
straddles it cannot earn on both sides. Only the out-of-sample number is
evidence; the in-sample number is what a backtest normally shows you.

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
it had not seen. That is the headline the `/demo` page leads with, and it is
the reason the rest of the validation stack exists — a single 70/30 split is
one number, and one number can be wrong in several distinct ways.

## Four more checks, and they do not agree

Each of these was built because the previous one was found to be lying in a
specific way. The interesting result is not that they all condemn momentum.
They do not.

**Deflated Sharpe Ratio** (`deflated.py`, Bailey & López de Prado 2014).
The walk-forward winner is the *maximum* of N grid cells, and the maximum of
N draws from zero-edge noise is well above zero. DSR asks whether the
in-sample Sharpe clears that bar. Momentum's does — DSR 0.81, clears the
noise bar. Bollinger's does not — DSR 0.37. So the check designed to catch
selection luck passes the strategy that failed out-of-sample and fails the
one that held up. That is not a bug. DSR tests whether an in-sample number is
distinguishable from picking the best of 16 coin flips; it says nothing about
whether the edge persists. A real in-sample edge that then vanishes is a
regime story, not a luck story, and DSR is the wrong instrument for it.

**Effective number of trials** (`trials.py`, Li & Ji 2005; López de Prado &
Lewis 2019). N in the DSR is not the grid size. A 20-day and a 25-day
lookback are nearly the same trial, so 16 cells over-deflate. Measured two
ways from the candidates' in-sample returns — eigenvalue count and
correlation clustering — momentum's 16 is really 6 (clusters say 3),
MACD's 4 is 2, Bollinger's 12 is 7 (clusters say 2). The headline takes the
larger estimate, because lowering N is the direction that flatters. DSR moves
by +0.07 to +0.12; no verdict changes. The check corrects the bar. It rescues
nothing.

**Probability of Backtest Overfitting** (`pbo.py`, CSCV). Instead of one
split, all 70 balanced splits of the period: how often does the cell that
won in-sample land in the bottom half out-of-sample? Momentum 0.23, MACD 0.30,
Bollinger 0.13 — all acceptable. Selecting on the in-sample score is
consistently better than picking at random. So the harsh verdict from the
single 70/30 split is *not* evidence of systematic overfitting; across
splits, momentum's ranking mostly survives. The one split we happened to
look at is unkind to it.

**Signal permutation** (`validation.py`). Shuffle the position series 500
times, holding the number of long, short, and flat days fixed, so only
*timing* changes. Momentum's real Sharpe sits at the 98th percentile of the
shuffles (p = 0.022); MACD at the 99th (p = 0.008). Timing matters for both.
Bollinger sits at the 94th (p = 0.066) — indistinguishable from random
timing at the 5 % level. The one strategy that held up out-of-sample is the
one whose entries cannot be told apart from shuffled entries.

**Block-bootstrap confidence intervals** (`bootstrap.py`, stationary block
bootstrap, BCa) sit under every metric on every plan. They do not change the
story above; they widen it. Momentum's out-of-sample Sharpe of −0.30 comes
from 437 bars and its 95 % interval is [−1.40, +1.41] — it contains zero, and
it contains Bollinger's 1.17. Bollinger's own interval is [0.20, 2.05], which
does exclude zero. So "failed" and "held up" are the right labels, but the
gap between them is smaller than two point estimates make it look.

Put the five side by side for momentum: walk-forward says failed, DSR says
real, effective N says still real, PBO says not overfit, permutation says
timing matters. Four of five say the in-sample edge was genuine. One says it
did not persist. Those are compatible. The edge was there in 2018–2021 and
was not there in 2022–2023.

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
0.77. Momentum's winning cell changes from MA 200 to MA 20 — the grid
re-optimised onto a different regime.

The mechanism is not subtle once you see the dates. The first window's
out-of-sample half is April 2022 → December 2023: a drawdown into late 2022
and a choppy recovery. Mean reversion earns in chop; trend following gets
whipsawed. The second window's out-of-sample half is December 2022 → December
2024: a sustained uptrend. Trend following earns in a trend; mean reversion
sells every rally. The split moved eight months and landed the out-of-sample
period on the other side of a regime boundary.

## What this actually shows

Not that mean reversion beats trend following on AAPL — the second window
says the opposite. Not that momentum is overfit — PBO across 70 splits says
it is not. What it shows is narrower and more useful:

1. **The in-sample ranking is not evidence.** Both windows agree on this. The
   best in-sample cell was the worst out-of-sample cell once, and was the
   best once, and nothing in the in-sample numbers distinguished the two
   cases.
2. **A single walk-forward split is one draw from a distribution of splits.**
   The verdict is a function of where the split lands relative to the market's
   regime changes, and the split lands wherever 70 % of the requested window
   happens to fall. Reporting a walk-forward result without the window and the
   split date is reporting a coin flip without saying which side came up.
3. **The checks disagree, and the disagreement is the information.** DSR and
   PBO measure selection luck; walk-forward measures persistence; permutation
   measures timing. A strategy can pass three and fail one, and the pattern of
   which one it fails says *why* — luck, overfit, regime, or exposure. A tool
   that prints a single "robust / not robust" label has thrown that away.
4. **Every check needs its own window sensitivity stated.** PBO was the most
   stable across the two windows for momentum and Bollinger, and the least
   stable for MACD (0.30 → 0.77). Which check is trustworthy depends on the
   strategy, which is a reason to run all of them, not a reason to pick one.

## What I would build next

The obvious fix for point 2 is to stop treating the split as fixed.
Regime-aware walk-forward — either rolling several splits across the period
and reporting the distribution of out-of-sample verdicts, or anchoring splits
to detected regime boundaries — is the top open research item
(`learning/research/open-questions.md` §3). CSCV already does the "every
split" half of this for the ranking question; extending it to the
out-of-sample Sharpe itself is the missing piece.

The second is portfolio-mode validation: walk-forward and permutation are
defined on one position series, so a 2–10-ticker basket currently gets
metrics and confidence intervals but no overfitting checks.

## Reproduce it

- Live: https://finertia.hulage.in → Dashboard → Validate, AAPL, 2018-01-01,
  end 2024-01-01 then 2025-01-01, default parameters, split 0.7.
- Source: `backend/validation.py` (`walk_forward`, `permutation_test`),
  `backend/deflated.py`, `backend/trials.py`, `backend/pbo.py`,
  `backend/purge.py`, `backend/bootstrap.py`. Pure pandas + numpy; no
  backtesting or statistics library; the normal CDF is `math.erf`.
- Tests: 567 in `backend/tests/`, including reproductions of the DSR paper's
  worked example and Lo (2002) to 1e-12, and mutation checks on every check
  above.
- Figures are as of 15 Sep 2026 with yfinance adjusted prices; Yahoo
  re-adjusts on corporate actions, so the third decimal will drift.
