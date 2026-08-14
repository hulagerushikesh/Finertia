"""Risk overlays — stop-loss / take-profit and volatility-targeted sizing.

These sit between signal generation and the engine: signals decide *direction*,
this module decides *whether to stay in* and *how large*. Keeping them separate
means every strategy gets stops and sizing for free, and neither one has to know
what the other does.

Unlike the rest of the engine, stops are genuinely path-dependent — whether you
are still in a trade on Tuesday depends on what happened Monday — so that part
is an explicit loop rather than a vectorised expression. It is O(n) over a few
thousand bars, which costs nothing measurable.
"""

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def apply_stops(
    position: pd.Series,
    returns: pd.Series,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> pd.Series:
    """Flatten a position once its return since entry breaches a limit.

    `stop_loss` and `take_profit` are positive fractions of the entry price
    (0.05 = 5%). Either may be None to disable that side.

    Two behaviours worth being explicit about:

    1. **Exits are evaluated at the close.** If a bar moves -10% against a 5%
       stop, the full -10% is taken and the exit happens at that close. Claiming
       the stop filled at exactly -5% would need intraday data and would flatter
       every result — a backtest that fills stops at the trigger price is one of
       the most common ways to manufacture an edge that does not exist.

    2. **A stopped-out trade does not re-enter on the same signal.** The position
       stays flat until the underlying signal actually changes, otherwise the
       next bar would re-enter immediately and the stop would achieve nothing
       beyond paying an extra round of costs.
    """
    if stop_loss is None and take_profit is None:
        return position

    if stop_loss is not None and stop_loss <= 0:
        raise ValueError("stop_loss must be a positive fraction, e.g. 0.05 for 5%")
    if take_profit is not None and take_profit <= 0:
        raise ValueError("take_profit must be a positive fraction, e.g. 0.10 for 10%")

    pos_values = position.to_numpy(dtype=float)
    ret_values = np.nan_to_num(returns.to_numpy(dtype=float), nan=0.0)

    out = np.zeros_like(pos_values)
    active = 0.0        # the signal we are currently trading
    equity = 1.0        # growth of the position since entry
    locked = False      # stopped out of the current signal run

    for i in range(len(pos_values)):
        signal = pos_values[i]

        if signal != active:
            # A fresh signal clears the lock — this is a different trade.
            active = signal
            equity = 1.0
            locked = False

        if signal == 0 or locked:
            out[i] = 0.0
            continue

        out[i] = signal

        # The bar's return is realised first, then the limit is checked. The
        # exit therefore takes effect from the *next* bar.
        equity *= 1 + signal * ret_values[i]
        pnl = equity - 1.0

        if stop_loss is not None and pnl <= -stop_loss:
            locked = True
        elif take_profit is not None and pnl >= take_profit:
            locked = True

    return pd.Series(out, index=position.index)


def volatility_target_size(
    returns: pd.Series,
    target_vol: float = 0.15,
    window: int = 20,
    max_leverage: float = 2.0,
) -> pd.Series:
    """Scale exposure so realised volatility sits near `target_vol` annualised.

    Sizing is `target / trailing_realised`, capped at `max_leverage`. The
    trailing window is shifted one bar: sizing today may only use volatility
    measured up to yesterday's close, exactly like the signals.

    Warm-up bars, and any bar where trailing volatility is zero (a flat price
    run), size to zero rather than to infinity.
    """
    if target_vol <= 0:
        raise ValueError("target_vol must be positive")
    if max_leverage <= 0:
        raise ValueError("max_leverage must be positive")
    if window < 2:
        raise ValueError("window must be at least 2 bars")

    realised = returns.rolling(window).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    # Shift first, then divide — sizing on today's own volatility would be
    # using a number that is not knowable until the bar closes.
    realised = realised.shift(1)

    size = target_vol / realised.replace(0.0, np.nan)
    return size.clip(upper=max_leverage).fillna(0.0)


def size_positions(
    position: pd.Series,
    returns: pd.Series,
    sizing: str = "fixed",
    target_vol: float = 0.15,
    vol_window: int = 20,
    max_leverage: float = 2.0,
) -> pd.Series:
    """Return the position series scaled by the chosen sizing rule.

    "fixed" is the original behaviour — full exposure whenever a signal is on.
    """
    if sizing == "fixed":
        return position
    if sizing == "vol_target":
        return position * volatility_target_size(
            returns, target_vol=target_vol, window=vol_window, max_leverage=max_leverage
        )
    raise ValueError(f"Unknown sizing rule '{sizing}'. Use 'fixed' or 'vol_target'.")
