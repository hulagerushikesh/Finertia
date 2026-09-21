"""Walk-forward and the permutation test, asked of a basket.

The anchor throughout: a one-leg book with weight 1 must reproduce the
single-ticker functions exactly, so every verdict means the same thing on
either tab. The remaining tests pin the two places a basket differs — the grid
is scored on the book, and every leg is re-timed on its own.
"""

import numpy as np
import pandas as pd
import pytest

from engine import compute_returns
from portfolio import equal_weights
from portfolio_validation import (
    book_net_return,
    leg_positions,
    portfolio_permutation_test,
    portfolio_walk_forward,
)
from strategies import build_positions
from validation import permutation_test, walk_forward

PARAMS = {"momentum_lookback": 20, "ma_window": 50, "momentum_threshold": 0.02}
COST = 0.001


def price(n=900, drift=0.0006, vol=0.015, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, vol, n))), index=idx)


def basket(*seeds):
    frame = pd.DataFrame({f"T{s}": price(seed=s) for s in seeds})
    return frame, equal_weights(list(frame.columns), frame.index)


# ---------------------------------------------------------------------------
# One leg is the single-ticker test
# ---------------------------------------------------------------------------


class TestOneLegReproducesSingleTicker:
    def test_walk_forward_matches_key_for_key(self):
        close = price()
        single = walk_forward(close, COST, seed=7)
        book = portfolio_walk_forward(pd.DataFrame({"T": close}), equal_weights(["T"], close.index), COST, seed=7)
        for k in ("best_params", "verdict", "sharpe_degradation", "split_date", "combinations_tested", "boundary"):
            assert book[k] == single[k], k
        assert book["best_in_sample"]["sharpe_ratio"] == single["best_in_sample"]["sharpe_ratio"]
        assert book["best_out_of_sample"]["sharpe_ratio"] == single["best_out_of_sample"]["sharpe_ratio"]
        assert book["overfitting"]["pbo"] == single["overfitting"]["pbo"]
        assert book["deflated"]["effective_trials"] == single["deflated"]["effective_trials"]
        # The basket's buy-and-hold is the asset's own, so the whole-grid test agrees too.
        assert book["snooping"]["reality_check"] == single["snooping"]["reality_check"]
        assert book["snooping"]["spa"] == single["snooping"]["spa"]
        assert [c["params"] for c in book["grid"]] == [c["params"] for c in single["grid"]]

    def test_permutation_matches_draw_for_draw(self):
        close = price()
        pos = build_positions(close, "momentum", PARAMS)
        single = permutation_test(pos, compute_returns(close), COST, n_trials=200, seed=3)
        book = portfolio_permutation_test(
            pd.DataFrame({"T": pos}), pd.DataFrame({"T": close}).pct_change(),
            equal_weights(["T"], close.index), COST, n_trials=200, seed=3,
        )
        assert book["real_sharpe"] == single["real_sharpe"]
        assert book["p_value"] == single["p_value"]
        assert book["percentile"] == single["percentile"]
        assert book["random_sharpe_mean"] == single["random_sharpe_mean"]
        assert book["random_sharpe_p95"] == single["random_sharpe_p95"]

    def test_two_identical_legs_are_one_leg(self):
        """Equal weight on two copies of the same series is the same book, so the
        walk-forward numbers cannot move — a check that weighting and summing
        do not leak anything of their own."""
        close = price()
        aligned = pd.DataFrame({"A": close, "B": close})
        book = portfolio_walk_forward(aligned, equal_weights(["A", "B"], close.index), COST)
        single = walk_forward(close, COST)
        assert book["best_params"] == single["best_params"]
        assert book["best_out_of_sample"]["sharpe_ratio"] == pytest.approx(single["best_out_of_sample"]["sharpe_ratio"], abs=1e-9)
        assert book["legs"]["A"] == book["legs"]["B"]


# ---------------------------------------------------------------------------
# The grid is scored on the book
# ---------------------------------------------------------------------------


class TestGridOnTheBook:
    def test_grid_sharpes_are_book_sharpes_not_a_legs(self):
        aligned, w = basket(1, 2, 3)
        r = portfolio_walk_forward(aligned, w, COST)
        is_end = r["boundary"]["is_end"]
        for cell in r["grid"][:3]:
            pos = leg_positions(aligned, "momentum", {"momentum_threshold": 0.02, **cell["params"]})
            net, exposure = book_net_return(pos, aligned.pct_change(), w, COST)
            from portfolio_validation import _metrics
            assert cell["sharpe_ratio"] == _metrics(net.iloc[:is_end], exposure.iloc[:is_end])["sharpe_ratio"]
        assert r["best_in_sample"]["sharpe_ratio"] == max(c["sharpe_ratio"] for c in r["grid"])

    def test_legs_block_names_every_ticker_and_the_weights_it_held(self):
        aligned, w = basket(1, 2, 3)
        r = portfolio_walk_forward(aligned, w, COST)
        assert r["tickers"] == ["T1", "T2", "T3"]
        assert set(r["legs"]) == {"T1", "T2", "T3"}
        assert sum(v["mean_weight"] for v in r["legs"].values()) == pytest.approx(1.0, abs=1e-3)
        for v in r["legs"].values():
            assert {"in_sample_sharpe", "out_of_sample_sharpe", "mean_weight"} <= set(v)

    def test_a_zero_weight_leg_contributes_nothing(self):
        aligned, _ = basket(1, 2)
        w = pd.DataFrame({"T1": 1.0, "T2": 0.0}, index=aligned.index)
        r = portfolio_walk_forward(aligned, w, COST)
        single = walk_forward(aligned["T1"], COST)
        assert r["best_params"] == single["best_params"]
        assert r["best_out_of_sample"]["sharpe_ratio"] == single["best_out_of_sample"]["sharpe_ratio"]

    def test_benchmark_is_the_held_basket(self):
        aligned, w = basket(1, 2, 3)
        r = portfolio_walk_forward(aligned, w, COST)
        assert r["snooping"]["benchmark"] == "buy_and_hold_basket"
        assert r["snooping"]["computable"]

    def test_user_params_scored_on_the_book(self):
        aligned, w = basket(1, 2)
        r = portfolio_walk_forward(aligned, w, COST, base_params=PARAMS, user_params={"momentum_lookback": 20, "ma_window": 50})
        assert r["user_params"]["params"] == {"momentum_lookback": 20, "ma_window": 50}
        assert "sharpe_ratio" in r["user_params"]["out_of_sample"]

    def test_rejects_a_range_too_short_to_split(self):
        aligned, w = basket(1, 2)
        with pytest.raises(ValueError, match="too short"):
            portfolio_walk_forward(aligned.iloc[:50], w.iloc[:50], COST)


# ---------------------------------------------------------------------------
# Every leg re-timed on its own
# ---------------------------------------------------------------------------


class TestPermutationNull:
    def test_legs_are_shuffled_independently(self):
        """A leg and its mirror image at half weight each: the real book is
        flat by construction and earns only the cost drag. Re-timed
        independently, the legs stop cancelling and the null book is a live
        one that beats the drag almost every draw — p near 1, which is the
        honest answer for a book with no exposure. Had both legs drawn the
        SAME permutation they would cancel on every trial too, the null would
        be nothing but drag, and a flat book would read as timing skill."""
        close = price()
        pos = build_positions(close, "momentum", PARAMS)
        r = portfolio_permutation_test(
            pd.DataFrame({"A": pos, "B": -pos}), pd.DataFrame({"A": close, "B": close}).pct_change(),
            equal_weights(["A", "B"], close.index), COST, n_trials=200, seed=5,
        )
        assert r["real_sharpe"] < 0
        assert r["random_sharpe_mean"] > r["real_sharpe"]
        assert r["p_value"] > 0.9

    def test_two_copies_do_not_share_a_draw(self):
        """Two copies of one leg. With one shared permutation the book would be
        that leg and its null the single-leg null, draw for draw."""
        close = price()
        pos = build_positions(close, "momentum", PARAMS)
        single = permutation_test(pos, compute_returns(close), COST, n_trials=200, seed=5)
        two = portfolio_permutation_test(
            pd.DataFrame({"A": pos, "B": pos}), pd.DataFrame({"A": close, "B": close}).pct_change(),
            equal_weights(["A", "B"], close.index), COST, n_trials=200, seed=5,
        )
        assert two["real_sharpe"] == pytest.approx(single["real_sharpe"], abs=1e-9)
        assert two["random_sharpe_p95"] != single["random_sharpe_p95"]

    def test_a_leg_that_never_trades_has_nothing_to_shuffle(self):
        close = price()
        always_long = pd.Series(1.0, index=close.index)
        r = portfolio_permutation_test(
            pd.DataFrame({"T": always_long}), pd.DataFrame({"T": close}).pct_change(),
            equal_weights(["T"], close.index), COST, n_trials=100,
        )
        assert r["p_value"] == 1.0
        assert r["random_sharpe_std"] == 0.0

    def test_weights_are_held_fixed(self):
        """A leg with zero weight cannot move the book, however it is re-timed."""
        aligned, _ = basket(1, 2)
        pos = leg_positions(aligned, "momentum", PARAMS)
        w = pd.DataFrame({"T1": 1.0, "T2": 0.0}, index=aligned.index)
        book = portfolio_permutation_test(pos, aligned.pct_change(), w, COST, n_trials=200, seed=9)
        single = permutation_test(pos["T1"], compute_returns(aligned["T1"]), COST, n_trials=200, seed=9)
        assert book["real_sharpe"] == single["real_sharpe"]
        # Different draw order (two legs share one generator), so the p-values
        # are not bit-identical; the null distribution is the same one.
        assert book["random_sharpe_mean"] == pytest.approx(single["random_sharpe_mean"], abs=0.05)

    def test_per_leg_block_is_the_single_ticker_test_on_each_leg(self):
        aligned, w = basket(1, 2, 3)
        pos = leg_positions(aligned, "momentum", PARAMS)
        r = portfolio_permutation_test(pos, aligned.pct_change(), w, COST, n_trials=200)
        assert set(r["legs"]) == {"T1", "T2", "T3"}
        for v in r["legs"].values():
            assert 0 < v["p_value"] <= 1
            assert v["significant"] == (v["p_value"] < 0.05)
        assert r["legs_significant"] == sum(v["significant"] for v in r["legs"].values())
        assert r["null"].startswith("each leg's timing shuffled independently")

    def test_deterministic_under_a_seed(self):
        aligned, w = basket(1, 2)
        pos = leg_positions(aligned, "momentum", PARAMS)
        a = portfolio_permutation_test(pos, aligned.pct_change(), w, COST, n_trials=100, seed=1)
        b = portfolio_permutation_test(pos, aligned.pct_change(), w, COST, n_trials=100, seed=1)
        c = portfolio_permutation_test(pos, aligned.pct_change(), w, COST, n_trials=100, seed=2)
        assert a == b
        assert a["random_sharpe_mean"] != c["random_sharpe_mean"]

    def test_rejects_mismatched_legs(self):
        aligned, w = basket(1, 2)
        pos = leg_positions(aligned, "momentum", PARAMS)
        with pytest.raises(ValueError, match="same tickers"):
            portfolio_permutation_test(pos[["T1"]], aligned.pct_change(), w, COST, n_trials=100)
        with pytest.raises(ValueError, match="share an index"):
            portfolio_permutation_test(pos.iloc[1:], aligned.pct_change(), w, COST, n_trials=100)
