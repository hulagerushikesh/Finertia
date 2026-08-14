"""Signal generation — momentum, moving average, and the lookahead-bias guard."""

import numpy as np
import pandas as pd
import pytest

from signals import compute_momentum, compute_moving_average, generate_signals


def series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


class TestMomentum:
    def test_rate_of_change_over_lookback(self):
        # 100 -> 110 across a 2-bar lookback is +10%.
        s = series([100, 105, 110, 120])
        mom = compute_momentum(s, lookback=2)
        assert mom.iloc[2] == pytest.approx(0.10)
        assert mom.iloc[3] == pytest.approx(120 / 105 - 1)

    def test_first_lookback_bars_are_nan(self):
        s = series([100, 101, 102, 103])
        mom = compute_momentum(s, lookback=2)
        assert mom.iloc[:2].isna().all()

    def test_negative_momentum_on_decline(self):
        s = series([100, 90, 80])
        assert compute_momentum(s, lookback=2).iloc[2] == pytest.approx(-0.20)


class TestMovingAverage:
    def test_rolling_mean(self):
        s = series([10, 20, 30, 40])
        ma = compute_moving_average(s, window=3)
        assert ma.iloc[2] == pytest.approx(20.0)
        assert ma.iloc[3] == pytest.approx(30.0)

    def test_window_minus_one_bars_are_nan(self):
        ma = compute_moving_average(series([1, 2, 3, 4, 5]), window=3)
        assert ma.iloc[:2].isna().all()


class TestLookaheadBias:
    """The single most important property of the whole engine."""

    def test_signal_is_previous_bars_decision(self):
        prices = series(list(np.linspace(100, 200, 60)))
        sig = generate_signals(prices, momentum_lookback=5, ma_window=10, momentum_threshold=0.01)

        # Reconstruct the unshifted decision and assert the output lags it by one.
        mom = compute_momentum(prices, 5)
        ma = compute_moving_average(prices, 10)
        raw = pd.Series(0, index=prices.index)
        raw[(mom > 0.01) & (prices > ma)] = 1
        raw[(mom < -0.01) & (prices < ma)] = -1

        pd.testing.assert_series_equal(sig, raw.shift(1).fillna(0), check_dtype=False)

    def test_cannot_trade_a_spike_on_the_spike_day(self):
        # Flat, then one enormous jump. A lookahead bug would go long ON the jump.
        prices = series([100] * 30 + [400] + [400] * 10)
        sig = generate_signals(prices, momentum_lookback=5, ma_window=10, momentum_threshold=0.05)
        spike_idx = 30
        assert sig.iloc[spike_idx] == 0, "position was open on the spike bar — lookahead bias"

    def test_first_bar_is_always_flat(self):
        sig = generate_signals(series(list(range(100, 160))), 5, 10, 0.01)
        assert sig.iloc[0] == 0


class TestSignalValues:
    def test_only_emits_minus_one_zero_or_one(self):
        rng = np.random.default_rng(0)
        prices = series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 200))))
        sig = generate_signals(prices, 20, 50, 0.02)
        assert set(sig.unique()).issubset({-1.0, 0.0, 1.0})

    def test_uptrend_goes_long(self):
        prices = series(list(np.linspace(100, 300, 80)))
        sig = generate_signals(prices, 10, 20, 0.02)
        assert (sig == 1).sum() > 0
        assert (sig == -1).sum() == 0

    def test_downtrend_goes_short(self):
        prices = series(list(np.linspace(300, 100, 80)))
        sig = generate_signals(prices, 10, 20, 0.02)
        assert (sig == -1).sum() > 0
        assert (sig == 1).sum() == 0

    def test_high_threshold_suppresses_all_trades(self):
        prices = series(list(np.linspace(100, 110, 80)))
        sig = generate_signals(prices, 10, 20, momentum_threshold=5.0)
        assert (sig == 0).all()
