"""Performance metrics — hand-checked values, not just shape assertions."""

import numpy as np
import pandas as pd
import pytest

from engine import compute_returns, apply_positions
from metrics import compute_metrics

METRIC_KEYS = {
    "total_return", "annualized_return", "annualized_volatility", "sharpe_ratio",
    "max_drawdown", "calmar_ratio", "win_rate", "profit_factor", "num_trades",
    "best_day", "worst_day", "avg_daily_return",
}


def series(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def metrics_for(close_values, position_values, cost=0.0):
    close = series(close_values)
    out = apply_positions(series(position_values), compute_returns(close), cost)
    return compute_metrics(
        out["net_return"].fillna(0), out["equity_curve"], out["drawdown"], out["position"]
    )


class TestShape:
    def test_returns_all_twelve_metrics(self):
        m = metrics_for([100, 110, 105, 115], [1, 1, 1, 1])
        assert set(m.keys()) == METRIC_KEYS

    def test_floats_rounded_to_six_places(self):
        m = metrics_for([100, 103, 101, 107], [1, 1, 1, 1])
        for k, v in m.items():
            if isinstance(v, float):
                assert v == round(v, 6), f"{k} not rounded"


class TestKnownValues:
    def test_total_return_matches_final_equity(self):
        m = metrics_for([100, 110, 121], [1, 1, 1])
        assert m["total_return"] == pytest.approx(0.21, abs=1e-6)

    def test_flat_strategy_is_all_zeros(self):
        m = metrics_for([100, 120, 90, 130], [0, 0, 0, 0])
        assert m["total_return"] == pytest.approx(0.0)
        assert m["max_drawdown"] == pytest.approx(0.0)
        assert m["num_trades"] == 0
        assert m["sharpe_ratio"] == pytest.approx(0.0)

    def test_max_drawdown_is_negative_on_a_loss(self):
        m = metrics_for([100, 120, 60], [1, 1, 1])
        assert m["max_drawdown"] == pytest.approx(-0.5)

    def test_num_trades_counts_position_changes(self):
        # 0 -> 1 -> 1 -> -1 -> 0 is three changes.
        m = metrics_for([100] * 5, [0, 1, 1, -1, 0])
        assert m["num_trades"] == 3

    def test_best_and_worst_day_bracket_all_returns(self):
        m = metrics_for([100, 110, 99, 105], [1, 1, 1, 1])
        assert m["best_day"] >= m["avg_daily_return"] >= m["worst_day"]


class TestWinRateAndProfitFactor:
    def test_win_rate_ignores_flat_days(self):
        # Active days: +10%, -10%, +10% -> 2 of 3 wins.
        m = metrics_for([100, 110, 99, 108.9, 108.9], [1, 1, 1, 1, 0])
        assert m["win_rate"] == pytest.approx(2 / 3, abs=1e-6)

    def test_all_winning_days_give_win_rate_one(self):
        m = metrics_for([100, 105, 110, 115], [1, 1, 1, 1])
        assert m["win_rate"] == pytest.approx(1.0)

    def test_profit_factor_above_one_when_gains_exceed_losses(self):
        m = metrics_for([100, 120, 115, 140], [1, 1, 1, 1])
        assert m["profit_factor"] > 1.0

    def test_profit_factor_zero_when_there_are_no_losses(self):
        # Guard branch: no negative returns means no denominator.
        m = metrics_for([100, 105, 110], [1, 1, 1])
        assert m["profit_factor"] == 0.0


class TestRatios:
    def test_sharpe_zero_when_volatility_is_zero(self):
        m = metrics_for([100] * 6, [1] * 6)
        assert m["sharpe_ratio"] == 0.0

    def test_calmar_zero_when_no_drawdown(self):
        m = metrics_for([100, 105, 110], [1, 1, 1])
        assert m["calmar_ratio"] == 0.0

    def test_sharpe_sign_follows_return_sign(self):
        rng = np.random.default_rng(3)
        up = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.01, 260)))
        m = metrics_for(list(up), [1] * 260)
        assert m["total_return"] > 0
        assert m["sharpe_ratio"] > 0
