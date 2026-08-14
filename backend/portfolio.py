"""Multi-ticker portfolio construction — alignment, weighting, aggregation.

Runs one strategy across several tickers and combines the legs into a single
equity curve. Each leg is a complete backtest in its own right: its own signals,
its own stops, its own sizing, its own transaction costs. This module only
decides how the legs are lined up in time and how much of each you hold.

The two decisions that actually matter here are alignment and weighting, and
both are places where a portfolio backtest can quietly lie to you — see the
docstrings below.
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def align_closes(closes: dict[str, pd.Series]) -> pd.DataFrame:
    """Line up several close series on the dates they all share.

    An **inner** join, deliberately. The alternatives are worse:

    - Forward-filling a ticker that had no bar invents a price and, worse,
      invents a flat return on a day the asset did not trade — which lowers
      measured volatility and flatters every risk metric.
    - A union with gaps would let a leg contribute NaN to a weighted sum, and a
      portfolio return of NaN silently becomes zero downstream.

    The cost is real and must be surfaced: one ticker that listed late truncates
    the whole portfolio to its own history. The caller reports the effective
    range so that truncation is visible rather than mysterious.
    """
    if not closes:
        raise ValueError("No tickers supplied")

    frame = pd.DataFrame(closes).dropna(how="any")
    if frame.empty:
        raise ValueError(
            "These tickers share no overlapping trading days. They may trade on "
            "exchanges with different calendars, or one may have listed after "
            "the others' history ends."
        )
    return frame


def equal_weights(columns: list[str], index: pd.Index) -> pd.DataFrame:
    """Constant 1/N in every asset, on every bar.

    Constant weights mean the portfolio is rebalanced each bar back to target.
    That is a real trading decision, not a neutral one — it sells winners and
    buys losers daily — but it is the only weighting whose behaviour is fully
    described by the phrase "equal weight". Letting the weights drift instead
    would make the result depend on the start date in a way nobody intends.
    """
    n = len(columns)
    if n == 0:
        raise ValueError("No tickers to weight")
    return pd.DataFrame(1.0 / n, index=index, columns=columns)


def inverse_vol_weights(
    returns: pd.DataFrame,
    window: int = 60,
    max_weight: float = 1.0,
) -> pd.DataFrame:
    """Weight each asset by the inverse of its trailing volatility, normalised.

    Quiet assets get more of the book, turbulent ones less, so no single
    volatile leg dominates the portfolio's risk.

    The trailing window is shifted one bar before use — today's weights may only
    depend on volatility knowable as of yesterday's close, exactly like the
    signals and the position sizing.

    Warm-up bars have no volatility estimate yet, so they fall back to equal
    weight rather than to zero exposure: a portfolio that sits flat for the
    first `window` bars would silently shorten the period being measured.
    """
    if window < 2:
        raise ValueError("window must be at least 2 bars")
    if not 0 < max_weight <= 1:
        raise ValueError("max_weight must be between 0 and 1")

    n_assets = len(returns.columns)
    if max_weight * n_assets < 1.0:
        # e.g. 2 assets capped at 0.4 can hold at most 0.8 of a book. Silently
        # producing weights that sum to 0.8 would understate every return.
        raise ValueError(
            f"max_weight of {max_weight} cannot fill a book of {n_assets} "
            f"assets — it must be at least {1 / n_assets:.3f}."
        )

    vol = returns.rolling(window).std().shift(1)

    # A zero-volatility asset would take the entire book. Treat it as unknown
    # and let the equal-weight fallback handle that bar.
    inv = 1.0 / vol.replace(0.0, np.nan)
    total = inv.sum(axis=1)

    weights = inv.div(total, axis=0)

    # Any bar without a complete set of estimates falls back to equal weight.
    incomplete = weights.isna().any(axis=1) | (total <= 0)
    weights.loc[incomplete, :] = 1.0 / len(returns.columns)

    if max_weight < 1.0:
        weights = _cap_and_redistribute(weights, max_weight)

    return weights


def _cap_and_redistribute(weights: pd.DataFrame, max_weight: float) -> pd.DataFrame:
    """Hold every weight at or below `max_weight` while still summing to 1.

    Clipping alone leaves the book short. Clipping and then renormalising is
    worse than useless — dividing every weight by a sum below 1 scales the
    capped asset straight back up, so a 0.99 weight capped at 0.6 lands at 0.997
    and the cap has achieved nothing.

    The fix is to push the freed weight *out* to the assets that still have room,
    proportionally, and repeat — capping one asset can lift another over the
    limit. At most one asset can be newly capped per pass, so the column count
    bounds the loop.
    """
    capped = weights.copy()

    for _ in range(len(capped.columns)):
        over = capped > max_weight + 1e-12
        if not over.to_numpy().any():
            break

        capped = capped.clip(upper=max_weight)
        shortfall = 1.0 - capped.sum(axis=1)

        # Only assets strictly below the cap can absorb the freed weight.
        has_room = capped < max_weight - 1e-12
        room_mass = capped.where(has_room, 0.0).sum(axis=1)

        # Distribute in proportion to existing weight where there is any to
        # scale, and evenly across the assets with room when there is not
        # (every uncapped asset sitting at exactly zero).
        proportional = capped.where(has_room, 0.0).div(
            room_mass.replace(0.0, np.nan), axis=0
        )
        even = has_room.astype(float).div(
            has_room.sum(axis=1).replace(0, np.nan), axis=0
        )
        share = proportional.fillna(even).fillna(0.0)

        capped = capped + share.mul(shortfall, axis=0)

    return capped


def combine(
    leg_returns: pd.DataFrame,
    weights: pd.DataFrame,
) -> dict:
    """Aggregate weighted leg returns into a portfolio return and equity curve.

    `leg_returns` are already **net** of each leg's own transaction costs, so
    nothing further is deducted here.
    """
    if not leg_returns.columns.equals(weights.columns):
        raise ValueError("Leg returns and weights must cover the same tickers")

    aligned_weights = weights.reindex(leg_returns.index).fillna(0.0)

    contributions = leg_returns.fillna(0.0) * aligned_weights
    portfolio_return = contributions.sum(axis=1)

    equity = (1 + portfolio_return).cumprod()
    drawdown = (equity - equity.cummax()) / equity.cummax()

    return {
        "net_return": portfolio_return,
        "equity_curve": equity,
        "drawdown": drawdown,
        "contributions": contributions,
        "weights": aligned_weights,
    }


def contribution_summary(contributions: pd.DataFrame) -> dict[str, float]:
    """Each leg's additive share of the portfolio's total return.

    Summed arithmetically rather than compounded, so the parts add up to
    (approximately) the whole and can be compared against each other. It is an
    attribution, not a claim that any leg standalone returned this much.
    """
    return {col: float(contributions[col].sum()) for col in contributions.columns}


def diversification_ratio(
    leg_returns: pd.DataFrame,
    weights: pd.DataFrame,
    portfolio_return: pd.Series,
) -> float | None:
    """Weighted average leg volatility divided by portfolio volatility.

    1.0 means the legs move as one and the portfolio bought no diversification
    at all. Above 1.0 means their moves partly cancel. It is the single number
    that answers "was holding several of these actually worth it?".

    Returns **None** when the portfolio has no volatility, because the ratio is
    genuinely undefined there and the two ways it happens mean opposite things:
    legs that perfectly offset are maximally diversified (the ratio diverges),
    while legs that never moved are not diversified at all. Reporting 0.0 would
    read as "no diversification" and be flatly wrong in the first case.
    """
    leg_vol = leg_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    avg_weight = weights.mean()
    weighted_avg_vol = float((leg_vol * avg_weight).sum())

    port_vol = float(portfolio_return.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
    if port_vol == 0:
        return None
    return round(weighted_avg_vol / port_vol, 4)
