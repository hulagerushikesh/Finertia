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


def _sharpe(x: pd.Series) -> float:
    if len(x) < 2:
        return 0.0
    sd = float(x.std())
    return float(x.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else 0.0


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

    rows = {}
    for name in LABELS:
        mask = (regime == name).to_numpy()
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
            "mean_realised_vol": round(float(frame["realised_vol"][mask].mean()), 6),
        }

    scored = {k: v for k, v in rows.items() if v["bars"] > 0}
    best = max(scored, key=lambda k: scored[k]["sharpe_ratio"])
    worst = min(scored, key=lambda k: scored[k]["sharpe_ratio"])
    return {
        "computable": True,
        "window": window,
        "labelled_bars": labelled_bars,
        "unlabelled_bars": int(len(net) - labelled_bars),
        "thresholds": labelled.attrs["thresholds"],
        "regimes": rows,
        "best_regime": best,
        "worst_regime": worst,
        "sharpe_spread": round(scored[best]["sharpe_ratio"] - scored[worst]["sharpe_ratio"], 6),
        "note": (
            "Terciles are relative to this period. Sharpe per regime is "
            "mean/std x sqrt(252) over non-contiguous bars; contributions are "
            "arithmetic and sum to the arithmetic total."
        ),
    }
