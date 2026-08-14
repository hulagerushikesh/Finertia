"""Time-sliced views of a completed backtest — monthly, annual, and rolling.

The headline metrics compress a whole run into single numbers. These functions
put the time axis back: which months hurt, which years beat the benchmark, and
whether risk-adjusted performance was steady or came from one lucky stretch.

Pure pandas/numpy, consistent with the rest of the engine.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _compound(returns: pd.Series) -> float:
    """Total return of a period, compounded rather than summed."""
    return float((1 + returns).prod() - 1)


def monthly_returns(net_return: pd.Series) -> list[dict]:
    """Compounded return for each calendar month present in the series."""
    if net_return.empty:
        return []

    grouped = net_return.groupby([net_return.index.year, net_return.index.month])
    return [
        {"year": int(year), "month": int(month), "return": round(_compound(vals), 6)}
        for (year, month), vals in grouped
    ]


def annual_returns(net_return: pd.Series, benchmark_return: pd.Series) -> list[dict]:
    """Strategy vs buy-and-hold, compounded per calendar year."""
    if net_return.empty:
        return []

    strat = net_return.groupby(net_return.index.year).apply(_compound)
    bench = benchmark_return.groupby(benchmark_return.index.year).apply(_compound)

    return [
        {
            "year": int(year),
            "strategy": round(float(strat.loc[year]), 6),
            "benchmark": round(float(bench.loc[year]), 6) if year in bench.index else 0.0,
        }
        for year in strat.index
    ]


def rolling_sharpe(net_return: pd.Series, window: int = 60) -> list[dict]:
    """Annualised Sharpe over a trailing window, one point per bar.

    Uses the conventional rolling form — mean over standard deviation, scaled by
    sqrt(252). That differs from the headline Sharpe in metrics.py, which divides
    an annualised *compounded* return by annualised volatility. Over a 60-bar
    window the compounded form is dominated by noise, so the mean-based version
    is the one that actually reads as a trend.
    """
    if len(net_return) < window:
        return []

    mean = net_return.rolling(window).mean()
    std = net_return.rolling(window).std()
    sharpe = (mean / std) * np.sqrt(TRADING_DAYS)
    sharpe = sharpe.replace([np.inf, -np.inf], np.nan)

    return [
        {"date": idx.strftime("%Y-%m-%d"), "value": round(float(val), 6)}
        for idx, val in sharpe.items()
        if pd.notna(val)
    ]
