"""Risk overlay tests — stops and volatility-targeted sizing.

Series are hand-built so every expected exit bar can be reasoned about by hand
rather than compared against whatever the implementation happened to produce.
"""

import numpy as np
import pandas as pd
import pytest

from risk import apply_stops, volatility_target_size, size_positions


def series(values):
    idx = pd.date_range("2022-01-03", periods=len(values), freq="B")
    return pd.Series(values, index=idx, dtype=float)


class TestStopsDisabled:
    def test_returns_the_position_untouched_when_both_limits_are_none(self):
        pos = series([1, 1, -1, 0, 1])
        out = apply_stops(pos, series([0.01] * 5))
        pd.testing.assert_series_equal(out, pos)

    def test_a_position_that_never_breaches_is_unchanged(self):
        pos = series([1] * 6)
        out = apply_stops(pos, series([0.005] * 6), stop_loss=0.10)
        assert out.tolist() == [1] * 6


class TestStopLoss:
    def test_exits_the_bar_after_the_breach(self):
        # -3% then -3% compounds to -5.91%, breaching a 5% stop on bar 1.
        pos = series([1, 1, 1, 1])
        rets = series([-0.03, -0.03, -0.03, -0.03])
        out = apply_stops(pos, rets, stop_loss=0.05)
        assert out.tolist() == [1, 1, 0, 0], "should hold through the breaching bar, then flatten"

    def test_the_breaching_bar_return_is_still_taken(self):
        # The exit is at the close, so the full adverse move is realised. A
        # backtest that fills at exactly -5% would be flattering itself.
        pos = series([1, 1, 1])
        out = apply_stops(pos, series([-0.20, 0.0, 0.0]), stop_loss=0.05)
        assert out.iloc[0] == 1

    def test_short_positions_stop_on_a_rally(self):
        pos = series([-1, -1, -1, -1])
        out = apply_stops(pos, series([0.04, 0.04, 0.04, 0.04]), stop_loss=0.05)
        assert out.tolist() == [-1, -1, 0, 0]

    def test_does_not_re_enter_on_the_same_signal_run(self):
        # The whole point of the lock: without it the next bar re-enters and the
        # stop only ever costs an extra round of transaction costs.
        pos = series([1] * 8)
        rets = series([-0.10, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05])
        out = apply_stops(pos, rets, stop_loss=0.05)
        assert out.tolist() == [1, 0, 0, 0, 0, 0, 0, 0]

    def test_a_new_signal_clears_the_lock(self):
        pos = series([1, 1, 1, -1, -1])
        rets = series([-0.10, 0.0, 0.0, 0.0, 0.0])
        out = apply_stops(pos, rets, stop_loss=0.05)
        assert out.tolist() == [1, 0, 0, -1, -1]

    def test_returning_to_flat_and_back_counts_as_a_new_trade(self):
        pos = series([1, 1, 0, 1, 1])
        rets = series([-0.10, 0.0, 0.0, 0.0, 0.0])
        out = apply_stops(pos, rets, stop_loss=0.05)
        assert out.tolist() == [1, 0, 0, 1, 1]

    def test_gains_before_a_loss_are_carried_into_the_stop_check(self):
        # +10% then -10% leaves the trade at -1%, which must not trip a 5% stop.
        pos = series([1, 1, 1])
        out = apply_stops(pos, series([0.10, -0.10, 0.0]), stop_loss=0.05)
        assert out.tolist() == [1, 1, 1]


class TestTakeProfit:
    def test_exits_after_the_target_is_reached(self):
        pos = series([1, 1, 1, 1])
        out = apply_stops(pos, series([0.06, 0.06, 0.06, 0.06]), take_profit=0.10)
        assert out.tolist() == [1, 1, 0, 0]

    def test_shorts_take_profit_on_a_decline(self):
        pos = series([-1, -1, -1])
        out = apply_stops(pos, series([-0.12, 0.0, 0.0]), take_profit=0.10)
        assert out.tolist() == [-1, 0, 0]

    def test_both_limits_can_be_active_at_once(self):
        pos = series([1, 1, 1, 0, 1, 1])
        rets = series([0.12, 0.0, 0.0, 0.0, -0.12, 0.0])
        out = apply_stops(pos, rets, stop_loss=0.05, take_profit=0.10)
        assert out.tolist() == [1, 0, 0, 0, 1, 0]


class TestStopValidation:
    @pytest.mark.parametrize("bad", [0, -0.05])
    def test_rejects_non_positive_stop_loss(self, bad):
        with pytest.raises(ValueError, match="positive fraction"):
            apply_stops(series([1, 1]), series([0.0, 0.0]), stop_loss=bad)

    @pytest.mark.parametrize("bad", [0, -0.1])
    def test_rejects_non_positive_take_profit(self, bad):
        with pytest.raises(ValueError, match="positive fraction"):
            apply_stops(series([1, 1]), series([0.0, 0.0]), take_profit=bad)

    def test_nan_returns_are_treated_as_flat(self):
        # The first bar's return is always NaN (pct_change has no prior close).
        rets = series([np.nan, 0.01, 0.01])
        out = apply_stops(series([1, 1, 1]), rets, stop_loss=0.05)
        assert out.tolist() == [1, 1, 1]


class TestVolatilityTargeting:
    def test_warmup_bars_size_to_zero(self):
        size = volatility_target_size(series([0.01, -0.01] * 10), window=20)
        assert size.iloc[:20].eq(0).all()

    def test_low_volatility_sizes_up_and_high_sizes_down(self):
        calm = volatility_target_size(series([0.001, -0.001] * 30), window=10, target_vol=0.15)
        wild = volatility_target_size(series([0.05, -0.05] * 30), window=10, target_vol=0.15)
        assert calm.iloc[-1] > wild.iloc[-1]

    def test_respects_the_leverage_cap(self):
        size = volatility_target_size(
            series([0.0001, -0.0001] * 30), window=10, max_leverage=2.0
        )
        assert size.max() <= 2.0

    def test_a_flat_price_run_sizes_to_zero_not_infinity(self):
        # Zero trailing volatility would otherwise divide by zero.
        size = volatility_target_size(series([0.0] * 30), window=10)
        assert np.isfinite(size).all() and size.eq(0).all()

    def test_sizing_never_uses_the_current_bar(self):
        # A volatility explosion on the final bar must not shrink that same
        # bar's size — that number is not knowable until the bar closes.
        rets = series([0.001] * 30 + [0.5])
        size = volatility_target_size(rets, window=10)
        assert size.iloc[-1] == pytest.approx(size.iloc[-2])

    @pytest.mark.parametrize(
        "kwargs,msg",
        [
            ({"target_vol": 0}, "target_vol"),
            ({"max_leverage": 0}, "max_leverage"),
            ({"window": 1}, "window"),
        ],
    )
    def test_rejects_nonsense_parameters(self, kwargs, msg):
        with pytest.raises(ValueError, match=msg):
            volatility_target_size(series([0.01] * 30), **kwargs)


class TestSizePositions:
    def test_fixed_sizing_is_the_identity(self):
        pos = series([1, -1, 0, 1])
        pd.testing.assert_series_equal(
            size_positions(pos, series([0.01] * 4), sizing="fixed"), pos
        )

    def test_vol_target_scales_the_position(self):
        pos = series([1.0] * 40)
        out = size_positions(pos, series([0.01, -0.01] * 20), sizing="vol_target", vol_window=10)
        assert out.iloc[-1] != 1.0 and out.iloc[-1] > 0

    def test_vol_target_keeps_direction(self):
        pos = series([-1.0] * 40)
        out = size_positions(pos, series([0.01, -0.01] * 20), sizing="vol_target", vol_window=10)
        assert out.iloc[-1] < 0

    def test_flat_stays_flat_whatever_the_sizing(self):
        pos = series([0.0] * 40)
        out = size_positions(pos, series([0.01, -0.01] * 20), sizing="vol_target", vol_window=10)
        assert out.eq(0).all()

    def test_rejects_an_unknown_rule(self):
        with pytest.raises(ValueError, match="Unknown sizing rule"):
            size_positions(series([1.0]), series([0.0]), sizing="kelly")
