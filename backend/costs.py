"""How much does the cost assumption matter, and where does the edge die?

This module exists because of a measurement that killed the feature it was
supposed to support. The plan was a vol-scaled transaction-cost model: real
spreads widen with volatility, a momentum strategy trades when volatility is
high, so a flat charge should flatter it exactly when it hurts most. Both
halves of that sentence are true. The conclusion does not follow.

Two things were measured before writing any of it.

1. The coefficient cannot be identified from the data we have
----------------------------------------------------------------
A vol-scaled model needs a coefficient: cost_t = base * (sigma_t/sigma_ref)^k.
With only daily OHLCV, k has to come from a high-low spread estimator —
Corwin-Schultz (2012) or Abdi-Ranaldo (2017). Neither can supply it.

The control: simulate bars whose true spread is CONSTANT and whose volatility
follows a GARCH process, then regress the estimated monthly spread on realised
monthly vol in logs. The true slope is zero by construction, so whatever comes
out is leakage.

    true spread   Abdi-Ranaldo slope   (true slope is 0.00)
        5 bps           1.07
       10 bps           0.99
       25 bps           0.86
       50 bps           0.57
      100 bps           0.23

The leakage has a mechanism, not just a magnitude. When the true spread is
small next to daily vol, the estimator returns its own noise floor, and that
floor is proportional to vol — so it reports "spreads scale with vol" for a
spread that never moved. The bias shrinks as the true spread grows, which is
exactly the monotone pattern above.

On real tickers, 2010-2025, monthly blocks, the same estimator gives slopes of
0.73 to 1.03 — squarely inside the range the constant-spread control produces.
It also puts SPY's effective spread at 24 bps and AAPL's at 38, one to two
orders of magnitude above what those names actually trade at, which is the
noise floor showing up in the level as well as the slope. Corwin-Schultz is
worse: truncated after averaging it returns a non-positive estimate in 69-96%
of months, so for most of the sample it yields no number at all.

A regression whose slope is the same whether or not the effect exists measures
nothing. There is no honest k here without a paid spread or quote feed.

2. It would not matter if there were
----------------------------------------------------------------
Split the question in two, because conflating them is what makes the original
claim sound obvious:

    LEVEL   a cost model that charges more on average scores worse.
    TIMING  holding the TOTAL cost paid fixed, does moving the charge onto
            high-vol bars hurt?

Only TIMING is about the model's shape; LEVEL is about the number the user
typed. Rescaling each vol-scaled model so it pays exactly what the flat model
pays isolates the shape. Across three strategies x eight tickers, 2010-2025:

    model                          cost paid vs flat   max |Sharpe shift|
    k = 1 (linear in vol)             1.02 - 1.33x           0.002
    k = 2                             1.28 - 2.30x           0.003
    k = 3                             1.88 - 5.32x           0.015
    5x multiplier in top vol decile   1.28 - 1.45x           0.002

For comparison, the LEVEL channel moves Sharpe by -0.16 to -0.32 per extra
10 bps. The shape of the cost model is worth roughly a thirtieth of the level,
and that is with k = 3 and a crisis multiplier — neither of which anybody
would defend as calibrated.

The reason is structural rather than a quirk of these samples. Redistributing
a fixed cost budget leaves the mean net return unchanged by construction, so
it can only reach Sharpe through the variance the cost series adds — which is
second order next to return variance. Pushed to the absurd extreme (the entire
cost budget charged on the top 1% of vol bars, roughly 37 bars in fifteen
years) the shift finally becomes visible, up to 0.157 Sharpe, and it moves the
WRONG WAY: concentrating cost inflates return variance, which shrinks |Sharpe|
toward zero. For a losing strategy that is an improvement. The flat model is
not flattering anybody.

Momentum also turns out not to trade especially when vol is high. Weighting
the vol ratio by turnover gives 1.07-1.27 against an unweighted 1.06-1.31 —
on three of eight tickers it trades at LOWER vol than average. The premise
that survived measurement was the spread one, not the timing one.

What this module ships instead
----------------------------------------------------------------
If the level is what matters, report the level. `cost_sensitivity` answers the
question the user can act on: how far can costs rise before the edge is gone?

`breakeven_cost` is the per-unit-turnover charge at which the strategy's
annualised return reaches exactly zero — and therefore, under this project's
Sharpe convention (annualised return / annualised vol), where the Sharpe on
the page reaches zero too. Equity ending at 1.0 means sum(log1p(net)) = 0, and
every term is non-increasing in cost with at least one strictly decreasing, so
the root is unique and bisection cannot land on the wrong one.

The headline is the ratio of that to what the user assumed. On momentum
20/50/2% at the default 10 bps, AAPL breaks even at 19 bps — a factor of 1.9 —
and five of eight tickers tested never had an edge to lose.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine import apply_positions
from metrics import compute_metrics

# Cost multiples of the user's own assumption. 0 is the frictionless upper
# bound, 1 is what they ran, and the rest ask "what if I am wrong by 2x/5x" —
# which the measurement above says is the only question about costs worth
# putting on the page.
CURVE_MULTIPLES: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 5.0)

# Used only when the user assumed zero cost, where multiples are meaningless.
CURVE_ABSOLUTE: tuple[float, ...] = (0.0, 0.0005, 0.0010, 0.0025, 0.0050)

# Bisection runs to this width in cost space. 1e-9 is a ten-thousandth of a
# basis point — far below the precision of any spread anyone could quote, and
# reached in about 40 halvings of a bracket that is never wider than 1.0.
_TOLERANCE = 1e-9
_MAX_ITER = 200


def _turnover(position: pd.Series) -> pd.Series:
    """Turnover exactly as the engine charges it, including the bar-0 rule."""
    turnover = position.diff().abs()
    turnover.iloc[0] = abs(position.iloc[0])
    return turnover


def _log_growth(gross: np.ndarray, turnover: np.ndarray, cost: float) -> float:
    """sum(log1p(net)) at this cost. -inf once equity would pass through zero.

    This reconstructs the engine's net return rather than calling it, because
    the bisection evaluates it ~40 times. `test_the_fast_path_matches_the_engine`
    pins the two together so the shortcut cannot drift.
    """
    net = gross - turnover * cost
    if np.any(net <= -1.0):
        return -np.inf
    return float(np.log1p(net).sum())


def _wipeout_cost(gross: np.ndarray, turnover: np.ndarray) -> float:
    """Smallest cost that drives equity through zero on some bar.

    Above this there is no real annualised return at all, so it is the hard
    right edge of the bracket. Only bars that actually trade can be pushed
    under by a cost.
    """
    trades = turnover > 0
    if not np.any(trades):
        return np.inf
    return float(((1.0 + gross[trades]) / turnover[trades]).min())


def breakeven_cost(position: pd.Series, returns: pd.Series) -> tuple[float | None, str]:
    """The cost per unit turnover at which annualised return hits zero.

    Returns (cost, status):
        ("measured")     a positive breakeven exists; the float is it
        ("unprofitable") the strategy loses before any cost, so 0.0
        ("no_trades")    nothing ever trades, so no cost can bite; None
    """
    gross = (position * returns.fillna(0.0)).to_numpy(dtype=float)
    turnover = _turnover(position).to_numpy(dtype=float)

    if not np.any(turnover > 0):
        return None, "no_trades"

    if _log_growth(gross, turnover, 0.0) <= 0.0:
        # Costs are not what killed it. Reporting a positive breakeven here
        # would imply an edge that has to be eaten away; there is none.
        return 0.0, "unprofitable"

    # Strictly decreasing from a positive value at 0 to -inf at the wipeout
    # bound, so exactly one root sits between them. Step just inside the bound:
    # at it, log1p(-1) is -inf rather than a number to compare.
    low, high = 0.0, _wipeout_cost(gross, turnover) * (1.0 - 1e-9)
    for _ in range(_MAX_ITER):
        if high - low <= _TOLERANCE:
            break
        mid = (low + high) / 2.0
        if _log_growth(gross, turnover, mid) > 0.0:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0, "measured"


def cost_sensitivity(
    position: pd.Series,
    returns: pd.Series,
    assumed_cost: float,
) -> dict:
    """Where the edge dies, and what the metrics look like on the way there.

    The curve is computed by running the real engine at each cost rather than
    by rescaling, so every point is exactly what the user would see if they
    re-ran the backtest with that number in the box.
    """
    breakeven, status = breakeven_cost(position, returns)

    # Multiples of what they assumed, unless they assumed nothing — in which
    # case every multiple collapses to zero and says nothing.
    levels = (
        tuple(assumed_cost * m for m in CURVE_MULTIPLES)
        if assumed_cost > 0
        else CURVE_ABSOLUTE
    )

    curve = []
    for cost in levels:
        out = apply_positions(position, returns, cost)
        m = compute_metrics(
            out["net_return"].fillna(0),
            out["equity_curve"].fillna(1),
            out["drawdown"].fillna(0),
            out["position"],
        )
        curve.append(
            {
                "cost": round(float(cost), 8),
                "sharpe_ratio": m["sharpe_ratio"],
                "annualized_return": m["annualized_return"],
                "total_return": m["total_return"],
            }
        )

    # How wrong the assumption can be before the edge is gone. Undefined when
    # they assumed zero cost (everything is infinitely many times zero) or
    # when there was no edge in the first place.
    headroom = (
        round(breakeven / assumed_cost, 4)
        if status == "measured" and assumed_cost > 0
        else None
    )

    return {
        "assumed_cost": round(float(assumed_cost), 8),
        "breakeven_cost": round(breakeven, 8) if breakeven is not None else None,
        "headroom": headroom,
        "status": status,
        "curve": curve,
    }
