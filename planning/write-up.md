# The best in-sample strategy was the worst out-of-sample one — and then the window moved

_Draft 2, 16 Sep 2026 (draft 1: 15 Sep). Every number below is reproducible on
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

## Walking the split forward

The obvious fix for point 2 is to stop treating the split as fixed. Built the
next day (`backend/rolling.py`): the in-sample stretch starts at 40 % of the
period and the rest is tiled into four segments. At each fold the grid is
re-optimised on everything before it and the winner is scored on the segment
that follows and nowhere else — anchored, because that is what a live re-fit
does. The purge gap sits at every boundary. Every bar after the first split
is scored out-of-sample exactly once, by parameters chosen before it.

AAPL 2018-01-01 → 2024-01-01, out-of-sample Sharpe per segment:

| Segment | Market | Momentum | MACD | Bollinger |
|---|---|---|---|---|
| Jun 2020 → Apr 2021 | +54 % | 0.27 | −0.32 | 0.57 |
| May 2021 → Mar 2022 | +30 % | **1.10** | 0.58 | −0.60 |
| Apr 2022 → Feb 2023 | −15 % | **−0.80** | 0.06 | **1.90** |
| Feb 2023 → Dec 2023 | +31 % | 0.88 | −0.60 | −1.73 |
| Stitched | | 0.12 [−0.84, 1.45] | −0.08 | 0.44 [−0.46, 1.22] |
| Winning parameters changed | | 4 of 4 folds | 2 sets | never |

Now the first window's headline reads differently. Momentum "failed" in the
one segment where the market fell, and earned in the three where it rose.
Bollinger "held up" because its +1.90 segment was followed by a −1.73 one and
the single 70/30 split scored both together. Momentum's winning parameters
were different at every re-fit — MA 50, then 100, then 200, then 20 — so the
thing being validated was never one strategy; it was "whatever fit the last
stretch". Bollinger kept 50/2.5 throughout and still alternated sign.

All three strategies, on both windows, read `regime_dependent`: at least one
fold positive, at least one not. The stitched intervals all contain zero.
That is the honest verdict, and it is not the verdict either single split
gave.

## Naming the regime

The folds are calendar segments; the reader infers the regime from the
market column. So label it directly (`backend/regimes.py`): every bar gets
the market's trailing 21-day realised volatility, the period is cut into
terciles, and the stitched out-of-sample return is broken down by label.
Sharpe on each third, AAPL 2018 → 2024-01-01, out-of-sample:

| Regime | Market | Momentum | MACD | Bollinger |
|---|---|---|---|---|
| Low vol (≤ 22 %) | 2.49 | 2.26 | 0.66 | −1.83 |
| Mid | 0.70 | 0.70 | 2.61 | 0.80 |
| High vol (> 32 %) | 0.60 | **−0.76** | **−1.76** | **1.31** |

Momentum's entire out-of-sample return came from the calm third, where the
market itself had a Sharpe of 2.49 — momentum was long and the market went
up. In the turbulent third the market was still positive and momentum lost:
that is whipsaw, not a bear market. Bollinger is the mirror image, losing in
calm markets it had no reason to trade and earning in the turbulence it was
built for. Neither is a good or bad strategy. Each is a bet on a regime, and
the single-split walk-forward was scoring which regime the split happened to
land in.

One more axis, added 21 Sep, because "calm" could be hiding "rising": every
bar also gets a trend label — the t-statistic of the market's trailing 60-day
mean return, `up` above +1σ, `down` below −1σ, `flat` between (a fixed cut,
not a tercile, so flat means flat). Crossing the two on momentum's
out-of-sample bars, same window:

| Momentum OOS Sharpe | Flat | Rising |
|---|---|---|
| Low vol | 2.40 (124 bars) | 2.29 (135) |
| Mid | 0.81 (195) | 0.45 (81) |
| High vol | **−1.88** (199) | **+1.29** (84) |

The guess was wrong: momentum's calm edge is there whether the market was
rising or not. What the grid separates is the turbulent third — the −0.76
above is −1.88 in turbulent *flat* bars and +1.29 when turbulence had a
direction. The loss the vol label called "turbulence" is chop. Bollinger reads
the same cell the other way round (+2.19 turbulent-flat, −1.01
turbulent-rising). "Down" is left off the table because AAPL hardly had any:
5% of bars, nearly all turbulent, too few per cell for a Sharpe worth printing —
which the grid says by reporting the count and no number.

## Against the market, with the search inside the test

Every check so far judges the winner, or the act of selecting it. None asks
the question a reader actually has: across everything the grid tried, does
*anything* beat simply holding the stock — once you account for having tried
all of it? White's Reality Check, Hansen's SPA and the Romano-Wolf stepdown
answer that in one bootstrap: every cell's excess return over buy-and-hold,
resampled jointly, the maximum compared with the distribution of a maximum.
Stepdown adds the per-cell version — which cells survive at 5%.

| Ticker, window | Grid | Best cell vs buy-and-hold | p alone | p, whole grid (RC / SPA) | Survivors |
|---|---|---|---|---|---|
| AAPL 2018→2024 | Momentum, 16 | −6.4%/yr | 0.63 | 0.89 / 1.00 | 0 |
| AAPL 2018→2024 | Bollinger, 12 | −25.0%/yr | 0.98 | 0.99 / 1.00 | 0 |
| AAPL 2018→2025 | Momentum, 16 | −9.6%/yr | 0.76 | 0.96 / 1.00 | 0 |
| BABA 2018→2024 | Bollinger, 12 | +15.4%/yr | 0.17 | 0.33 / 0.33 | 0 |
| PYPL 2018→2024 | Bollinger, 12 | +8.8%/yr | 0.31 | 0.47 / 0.47 | 0 |
| INTC 2018→2024 | Bollinger, 12 | +5.7%/yr | 0.37 | 0.52 / 0.53 | 0 |

Five tickers, two windows, three grids: not one cell beats buy-and-hold at
5% once the search is in the test. Two things in that table are worth
more than the zeros. The gap between "p alone" and "p, whole grid" is the
size of the data snooping — BABA's best Bollinger cell looks like a
one-in-six fluke on its own and a one-in-three fluke inside the grid that
found it. And AAPL momentum on the 2025 window reads *held up* on
walk-forward while trailing buy-and-hold by 9.6% a year: "held up" was
always a statement against zero, not against the market.

## The same questions, asked of a basket

Every check above is defined on one position series. A 2–10-ticker basket
had none of them, and extending them turned out to be two decisions rather
than any new maths. First, what is optimised: a basket runs one parameter set
across every leg, so the grid is scored on the *book's* in-sample Sharpe and
the whole-grid benchmark is holding the basket at the same weights. Second,
what "random timing" means for a book. Shuffling the weight path asks whether
the allocation rule adds anything; shuffling each leg's timing independently,
weights fixed, asks whether any leg can time its own market. The second is
the question a shared-parameter strategy poses, so that is the null — and it
has to be independent per leg, not one shared draw, or two mirror-image legs
would cancel under the null exactly as they do in reality and a flat book
would read as skill.

AAPL + MSFT + GOOGL, 2018→2024, equal weight, on the first split:

| Strategy | Walk-forward | Timing p (book) | Legs beating random timing | Best cell vs holding the basket | SPA p |
|---|---|---|---|---|---|
| Momentum | failed, 0.42 → −0.51 | 0.134 | 1 of 3 (AAPL) | −23.9%/yr | 1.00 |
| Bollinger | **held up**, 0.83 → 0.77 | **0.002** | **3 of 3** | −18.7%/yr | 1.00 |

Bollinger on the mega-cap basket is the cleanest two-verdict result in the
whole piece: it survived the split, every leg beat random timing, and it
still trails simply holding the three stocks by nineteen points a year. The
timing is real. It was not worth doing.

## Two numbers, and the gap between them

Every result page prints the strategy's Sharpe with buy-and-hold's curve
beside it. The comparison is irresistible and, as printed, unmakeable: the
two series share most of their bars, and nothing on the page says how wide
the gap would have to be to mean anything. Ledoit and Wolf (2008) is the test
for exactly this — paired, because the strategy trades the benchmark's own
asset; HAC, because daily returns are neither independent nor
homoskedastic; and studentised-bootstrap rather than normal, because a few
thousand bars is not asymptotia. Two-sided, because a strategy significantly
*worse* than holding is the more common finding and the reader deserves it.

Sharpe here is mean over standard deviation, annualised — the delta method is
defined on the moments, and the geometric figure on the results card sits
0.05 to 0.19 lower on these runs. The pair below is the pair that was tested.

| Ticker, window | Strategy | Sharpe | Buy-and-hold | Gap | Std. error | p |
|---|---|---|---|---|---|---|
| AAPL 2018→2024 | Momentum | 0.59 | 0.98 | −0.39 | 0.51 | 0.40 |
| AAPL 2018→2024 | Bollinger | 0.06 | 0.98 | −0.91 | 0.54 | 0.15 |
| AAPL 2018→2024 | MACD | 0.53 | 0.98 | −0.44 | 0.54 | 0.39 |
| AAPL 2015→2020 | Bollinger | −0.46 | 0.99 | −1.45 | 0.60 | **0.031** |
| SPY 2018→2024 | Momentum | −0.26 | 0.65 | −0.91 | 0.62 | 0.076 |
| BABA 2018→2024 | Bollinger | 0.13 | −0.08 | +0.21 | 0.57 | 0.71 |

The standard error is the column to read. Six years of daily bars pins a
Sharpe *difference* to about ±0.5 — so a strategy trailing the market by four
tenths of a Sharpe, which looks like a settled verdict on the page, is not
distinguishable from a strategy that matches it. The one significant row is a
loss: Bollinger on AAPL's 2015→2020 window is genuinely worse than holding
the stock, not unluckier.

This cuts both ways, and the simulated power table says how much. Against a
benchmark it correlates with, this test needs roughly a full point of Sharpe
over five years before it will reject at 5% (74% power at +0.92, 28% at
+0.47). So a p of 0.4 here is not evidence that the gap is zero — it is the
honest statement that five years of one stock cannot resolve it. That is a
limit of the data, and it is worth printing beside the number rather than
leaving the reader to infer a verdict the sample cannot support.

## What is still open

A rolling walk-forward for a book is not built. The bootstrap intervals
still do not resample by regime, so the vol-CI coverage gap stands.

## Reproduce it

- Live: https://finertia.hulage.in → Dashboard → Validate, AAPL, 2018-01-01,
  end 2024-01-01 then 2025-01-01, default parameters, split 0.7.
- Source: `backend/validation.py` (`walk_forward`, `permutation_test`),
  `backend/rolling.py`, `backend/regimes.py`, `backend/deflated.py`, `backend/trials.py`,
  `backend/pbo.py`, `backend/snooping.py`, `backend/sharpe_test.py`, `backend/portfolio_validation.py`, `backend/purge.py`, `backend/bootstrap.py`. Pure pandas + numpy; no
  backtesting or statistics library; the normal CDF is `math.erf`.
- Tests: 712 in `backend/tests/`, including reproductions of the DSR paper's
  worked example and Lo (2002) to 1e-12, and mutation checks on every check
  above.
- Figures are as of 15 Sep 2026 (whole-grid table: 20 Sep; basket and vol × trend tables: 21 Sep; Sharpe-gap table: 23 Sep) with yfinance adjusted prices; Yahoo
  re-adjusts on corporate actions, so the third decimal will drift.
