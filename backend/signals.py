"""Signal generation for every strategy — pure pandas, no external TA libraries.

Every generator ends with `.shift(1)`. A signal derived from a bar's close can
only be acted on at the next bar, and doing that shift in one place is what
keeps lookahead bias out of the whole engine.
"""

import pandas as pd


def compute_momentum(close: pd.Series, lookback: int) -> pd.Series:
    """Return rate-of-change momentum: close / close.shift(lookback) - 1."""
    return close / close.shift(lookback) - 1


def compute_moving_average(close: pd.Series, window: int) -> pd.Series:
    """Return simple rolling mean of close prices."""
    return close.rolling(window).mean()


def generate_signals(
    close: pd.Series,
    momentum_lookback: int,
    ma_window: int,
    momentum_threshold: float,
) -> pd.Series:
    """Generate long(+1)/short(-1)/flat(0) signals shifted by 1 to avoid lookahead bias."""
    momentum = compute_momentum(close, momentum_lookback)
    ma = compute_moving_average(close, ma_window)

    raw_signal = pd.Series(0, index=close.index)
    raw_signal[
        (momentum > momentum_threshold) & (close > ma)
    ] = 1
    raw_signal[
        (momentum < -momentum_threshold) & (close < ma)
    ] = -1

    return raw_signal.shift(1).fillna(0)


# ---------------------------------------------------------------------------
# MACD — trend following via the gap between two exponential averages
# ---------------------------------------------------------------------------


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (macd_line, signal_line, histogram).

    `adjust=False` gives the recursive EMA that charting packages use, so the
    numbers line up with what a user sees elsewhere.
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def generate_macd_signals(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    """Long while MACD sits above its signal line, short while below.

    This holds the crossover *state* rather than trading only the crossing bar,
    which keeps the position series continuous and comparable to the momentum
    strategy.
    """
    macd_line, signal_line, _ = compute_macd(close, fast, slow, signal_period)

    raw_signal = pd.Series(0, index=close.index)
    raw_signal[macd_line > signal_line] = 1
    raw_signal[macd_line < signal_line] = -1

    # An EMA emits a value from bar one, but the first `slow` bars are mostly
    # seeded by the initial price rather than by real history.
    warmup = min(slow, len(raw_signal))
    raw_signal.iloc[:warmup] = 0

    return raw_signal.shift(1).fillna(0)


# ---------------------------------------------------------------------------
# Bollinger Bands — mean reversion against a volatility envelope
# ---------------------------------------------------------------------------


def compute_bollinger(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return (middle_band, upper_band, lower_band)."""
    middle = close.rolling(window).mean()
    std = close.rolling(window).std()

    return middle, middle + num_std * std, middle - num_std * std


def generate_bollinger_signals(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> pd.Series:
    """Buy below the lower band, sell above the upper one.

    This is the deliberately literal mean-reversion rule: the position exists
    only while price sits outside the envelope, and closes as soon as it comes
    back inside. It is the opposite stance to momentum, which is the point —
    the two strategies should disagree on the same data.
    """
    _, upper, lower = compute_bollinger(close, window, num_std)

    raw_signal = pd.Series(0, index=close.index)
    raw_signal[close < lower] = 1
    raw_signal[close > upper] = -1

    return raw_signal.shift(1).fillna(0)
