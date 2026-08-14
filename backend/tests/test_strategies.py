"""MACD and Bollinger signal generation, plus the strategy registry."""

import numpy as np
import pandas as pd
import pytest

from signals import (
    compute_macd,
    compute_bollinger,
    generate_macd_signals,
    generate_bollinger_signals,
)
from strategies import (
    STRATEGIES,
    STRATEGY_NAMES,
    build_positions,
    longest_window,
    param_grid,
)


def series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def trending(n=200, slope=1.0, start_price=100.0):
    return series([start_price + slope * i for i in range(n)])


def noisy(n=300, seed=0, vol=0.015):
    rng = np.random.default_rng(seed)
    return series(100 * np.exp(np.cumsum(rng.normal(0, vol, n))))


class TestMacdMath:
    def test_returns_three_aligned_series(self):
        close = trending(100)
        macd, signal, hist = compute_macd(close)
        assert len(macd) == len(signal) == len(hist) == len(close)
        assert macd.index.equals(close.index)

    def test_histogram_is_line_minus_signal(self):
        macd, signal, hist = compute_macd(noisy(200))
        pd.testing.assert_series_equal(hist, macd - signal, check_names=False)

    def test_positive_in_a_sustained_uptrend(self):
        # Fast EMA leads slow EMA when price is rising.
        macd, _, _ = compute_macd(trending(200, slope=1.0))
        assert macd.iloc[-1] > 0

    def test_negative_in_a_sustained_downtrend(self):
        macd, _, _ = compute_macd(trending(200, slope=-1.0, start_price=400))
        assert macd.iloc[-1] < 0

    def test_flat_prices_give_zero_macd(self):
        macd, _, _ = compute_macd(series([100.0] * 120))
        assert macd.iloc[-1] == pytest.approx(0.0, abs=1e-9)

    def test_custom_periods_change_the_result(self):
        close = noisy(200)
        a, _, _ = compute_macd(close, 12, 26, 9)
        b, _, _ = compute_macd(close, 5, 35, 9)
        assert not np.allclose(a.to_numpy(), b.to_numpy())


class TestMacdSignals:
    def test_only_emits_valid_positions(self):
        sig = generate_macd_signals(noisy(300))
        assert set(sig.unique()).issubset({-1.0, 0.0, 1.0})

    def test_warmup_bars_are_flat(self):
        sig = generate_macd_signals(noisy(300), fast=12, slow=26, signal_period=9)
        assert (sig.iloc[:26] == 0).all()

    def test_goes_long_in_an_uptrend(self):
        sig = generate_macd_signals(trending(200, slope=1.0))
        assert (sig == 1).sum() > 0
        assert (sig == -1).sum() == 0

    def test_goes_short_in_a_downtrend(self):
        sig = generate_macd_signals(trending(200, slope=-1.0, start_price=400))
        assert (sig == -1).sum() > 0
        assert (sig == 1).sum() == 0

    def test_shifted_to_prevent_lookahead(self):
        close = noisy(200)
        macd, signal_line, _ = compute_macd(close)
        raw = pd.Series(0, index=close.index)
        raw[macd > signal_line] = 1
        raw[macd < signal_line] = -1
        raw.iloc[:26] = 0
        pd.testing.assert_series_equal(
            generate_macd_signals(close), raw.shift(1).fillna(0), check_dtype=False
        )

    def test_holds_position_rather_than_trading_only_crossings(self):
        # Crossover state means long stretches, not isolated one-bar trades.
        sig = generate_macd_signals(trending(200, slope=1.0))
        assert (sig != 0).sum() > 100


class TestBollingerMath:
    def test_bands_bracket_the_middle(self):
        mid, upper, lower = compute_bollinger(noisy(200), window=20, num_std=2.0)
        valid = mid.notna()
        assert (upper[valid] >= mid[valid]).all()
        assert (lower[valid] <= mid[valid]).all()

    def test_middle_band_is_the_rolling_mean(self):
        close = noisy(100)
        mid, _, _ = compute_bollinger(close, window=20)
        pd.testing.assert_series_equal(mid, close.rolling(20).mean(), check_names=False)

    def test_wider_num_std_widens_the_envelope(self):
        close = noisy(200)
        _, u2, l2 = compute_bollinger(close, 20, 2.0)
        _, u3, l3 = compute_bollinger(close, 20, 3.0)
        assert (u3.dropna() >= u2.dropna()).all()
        assert (l3.dropna() <= l2.dropna()).all()

    def test_flat_prices_collapse_the_bands(self):
        mid, upper, lower = compute_bollinger(series([100.0] * 60), window=20)
        assert upper.iloc[-1] == pytest.approx(mid.iloc[-1])
        assert lower.iloc[-1] == pytest.approx(mid.iloc[-1])


class TestBollingerSignals:
    def test_only_emits_valid_positions(self):
        sig = generate_bollinger_signals(noisy(300))
        assert set(sig.unique()).issubset({-1.0, 0.0, 1.0})

    def test_buys_below_the_lower_band(self):
        # Steady prices then a sharp drop pushes close under the lower band.
        close = series([100.0] * 40 + [80.0] + [100.0] * 10)
        sig = generate_bollinger_signals(close, window=20, num_std=2.0)
        assert (sig == 1).sum() > 0

    def test_sells_above_the_upper_band(self):
        close = series([100.0] * 40 + [130.0] + [100.0] * 10)
        sig = generate_bollinger_signals(close, window=20, num_std=2.0)
        assert (sig == -1).sum() > 0

    def test_mostly_flat_because_it_only_trades_extremes(self):
        sig = generate_bollinger_signals(noisy(500, seed=1), window=20, num_std=2.0)
        assert (sig == 0).mean() > 0.7

    def test_shifted_to_prevent_lookahead(self):
        close = noisy(200)
        _, upper, lower = compute_bollinger(close, 20, 2.0)
        raw = pd.Series(0, index=close.index)
        raw[close < lower] = 1
        raw[close > upper] = -1
        pd.testing.assert_series_equal(
            generate_bollinger_signals(close), raw.shift(1).fillna(0), check_dtype=False
        )


class TestOppositeStances:
    def test_momentum_and_bollinger_disagree_on_a_trend(self):
        # A strong uptrend: momentum rides it, mean reversion fades it.
        close = trending(200, slope=1.5)
        mom = build_positions(close, "momentum", {"momentum_lookback": 10, "ma_window": 20})
        boll = build_positions(close, "bollinger", {"bb_window": 20, "bb_std": 2.0})
        assert (mom == 1).sum() > 0
        assert (boll == 1).sum() == 0  # never buys a market making new highs


class TestRegistry:
    def test_every_registered_strategy_builds_positions(self):
        close = noisy(300)
        for name in STRATEGY_NAMES:
            pos = build_positions(close, name, {})
            assert len(pos) == len(close)
            assert set(pos.unique()).issubset({-1.0, 0.0, 1.0})

    def test_unknown_strategy_names_the_valid_options(self):
        with pytest.raises(ValueError, match="momentum"):
            build_positions(noisy(50), "not_a_strategy", {})

    def test_empty_params_fall_back_to_defaults(self):
        close = noisy(300)
        pd.testing.assert_series_equal(
            build_positions(close, "momentum", {}),
            build_positions(close, "momentum", {"momentum_lookback": 20, "ma_window": 50,
                                                "momentum_threshold": 0.02}),
        )

    def test_none_params_are_tolerated(self):
        assert len(build_positions(noisy(100), "macd", None)) == 100

    def test_longest_window_reflects_the_parameters(self):
        assert longest_window("momentum", {"momentum_lookback": 10, "ma_window": 200}) == 200
        assert longest_window("macd", {"macd_slow": 26, "macd_signal": 9}) == 35
        assert longest_window("bollinger", {"bb_window": 30}) == 30

    def test_every_strategy_has_a_non_empty_grid(self):
        for name in STRATEGY_NAMES:
            grid = param_grid(name)
            assert len(grid) > 0
            assert all(isinstance(combo, dict) for combo in grid)

    def test_grid_is_a_copy_so_callers_cannot_mutate_the_registry(self):
        grid = param_grid("momentum")
        original = len(grid)
        grid.append({"bogus": 1})
        assert len(param_grid("momentum")) == original

    def test_registry_exposes_a_label_for_each_strategy(self):
        for name in STRATEGY_NAMES:
            assert STRATEGIES[name]["label"]
