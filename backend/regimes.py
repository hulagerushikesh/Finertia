"""Volatility regimes — where, in the market's own terms, a result was earned.

The rolling walk-forward (`rolling.py`) shows that a verdict depends on the
stretch it was scored in, and leaves the reader to infer the regime from each
fold's market return. This module makes the regime explicit: every bar gets a
label from the market's realised volatility, and the strategy's return is
broken down by label. "Earns in calm markets, gives it back in turbulent
ones" then becomes three numbers instead of a story told from a fold table.

Label
-----
Realised volatility is the trailing `window`-bar standard deviation of the
*market's* daily returns, annualised. The window ends at the bar it labels,
which includes that bar — this is a description of where returns landed, not
a signal, so nothing is decided on it and there is no lookahead to avoid.

Bars are cut into terciles of that series over the period requested: the
calmest third is `low`, the middle third `mid`, the most turbulent third
`high`. Terciles are relative to the period, deliberately: a 20% vol bar is
"high" inside 2017 and "low" inside 2020, and the question being answered is
about *this* backtest's spread of conditions, not a fixed calendar of crises.
The thresholds are reported so the reader can see what "high" meant.

Trend label
-----------
Volatility alone cannot separate "calm and rising" from "calm and flat", and
that is exactly where a momentum strategy's beta hides. So every bar also
gets a trend label from the *direction* of the market over the trailing
`trend_window` bars: the t-statistic of that window's mean daily return,
`sum(r) / (std(r) * sqrt(n))`. Above +1 the market was trending `up`, below
−1 `down`, in between `flat` — a move inside one standard deviation of its
own noise is not a trend, whatever its sign. The cut is a fixed ±1σ rather
than a tercile because "flat" has to mean flat; a tercile would call the
middle third of a bull market flat. Scaling by the window's own volatility
makes the label unit-free across tickers and, deliberately, harder to earn
in turbulent stretches: a 10% move over 60 days is a trend at 12% vol and
noise at 60%.

The two labels are also crossed: a 3 × 3 grid of volatility × trend cells
with the strategy's Sharpe in each, so "earns in calm markets" can be read
as "earns in calm *rising* markets" when that is what the numbers say.

Breakdown
---------
Per regime: how many bars, the strategy's Sharpe on those bars, its arithmetic
contribution to the total return, the hit rate, how much of the time it was in
the market, and the market's own Sharpe on the same bars for comparison.

The Sharpe here is the conventional mean-over-standard-deviation form scaled
by sqrt(252), not the compounded form the headline metric uses. Regime bars
are not contiguous — compounding a subset of scattered days would describe a
trade nobody could have made — while the arithmetic mean of those days'
returns is exactly what "how did the strategy do on high-vol days" means.
Contributions are arithmetic sums for the same reason; they add up to the
arithmetic total across regimes.

Pure pandas/numpy.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252
DEFAULT_WINDOW = 21
LABELS = ("low", "mid", "high")
# Below this many labelled bars a tercile has under ~one window of data in
# it and the per-regime Sharpe is noise about the sample, not the strategy.
MIN_BARS = 3 * DEFAULT_WINDOW
TREND_WINDOW = 60
TREND_SIGMA = 1.0
TRENDS = ("down", "flat", "up")
# A cell of the vol x trend grid with fewer bars than one vol window is
# reported by count only; its Sharpe would be a handful of days.
MIN_CELL_BARS = DEFAULT_WINDOW


def label_regimes(market_returns: pd.Series, window: int = DEFAULT_WINDOW) -> pd.DataFrame:
    """Realised vol per bar and its tercile label. Rows inside the first
    `window` bars have no label (NaN vol, label None)."""
    if window < 5:
        raise ValueError("window must be at least 5 bars")
    r = market_returns.astype(float)
    vol = r.rolling(window).std() * np.sqrt(TRADING_DAYS)
    valid = vol.dropna()
    labels = pd.Series([None] * len(r), index=r.index, dtype=object)
    thresholds = {"low_max": None, "high_min": None}
    if len(valid) >= MIN_BARS:
        lo, hi = valid.quantile([1 / 3, 2 / 3]).to_numpy()
        thresholds = {"low_max": round(float(lo), 6), "high_min": round(float(hi), 6)}
        labels.loc[valid.index] = np.where(
            valid <= lo, "low", np.where(valid > hi, "high", "mid")
        )
    out = pd.DataFrame({"realised_vol": vol, "regime": labels})
    out.attrs["thresholds"] = thresholds
    out.attrs["window"] = window
    return out


def label_trend(market_returns: pd.Series, window: int = TREND_WINDOW, sigma: float = TREND_SIGMA) -> pd.DataFrame:
    """Trailing-window market return, its t-statistic, and the `down` /
    `flat` / `up` label. Rows inside the first `window` bars have no label.
    A window with zero variance has no direction and reads `flat`."""
    if window < 20:
        raise ValueError("trend window must be at least 20 bars")
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    r = market_returns.astype(float)
    total = r.rolling(window).sum()
    sd = r.rolling(window).std()
    z = total / (sd * np.sqrt(window))
    z = z.where(sd > 0, 0.0).where(total.notna())
    ret = np.exp(np.log1p(r).rolling(window).sum()) - 1
    labels = pd.Series([None] * len(r), index=r.index, dtype=object)
    valid = z.dropna()
    labels.loc[valid.index] = np.where(valid > sigma, "up", np.where(valid < -sigma, "down", "flat"))
    out = pd.DataFrame({"trend_return": ret, "trend_z": z, "trend": labels})
    out.attrs["window"] = window
    out.attrs["sigma"] = sigma
    return out


def _sharpe(x: pd.Series) -> float:
    if len(x) < 2:
        return 0.0
    sd = float(x.std())
    return float(x.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


def _rows(labels, names, net, mkt, pos, labelled_bars, total, extra):
    """One breakdown row per label. `extra` maps a key to a per-bar series
    whose mean over the label's bars is reported under that key."""
    rows = {}
    for name in names:
        mask = (labels == name).to_numpy()
        n = int(mask.sum())
        if n == 0:
            rows[name] = {"bars": 0, "share_of_bars": 0.0}
            continue
        seg = net[mask]
        contribution = float(seg.sum())
        nonzero = seg[seg != 0]
        rows[name] = {
            "bars": n,
            "share_of_bars": round(n / labelled_bars, 6),
            "sharpe_ratio": round(_sharpe(seg), 6),
            "contribution": round(contribution, 6),
            # Share of the arithmetic total; undefined when the total is ~0,
            # where any share would be a division by noise.
            "share_of_return": round(contribution / total, 6) if abs(total) > 1e-9 else None,
            "hit_rate": round(float((nonzero > 0).mean()), 6) if len(nonzero) else 0.0,
            "time_in_market": round(float(pos[mask].abs().mean()), 6),
            "market_sharpe_ratio": round(_sharpe(mkt[mask]), 6),
            **{k: round(float(v[mask].mean()), 6) for k, v in extra.items()},
        }
    return rows


def _best_worst(rows):
    scored = {k: v for k, v in rows.items() if v["bars"] > 0}
    best = max(scored, key=lambda k: scored[k]["sharpe_ratio"])
    worst = min(scored, key=lambda k: scored[k]["sharpe_ratio"])
    return best, worst, round(scored[best]["sharpe_ratio"] - scored[worst]["sharpe_ratio"], 6)


def trend_breakdown(net_return, position, market_returns, window=TREND_WINDOW, sigma=TREND_SIGMA):
    """Strategy return broken down by the market's trend label."""
    labelled = label_trend(market_returns, window, sigma)
    frame = labelled.loc[net_return.index]
    trend = frame["trend"]
    labelled_bars = int(trend.notna().sum())
    if labelled_bars < MIN_BARS:
        return {
            "computable": False,
            "reason": (
                f"Fewer than {MIN_BARS} labelled bars — the period is too short to "
                f"label trend on a {window}-bar window."
            ),
        }
    net = net_return.astype(float)
    mkt = market_returns.loc[net.index].astype(float)
    pos = position.loc[net.index].astype(float)
    total = float(net[trend.notna()].sum())
    rows = _rows(trend, TRENDS, net, mkt, pos, labelled_bars, total,
                 extra={"mean_trend_return": frame["trend_return"], "mean_trend_z": frame["trend_z"]})
    best, worst, spread = _best_worst(rows)
    return {
        "computable": True,
        "window": window,
        "threshold_sigma": sigma,
        "labelled_bars": labelled_bars,
        "unlabelled_bars": int(len(net) - labelled_bars),
        "regimes": rows,
        "best_regime": best,
        "worst_regime": worst,
        "sharpe_spread": spread,
        "note": (
            f"A bar is 'up' or 'down' when the trailing {window}-day mean return "
            f"is more than {sigma:g} standard error from zero, else 'flat'. "
            "Fixed cut, not a tercile: flat means flat."
        ),
    }


def joint_breakdown(net_return, vol_labels, trend_labels):
    """Sharpe per volatility x trend cell. Cells with fewer than
    MIN_CELL_BARS bars report a count and a null Sharpe."""
    net = net_return.astype(float)
    vol = vol_labels.loc[net.index]
    trend = trend_labels.loc[net.index]
    both = vol.notna() & trend.notna()
    labelled_bars = int(both.sum())
    grid = {}
    scored = {}
    for v in LABELS:
        grid[v] = {}
        for t in TRENDS:
            mask = ((vol == v) & (trend == t)).to_numpy()
            n = int(mask.sum())
            cell = {"bars": n, "share_of_bars": round(n / labelled_bars, 6) if labelled_bars else 0.0}
            if n >= MIN_CELL_BARS:
                cell["sharpe_ratio"] = round(_sharpe(net[mask]), 6)
                cell["contribution"] = round(float(net[mask].sum()), 6)
                scored[(v, t)] = cell["sharpe_ratio"]
            else:
                cell["sharpe_ratio"] = None
                cell["contribution"] = round(float(net[mask].sum()), 6) if n else 0.0
            grid[v][t] = cell
    if not scored:
        return {"computable": False, "reason": f"No volatility x trend cell has {MIN_CELL_BARS} bars."}
    best = max(scored, key=scored.get)
    worst = min(scored, key=scored.get)
    return {
        "computable": True,
        "labelled_bars": labelled_bars,
        "min_cell_bars": MIN_CELL_BARS,
        "cells": grid,
        "best_cell": {"vol": best[0], "trend": best[1], "sharpe_ratio": scored[best]},
        "worst_cell": {"vol": worst[0], "trend": worst[1], "sharpe_ratio": scored[worst]},
        "sharpe_spread": round(scored[best] - scored[worst], 6),
        "scored_cells": len(scored),
    }


def regime_breakdown(
    net_return: pd.Series,
    position: pd.Series,
    market_returns: pd.Series,
    window: int = DEFAULT_WINDOW,
) -> dict:
    """Strategy return broken down by the market's volatility regime.

    `market_returns` may be longer than `net_return` (the labels are computed
    on the market series so the window never straddles a gap in the strategy
    series) and is aligned to `net_return`'s index.
    """
    labelled = label_regimes(market_returns, window)
    frame = labelled.loc[net_return.index]
    regime = frame["regime"]
    if regime.isna().all() or labelled.attrs["thresholds"]["low_max"] is None:
        return {
            "computable": False,
            "reason": (
                f"Fewer than {MIN_BARS} labelled bars — the period is too short to "
                f"split into volatility terciles on a {window}-bar window."
            ),
        }

    net = net_return.astype(float)
    mkt = market_returns.loc[net.index].astype(float)
    pos = position.loc[net.index].astype(float)
    labelled_bars = int(regime.notna().sum())
    total = float(net[regime.notna()].sum())

    rows = _rows(regime, LABELS, net, mkt, pos, labelled_bars, total,
                 extra={"mean_realised_vol": frame["realised_vol"]})

    best, worst, spread = _best_worst(rows)
    trend = trend_breakdown(net_return, position, market_returns)
    joint = (
        joint_breakdown(net_return, labelled["regime"], label_trend(market_returns)["trend"])
        if trend["computable"] else {"computable": False, "reason": trend["reason"]}
    )
    return {
        "computable": True,
        "window": window,
        "labelled_bars": labelled_bars,
        "unlabelled_bars": int(len(net) - labelled_bars),
        "thresholds": labelled.attrs["thresholds"],
        "regimes": rows,
        "best_regime": best,
        "worst_regime": worst,
        "sharpe_spread": spread,
        "note": (
            "Terciles are relative to this period. Sharpe per regime is "
            "mean/std x sqrt(252) over non-contiguous bars; contributions are "
            "arithmetic and sum to the arithmetic total."
        ),
        # The second axis: which way the market was going, and the two
        # labels crossed.
        "trend": trend,
        "joint": joint,
    }
