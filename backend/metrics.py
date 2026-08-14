"""Performance metrics — pure numpy/pandas, no external libraries."""

import pandas as pd


def compute_metrics(
    net_return: pd.Series,
    equity_curve: pd.Series,
    drawdown: pd.Series,
    position: pd.Series,
) -> dict:
    """Compute all performance metrics and return as a flat dict rounded to 6 dp."""
    total_return = float(equity_curve.iloc[-1] - 1)
    n = len(net_return)

    annualized_return = float((1 + total_return) ** (252 / n) - 1) if n > 0 else 0.0
    annualized_volatility = float(net_return.std() * (252 ** 0.5))

    sharpe_ratio = (
        annualized_return / annualized_volatility
        if annualized_volatility != 0
        else 0.0
    )

    max_drawdown = float(drawdown.min())
    calmar_ratio = (
        annualized_return / abs(max_drawdown)
        if max_drawdown != 0
        else 0.0
    )

    non_zero = net_return[net_return != 0]
    win_rate = float((non_zero > 0).sum() / max(len(non_zero), 1))

    positive_returns = net_return[net_return > 0]
    negative_returns = net_return[net_return < 0]
    profit_factor = (
        float(positive_returns.sum() / abs(negative_returns.sum()))
        if len(negative_returns) > 0 and negative_returns.sum() != 0
        else 0.0
    )

    num_trades = int((position.diff().abs() > 0).sum())
    best_day = float(net_return.max())
    worst_day = float(net_return.min())
    avg_daily_return = float(net_return.mean())

    raw = {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "num_trades": num_trades,
        "best_day": best_day,
        "worst_day": worst_day,
        "avg_daily_return": avg_daily_return,
    }

    return {k: round(v, 6) if isinstance(v, float) else v for k, v in raw.items()}
