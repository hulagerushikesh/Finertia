"""Position sizing, equity curve, and benchmark computation — pure pandas/numpy."""

import pandas as pd


def compute_returns(close: pd.Series) -> pd.Series:
    """Return daily percentage returns from close prices."""
    return close.pct_change()


def apply_positions(
    signals: pd.Series,
    returns: pd.Series,
    transaction_cost: float,
) -> dict:
    """Apply positions to returns, deduct transaction costs, compute equity and drawdown."""
    position = signals

    # Cost is charged on *turnover*, not on the fact that something changed.
    # Two reasons it has to be proportional:
    #   - Flipping -1 → +1 closes a short and opens a long. That is two trades'
    #     worth of turnover, so a flat charge understates it by half.
    #   - Volatility-targeted sizing moves the position by small fractions most
    #     bars. A flat charge would bill a full round trip for a 2% adjustment
    #     and make the sizing rule look far worse than it is.
    # For plain 0 → ±1 signals |Δ| is 1, so this is identical to a flat charge.
    turnover = position.diff().abs()
    # diff() has no prior bar to compare against, so bar 0 is measured from flat.
    turnover.iloc[0] = abs(position.iloc[0])

    trade_occurred = turnover > 0

    # The first bar has no prior close, so pct_change leaves it NaN. Treating it
    # as flat matters because otherwise NaN - cost = NaN, and an entry cost
    # booked on bar 0 would vanish instead of being charged. Every real signal
    # series is flat at bar 0 anyway (generators zero their warm-up), so this
    # only bites on hand-constructed positions — but silently losing a cost is
    # exactly the kind of thing that makes a backtest look better than it is.
    gross_return = position * returns.fillna(0.0)
    net_return = gross_return - turnover * transaction_cost

    # The first bar's return is NaN (pct_change has no prior close), so fill it
    # to 0 — that anchors the equity curve at exactly 1.0 on day one.
    equity_curve = (1 + net_return.fillna(0)).cumprod()

    drawdown = (equity_curve - equity_curve.cummax()) / equity_curve.cummax()

    return {
        "position": position,
        "trade_occurred": trade_occurred,
        "gross_return": gross_return,
        "net_return": net_return,
        "equity_curve": equity_curve,
        "drawdown": drawdown,
    }


def compute_benchmark(close: pd.Series) -> pd.Series:
    """Return buy-and-hold equity curve normalised to start at 1.0."""
    pct = close.pct_change().fillna(0)
    return (1 + pct).cumprod()
