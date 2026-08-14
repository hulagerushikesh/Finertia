"""Position application, transaction costs, equity curve, drawdown, benchmark."""

import numpy as np
import pandas as pd
import pytest

from engine import compute_returns, apply_positions, compute_benchmark


def series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


class TestReturns:
    def test_percentage_change(self):
        r = compute_returns(series([100, 110, 99]))
        assert np.isnan(r.iloc[0])
        assert r.iloc[1] == pytest.approx(0.10)
        assert r.iloc[2] == pytest.approx(-0.10)


class TestEquityCurve:
    def test_starts_at_exactly_one(self):
        close = series([100, 101, 102, 103])
        out = apply_positions(series([0, 1, 1, 1]), compute_returns(close), 0.0)
        assert out["equity_curve"].iloc[0] == pytest.approx(1.0)

    def test_flat_position_never_moves_equity(self):
        close = series([100, 120, 80, 95])
        out = apply_positions(series([0, 0, 0, 0]), compute_returns(close), 0.001)
        assert out["equity_curve"].eq(1.0).all()

    def test_long_position_compounds_returns(self):
        close = series([100, 110, 121])  # +10%, +10%
        out = apply_positions(series([1, 1, 1]), compute_returns(close), 0.0)
        assert out["equity_curve"].iloc[-1] == pytest.approx(1.21)

    def test_short_position_profits_when_price_falls(self):
        close = series([100, 90])  # -10%
        out = apply_positions(series([-1, -1]), compute_returns(close), 0.0)
        assert out["equity_curve"].iloc[-1] == pytest.approx(1.10)


class TestTransactionCosts:
    def test_cost_deducted_only_when_position_changes(self):
        close = series([100, 100, 100, 100])
        # Position changes at index 1 only.
        out = apply_positions(series([0, 1, 1, 1]), compute_returns(close), 0.01)
        net = out["net_return"]
        assert net.iloc[1] == pytest.approx(-0.01)
        assert net.iloc[2] == pytest.approx(0.0)
        assert net.iloc[3] == pytest.approx(0.0)

    def test_more_flipping_costs_more(self):
        close = series([100] * 8)
        rets = compute_returns(close)
        steady = apply_positions(series([1] * 8), rets, 0.01)["equity_curve"].iloc[-1]
        flippy = apply_positions(series([1, -1, 1, -1, 1, -1, 1, -1]), rets, 0.01)["equity_curve"].iloc[-1]
        assert flippy < steady

    def test_a_short_to_long_flip_costs_two_trades(self):
        # Closing a short and opening a long is twice the turnover of going
        # flat to long. A flat per-change charge would understate it by half.
        close = series([100, 100])
        out = apply_positions(series([-1, 1]), compute_returns(close), 0.01)
        assert out["net_return"].iloc[1] == pytest.approx(-0.02)

    def test_cost_scales_with_the_size_of_the_change(self):
        # Volatility targeting nudges the position by fractions; billing a full
        # round trip for a 2% adjustment would bury the sizing rule.
        close = series([100, 100])
        out = apply_positions(series([0.50, 0.52]), compute_returns(close), 0.01)
        assert out["net_return"].iloc[1] == pytest.approx(-0.0002)

    def test_opening_on_the_first_bar_is_charged(self):
        # diff() has no prior bar, so bar 0 is measured from flat rather than
        # silently costing nothing.
        close = series([100, 100])
        out = apply_positions(series([1, 1]), compute_returns(close), 0.01)
        assert out["net_return"].iloc[0] == pytest.approx(-0.01)

    def test_holding_flat_from_the_start_costs_nothing(self):
        close = series([100, 100])
        out = apply_positions(series([0, 0]), compute_returns(close), 0.01)
        assert out["net_return"].iloc[0] == pytest.approx(0.0)

    def test_zero_cost_leaves_gross_equal_to_net(self):
        close = series([100, 105, 103, 108])
        out = apply_positions(series([1, 1, 0, 1]), compute_returns(close), 0.0)
        pd.testing.assert_series_equal(
            out["gross_return"].fillna(0), out["net_return"].fillna(0), check_names=False
        )


class TestDrawdown:
    def test_never_positive(self):
        rng = np.random.default_rng(1)
        close = series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 300))))
        out = apply_positions(series(rng.choice([-1, 0, 1], 300)), compute_returns(close), 0.001)
        assert (out["drawdown"] <= 1e-12).all()

    def test_zero_while_making_new_highs(self):
        close = series([100, 110, 120, 130])
        out = apply_positions(series([1, 1, 1, 1]), compute_returns(close), 0.0)
        assert out["drawdown"].abs().max() == pytest.approx(0.0)

    def test_matches_hand_computed_trough(self):
        # Long through +20% then -50%: peak 1.2, trough 0.6 -> -50% drawdown.
        close = series([100, 120, 60])
        out = apply_positions(series([1, 1, 1]), compute_returns(close), 0.0)
        assert out["drawdown"].min() == pytest.approx(-0.5)


class TestBenchmark:
    def test_tracks_price_growth(self):
        bench = compute_benchmark(series([100, 110, 121]))
        assert bench.iloc[0] == pytest.approx(1.0)
        assert bench.iloc[-1] == pytest.approx(1.21)

    def test_independent_of_strategy_positions(self):
        close = series([100, 105, 110])
        assert compute_benchmark(close).iloc[-1] == pytest.approx(1.10)
