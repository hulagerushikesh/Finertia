"""User-defined rules (rules.py): correctness, no lookahead, and refusals."""

import numpy as np
import pandas as pd
import pytest

from engine import apply_positions, compute_returns
from rules import RuleError, build_rule_positions, rule_warmup, validate


def _close(n=600, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, n))), index=idx)


def cond(left, op, right):
    return {"left": left, "op": op, "right": right}


SMA_CROSS = {
    "direction": "long",
    "entry": {"all": [cond({"ind": "sma", "n": 20}, "crosses_above", {"ind": "sma", "n": 50})]},
    "exit": {"all": [cond({"ind": "sma", "n": 20}, "crosses_below", {"ind": "sma", "n": 50})]},
}
RSI_DIP = {
    "direction": "long",
    "entry": {"all": [cond({"ind": "rsi", "n": 14}, "<", {"value": 30}),
                      cond({"ind": "close"}, ">", {"ind": "sma", "n": 200})]},
    "exit": {"any": [cond({"ind": "rsi", "n": 14}, ">", {"value": 70})]},
}


class TestPositions:
    def test_sma_cross_matches_a_hand_computation(self):
        close = _close()
        fast, slow = close.rolling(20).mean(), close.rolling(50).mean()
        expected, held = [], 0.0
        for t in range(len(close)):
            if t > 0 and not np.isnan(slow.iloc[t - 1]):
                up = fast.iloc[t] > slow.iloc[t] and fast.iloc[t - 1] <= slow.iloc[t - 1]
                down = fast.iloc[t] < slow.iloc[t] and fast.iloc[t - 1] >= slow.iloc[t - 1]
                if down:
                    held = 0.0
                elif up:
                    held = 1.0
            expected.append(held)
        expected = pd.Series(expected, index=close.index).shift(1).fillna(0.0)
        pd.testing.assert_series_equal(build_rule_positions(close, SMA_CROSS), expected, check_names=False)

    @pytest.mark.parametrize("rule", [SMA_CROSS, RSI_DIP], ids=["sma-cross", "rsi-dip"])
    def test_no_bar_can_see_the_future(self, rule):
        """Positions up to bar k are the same whether or not later bars exist."""
        close = _close()
        full = build_rule_positions(close, rule)
        for k in (60, 210, 333, 599):
            part = build_rule_positions(close.iloc[:k], rule)
            pd.testing.assert_series_equal(part, full.iloc[:k])

    def test_a_signal_is_acted_on_the_next_bar(self):
        close = pd.Series([10.0, 10, 10, 12, 12, 12], index=pd.bdate_range("2020-01-01", periods=6))
        rule = {"entry": {"all": [cond({"ind": "close"}, ">", {"value": 11})]},
                "exit": {"all": [cond({"ind": "close"}, "<", {"value": 5})]}}
        assert build_rule_positions(close, rule).tolist() == [0, 0, 0, 0, 1, 1]

    def test_held_until_the_exit_and_the_exit_wins_a_tie(self):
        close = pd.Series([1.0, 5, 3, 3, 9, 1], index=pd.bdate_range("2020-01-01", periods=6))
        rule = {"entry": {"any": [cond({"ind": "close"}, ">", {"value": 4})]},
                "exit": {"any": [cond({"ind": "close"}, ">", {"value": 8})]}}
        # Raw state: bar1 enter, bars 2-3 hold, bar4 both fire (exit wins), bar5 flat.
        assert build_rule_positions(close, rule).tolist() == [0, 0, 1, 1, 1, 0]

    def test_short_rules_go_short(self):
        close = _close()
        rule = {**SMA_CROSS, "direction": "short"}
        assert set(build_rule_positions(close, rule).unique()) <= {0.0, -1.0}
        assert (build_rule_positions(close, rule) == -build_rule_positions(close, SMA_CROSS)).all()

    def test_rsi_is_wilder_smoothing_from_the_first_bar(self):
        from rules import _rsi
        close = _close(200)
        n = 14
        d = close.diff().to_numpy()
        gains, losses = np.clip(d, 0, None), np.clip(-d, 0, None)
        avg_g = avg_l = None
        out = [np.nan] * len(close)
        for t in range(1, len(close)):
            g, l_ = gains[t], losses[t]
            avg_g = g if avg_g is None else avg_g + (g - avg_g) / n
            avg_l = l_ if avg_l is None else avg_l + (l_ - avg_l) / n
            if t >= n:
                out[t] = 100 - 100 / (1 + avg_g / avg_l)
        np.testing.assert_allclose(_rsi(close, n).to_numpy()[n + 1:], np.array(out)[n + 1:], rtol=1e-9)

    def test_the_engine_runs_a_rule(self):
        close = _close()
        out = apply_positions(build_rule_positions(close, RSI_DIP), compute_returns(close), 0.001)
        assert np.isfinite(out["equity_curve"].iloc[-1])


class TestWarmup:
    def test_the_longest_indicator_sets_it(self):
        assert rule_warmup(RSI_DIP) == 202
        assert rule_warmup(SMA_CROSS) == 52

    def test_macd_signal_counts_both_windows(self):
        rule = {"entry": {"all": [cond({"ind": "macd"}, "crosses_above", {"ind": "macd_signal"})]},
                "exit": {"all": [cond({"ind": "macd"}, "crosses_below", {"ind": "macd_signal"})]}}
        assert rule_warmup(rule) == 26 + 9 + 2

    def test_no_signal_before_the_warmup(self):
        close = _close()
        pos = build_rule_positions(close, RSI_DIP)
        assert (pos.iloc[: rule_warmup(RSI_DIP) - 1] == 0).all()


class TestRefusals:
    @pytest.mark.parametrize("rule, message", [
        ("x", "object"),
        ({"entry": SMA_CROSS["entry"]}, "both an entry and an exit"),
        ({**SMA_CROSS, "size": 2}, "Unknown field"),
        ({**SMA_CROSS, "direction": "sideways"}, "long or short"),
        ({**SMA_CROSS, "entry": {"all": []}}, "at least one"),
        ({**SMA_CROSS, "entry": {"both": SMA_CROSS["entry"]["all"]}}, "all"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "vwap"}, ">", {"value": 1})]}}, "unknown indicator"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "sma", "n": 1}, ">", {"value": 1})]}}, "from 2 to 400"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "sma", "n": 500}, ">", {"value": 1})]}}, "from 2 to 400"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "sma", "n": 20.5}, ">", {"value": 1})]}}, "whole number"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "sma", "n": True}, ">", {"value": 1})]}}, "whole number"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "sma", "window": 5}, ">", {"value": 1})]}}, "does not take"),
        ({**SMA_CROSS, "entry": {"all": [cond({"value": 1}, ">", {"value": 2})]}}, "two fixed values"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "close"}, "=", {"value": 1})]}}, "op must be"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "close"}, ">", {"value": float("nan")})]}}, "finite"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "macd", "fast": 30, "slow": 20}, ">", {"value": 0})]}}, "fast must be shorter"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "bb_upper", "k": 9}, ">", {"value": 0})]}}, "k must be"),
        ({**SMA_CROSS, "entry": {"all": [cond({"ind": "close"}, ">", {"value": 1})] * 9}}, "at most 8"),
    ])
    def test_a_bad_rule_is_refused_with_a_reason(self, rule, message):
        with pytest.raises(RuleError, match=message):
            validate(rule)

    def test_defaults_are_filled_in(self):
        rule = validate({"entry": {"all": [cond({"ind": "rsi"}, "<", {"value": 30})]},
                         "exit": {"all": [cond({"ind": "rsi"}, ">", {"value": 70})]}})
        assert rule["direction"] == "long"
        assert rule["entry"]["all"][0]["left"] == {"ind": "rsi", "n": 14}
