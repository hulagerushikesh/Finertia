"""Walk-forward validation and the signal permutation test."""

import numpy as np
import pandas as pd
import pytest

from engine import compute_returns
from strategies import build_positions, STRATEGY_NAMES
from validation import walk_forward, permutation_test, _verdict


def price_series(n=600, drift=0.0006, vol=0.015, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)


class TestWalkForwardSplit:
    def test_split_sizes_follow_the_ratio_minus_the_gap(self):
        """The ratio sets where the cut falls; the purge-and-embargo gap then
        takes bars off each side. The reported counts are what each half
        actually used, not the nominal 420/180 — quoting the nominal figure
        would claim more evidence than either number rests on."""
        r = walk_forward(price_series(600), 0.001, split_ratio=0.7)
        gap = r["boundary"]["purge_bars"]
        assert gap == 6  # 1% of 600
        assert r["in_sample_bars"] == 420 - gap
        assert r["out_of_sample_bars"] == 180 - gap
        assert r["split_date"] == str(price_series(600).index[420].date())

    def test_the_two_halves_never_touch(self):
        r = walk_forward(price_series(600), 0.001, split_ratio=0.7)
        b = r["boundary"]
        assert b["oos_start"] - b["is_end"] == 2 * b["purge_bars"] > 0
        assert b["in_sample_end_date"] < b["out_of_sample_start_date"]
        assert b["applied"] is True and b["shortened"] is False

    def test_a_short_period_gives_up_the_gap_rather_than_the_split(self):
        """With 100 bars there is no room for a gap once both halves keep their
        30-bar floor. Dropping the gap is the right trade — but it has to be
        visible, because those numbers still carry boundary contamination."""
        r = walk_forward(price_series(100), 0.001, split_ratio=0.7)
        assert r["boundary"]["applied"] is False
        assert r["boundary"]["shortened"] is True

    def test_split_date_sits_between_the_endpoints(self):
        close = price_series(600)
        r = walk_forward(close, 0.001, split_ratio=0.7)
        split = pd.Timestamp(r["split_date"])
        assert close.index[0] < split < close.index[-1]

    def test_rejects_a_range_too_short_to_split(self):
        with pytest.raises(ValueError, match="too short"):
            walk_forward(price_series(40), 0.001, split_ratio=0.7)

    def test_skips_combinations_needing_more_warmup_than_the_in_sample_half(self):
        close = price_series(300)  # in-sample = 210 bars
        r = walk_forward(
            close, 0.001, split_ratio=0.7,
            grid=[{"ma_window": 20}, {"ma_window": 50}, {"ma_window": 400}],
        )
        assert all(g["params"]["ma_window"] != 400 for g in r["grid"])

    def test_raises_when_no_combination_fits(self):
        with pytest.raises(ValueError, match="No parameter combination"):
            walk_forward(price_series(200), 0.001, grid=[{"ma_window": 5000}])


class TestWalkForwardResults:
    def test_best_params_are_the_top_of_the_grid(self):
        r = walk_forward(price_series(600), 0.001)
        assert r["best_params"] == r["grid"][0]["params"]

    def test_grid_is_sorted_by_sharpe_descending(self):
        r = walk_forward(price_series(600), 0.001)
        sharpes = [g["sharpe_ratio"] for g in r["grid"]]
        assert sharpes == sorted(sharpes, reverse=True)

    def test_degradation_is_in_sample_minus_out_of_sample(self):
        r = walk_forward(price_series(600), 0.001)
        expected = r["best_in_sample"]["sharpe_ratio"] - r["best_out_of_sample"]["sharpe_ratio"]
        assert r["sharpe_degradation"] == pytest.approx(expected, abs=1e-6)

    def test_user_params_block_omitted_when_not_supplied(self):
        assert walk_forward(price_series(600), 0.001)["user_params"] is None

    def test_user_params_scored_on_both_halves_when_supplied(self):
        r = walk_forward(
            price_series(600), 0.001,
            user_params={"momentum_lookback": 20, "ma_window": 50},
        )
        u = r["user_params"]
        assert u["params"] == {"momentum_lookback": 20, "ma_window": 50}
        assert "sharpe_ratio" in u["in_sample"]
        assert "sharpe_ratio" in u["out_of_sample"]

    def test_deterministic_for_the_same_input(self):
        close = price_series(600)
        assert walk_forward(close, 0.001) == walk_forward(close, 0.001)

    def test_base_params_are_merged_under_grid_params(self):
        close = price_series(600)
        loose = walk_forward(close, 0.001, base_params={"momentum_threshold": 0.0})
        strict = walk_forward(close, 0.001, base_params={"momentum_threshold": 0.5})
        # A threshold of 0.5 suppresses nearly every signal, so results must differ.
        assert loose["best_in_sample"] != strict["best_in_sample"]


class TestWalkForwardAcrossStrategies:
    def test_runs_for_every_registered_strategy(self):
        close = price_series(700)
        for name in STRATEGY_NAMES:
            r = walk_forward(close, 0.001, strategy=name)
            assert r["strategy"] == name
            assert r["combinations_tested"] > 0
            assert r["verdict"] in {"held_up", "weakened", "overfit", "failed", "inconclusive"}

    def test_reports_the_strategy_it_was_given(self):
        assert walk_forward(price_series(700), 0.001, strategy="macd")["strategy"] == "macd"

    def test_best_params_match_the_strategys_own_grid_keys(self):
        r = walk_forward(price_series(700), 0.001, strategy="bollinger")
        assert set(r["best_params"]) == {"bb_window", "bb_std"}

    def test_unknown_strategy_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            walk_forward(price_series(600), 0.001, strategy="nope")


class TestVerdict:
    def test_negative_out_of_sample_sharpe_fails(self):
        assert _verdict(1.0, -0.2) == "failed"

    def test_keeping_most_of_the_edge_holds_up(self):
        assert _verdict(1.0, 0.8) == "held_up"

    def test_losing_most_of_the_edge_is_overfit(self):
        assert _verdict(1.0, 0.2) == "overfit"

    def test_middle_ground_is_weakened(self):
        assert _verdict(1.0, 0.5) == "weakened"

    def test_non_positive_in_sample_is_inconclusive(self):
        assert _verdict(-0.3, 0.1) == "inconclusive"


class TestPermutationTest:
    def _setup(self, seed=0):
        close = price_series(500, seed=seed)
        return build_positions(close, "momentum", {}), compute_returns(close)

    def test_deterministic_for_a_fixed_seed(self):
        pos, ret = self._setup()
        assert permutation_test(pos, ret, 0.001, 200, seed=42) == permutation_test(
            pos, ret, 0.001, 200, seed=42
        )

    def test_seed_changes_the_random_draw(self):
        pos, ret = self._setup()
        a = permutation_test(pos, ret, 0.001, 200, seed=1)
        b = permutation_test(pos, ret, 0.001, 200, seed=2)
        assert a["random_sharpe_mean"] != b["random_sharpe_mean"]

    def test_percentile_and_p_value_stay_in_range(self):
        pos, ret = self._setup()
        r = permutation_test(pos, ret, 0.001, 200, seed=0)
        assert 0.0 <= r["percentile"] <= 1.0
        assert 0.0 < r["p_value"] <= 1.0

    def test_significant_flag_agrees_with_p_value(self):
        pos, ret = self._setup()
        r = permutation_test(pos, ret, 0.001, 200, seed=0)
        assert r["significant"] == (r["p_value"] < 0.05)

    def test_verdict_agrees_with_significance(self):
        pos, ret = self._setup()
        r = permutation_test(pos, ret, 0.001, 200, seed=0)
        expected = "signal_timing_matters" if r["significant"] else "indistinguishable_from_random_timing"
        assert r["verdict"] == expected

    def test_rejects_mismatched_lengths(self):
        pos, ret = self._setup()
        with pytest.raises(ValueError, match="same length"):
            permutation_test(pos.iloc[:-5], ret, 0.001, 10)

    def test_shuffling_preserves_exposure_so_a_flat_strategy_stays_flat(self):
        close = price_series(300)
        flat = pd.Series(0.0, index=close.index)
        r = permutation_test(flat, compute_returns(close), 0.001, 50, seed=0)
        assert r["real_sharpe"] == 0.0
        assert r["random_sharpe_mean"] == 0.0
