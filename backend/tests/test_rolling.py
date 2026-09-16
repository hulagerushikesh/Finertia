"""Rolling (anchored) walk-forward.

The single-split walk-forward is one draw; this is the distribution. The tests
pin the fold geometry (tiling, gaps, anchoring), that positions are never
rebuilt on a slice, that a regime change shows up as one, and that the
aggregate blocks are consistent with the folds they summarise.
"""

import numpy as np
import pandas as pd
import pytest

from purge import MIN_HALF_BARS
from rolling import _fold_edges, rolling_walk_forward
from strategies import build_positions
from validation import _segment_metrics
from engine import compute_returns


def _series(values, start="2018-01-01"):
    idx = pd.bdate_range(start, periods=len(values))
    return pd.Series(np.asarray(values, dtype=float), index=idx, name="Close")


def _trend(n, drift=0.003, vol=0.004, seed=0):
    """A clean uptrend: momentum stays long and earns in every stretch."""
    rng = np.random.default_rng(seed)
    return _series(100 * np.cumprod(1 + drift + vol * rng.standard_normal(n)))


def _whipsaw(n, level=100.0, seed=1):
    """A 20-bar oscillation. A 10-bar momentum reads most positive at the peak
    and most negative at the trough, so the strategy buys tops and sells
    bottoms by construction; the 20-bar lookback never clears the threshold
    and stays flat. Momentum cannot earn here."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return level * (1 + 0.06 * np.sin(2 * np.pi * t / 20)) * (1 + 0.001 * rng.standard_normal(n))


def _regime_switch(n_trend=700, n_chop=700):
    """A clean uptrend, then the whipsaw at the level the trend reached.

    Momentum earns in the first half and loses in the second; the folds that
    land in each half should say so.
    """
    trend = _trend(n_trend).to_numpy()
    return _series(np.concatenate([trend, _whipsaw(n_chop, level=trend[-1])]))


GRID = [{"momentum_lookback": lb, "ma_window": w} for lb in (10, 20) for w in (20, 50)]


# --- geometry ---------------------------------------------------------------


def test_edges_tile_the_period_after_the_first_split():
    edges = _fold_edges(1000, 4, 0.4)
    assert edges[0] == 400
    assert edges[-1] == 1000
    assert len(edges) == 5
    assert all(b > a for a, b in zip(edges, edges[1:]))


def test_too_short_for_the_folds_is_a_clear_error():
    with pytest.raises(ValueError, match="fewer folds"):
        _fold_edges(150, 4, 0.4)


def test_fewer_than_two_folds_is_refused():
    with pytest.raises(ValueError, match="at least 2"):
        rolling_walk_forward(_trend(800), 0.001, grid=GRID, n_folds=1)


def test_folds_are_anchored_purged_and_non_overlapping():
    close = _trend(1000)
    res = rolling_walk_forward(close, 0.001, grid=GRID, n_folds=4)
    folds = res["folds"]
    assert len(folds) == 4
    is_bars = [f["in_sample_bars"] for f in folds]
    # Anchored: every fold's in-sample stretch starts at bar 0 and grows.
    assert is_bars == sorted(is_bars) and len(set(is_bars)) == 4
    for f in folds:
        assert f["gap_bars"] > 0
        assert f["out_of_sample_bars"] >= MIN_HALF_BARS
    # A fold's out-of-sample segment ends where the next split sits, and the
    # next fold purges its in-sample end back from that same split — so the
    # straddling bars are scored by fold k and never selected on by fold k+1.
    dates = pd.to_datetime
    for a, b in zip(folds, folds[1:]):
        assert dates(a["out_of_sample_end_date"]) > dates(b["in_sample_end_date"])
        assert dates(b["out_of_sample_start_date"]) > dates(a["out_of_sample_end_date"])


def test_stitched_length_is_the_sum_of_the_segments():
    res = rolling_walk_forward(_trend(1000), 0.001, grid=GRID, n_folds=4)
    assert res["out_of_sample_stitched"]["bars"] == sum(
        f["out_of_sample_bars"] for f in res["folds"]
    )


def test_verdict_counts_and_positives_agree_with_the_folds():
    res = rolling_walk_forward(_regime_switch(), 0.001, grid=GRID, n_folds=4)
    assert sum(res["verdict_counts"].values()) == res["n_folds"]
    assert res["folds_positive"] == sum(
        1 for f in res["folds"] if f["out_of_sample_sharpe"] > 0
    )
    lo, hi = res["out_of_sample_sharpe_range"]
    for f in res["folds"]:
        assert lo <= f["out_of_sample_sharpe"] <= hi


# --- the numbers are the right numbers ---------------------------------------


def test_fold_scores_are_full_series_positions_sliced():
    """A fold's out-of-sample metrics must equal the same parameters' metrics
    taken from positions built on the whole series and then sliced. Building
    on the slice would leave the warm-up flat and change the number."""
    close = _trend(1000)
    returns = compute_returns(close)
    res = rolling_walk_forward(close, 0.001, grid=GRID, n_folds=3)
    for f in res["folds"]:
        pos = build_positions(close, "momentum", f["best_params"])
        seg = slice(
            close.index.get_loc(pd.Timestamp(f["out_of_sample_start_date"])),
            close.index.get_loc(pd.Timestamp(f["out_of_sample_end_date"])) + 1,
        )
        expected = _segment_metrics(pos.iloc[seg], returns.iloc[seg], 0.001)
        assert f["out_of_sample_sharpe"] == pytest.approx(expected["sharpe_ratio"], abs=1e-9)


def test_benchmark_return_is_the_segment_close_ratio():
    close = _trend(1000)
    res = rolling_walk_forward(close, 0.001, grid=GRID, n_folds=4)
    for f in res["folds"]:
        first = close[f["out_of_sample_start_date"]]
        last = close[f["out_of_sample_end_date"]]
        assert f["benchmark_return"] == pytest.approx(last / first - 1, abs=1e-6)


def test_the_winner_is_chosen_on_the_in_sample_stretch_only():
    """Selecting on the segment being scored is the leak the whole design
    exists to close. The in-sample Sharpe reported for the winner must be
    the maximum over the grid on bars strictly before the gap."""
    close = _trend(1000)
    returns = compute_returns(close)
    res = rolling_walk_forward(close, 0.001, grid=GRID, n_folds=3)
    for f in res["folds"]:
        is_end = f["in_sample_bars"]
        sharpes = {}
        for combo in GRID:
            pos = build_positions(close, "momentum", combo)
            m = _segment_metrics(pos.iloc[:is_end], returns.iloc[:is_end], 0.001)
            sharpes[tuple(sorted(combo.items()))] = m["sharpe_ratio"]
        best_key = max(sharpes, key=sharpes.get)
        assert tuple(sorted(f["best_params"].items())) == best_key
        assert f["in_sample_sharpe"] == pytest.approx(sharpes[best_key], abs=1e-6)


# --- regimes -----------------------------------------------------------------


def test_a_regime_change_is_reported_as_one():
    res = rolling_walk_forward(_regime_switch(), 0.001, grid=GRID, n_folds=4)
    verdicts = [f["out_of_sample_sharpe"] > 0 for f in res["folds"]]
    # Momentum earns in the trend and is whipsawed in the chop: the first
    # fold is positive, the last is not, and the overall reading says so.
    assert verdicts[0] is True
    assert verdicts[-1] is False
    assert res["verdict"] == "regime_dependent"


def test_a_clean_trend_is_consistent():
    res = rolling_walk_forward(_trend(1200, seed=3), 0.001, grid=GRID, n_folds=3)
    assert res["verdict"] == "consistent"
    assert res["folds_positive"] == 3


def test_a_strategy_that_never_earns_is_failed():
    res = rolling_walk_forward(_series(_whipsaw(1200)), 0.002, grid=GRID, n_folds=3)
    assert res["verdict"] == "failed"
    assert res["folds_positive"] == 0


def test_market_context_travels_with_the_verdict():
    res = rolling_walk_forward(_regime_switch(), 0.001, grid=GRID, n_folds=4)
    # The trend half should show a positive market; the chop half, roughly flat.
    assert res["folds"][0]["benchmark_return"] > 0.1
    assert abs(res["folds"][-1]["benchmark_return"]) < 0.15
    for f in res["folds"]:
        assert f["realised_volatility"] > 0


# --- aggregates ----------------------------------------------------------------


def test_parameter_stability_counts_distinct_winners():
    res = rolling_walk_forward(_trend(1000), 0.001, grid=GRID, n_folds=4)
    stab = res["parameter_stability"]
    keys = {tuple(sorted(f["best_params"].items())) for f in res["folds"]}
    assert stab["distinct_parameter_sets"] == len(keys)
    assert 0 < stab["modal_share"] <= 1
    assert tuple(sorted(stab["modal_params"].items())) in keys


def test_one_cell_grid_is_perfectly_stable():
    res = rolling_walk_forward(_trend(1000), 0.001, grid=GRID[:1], n_folds=3)
    assert res["parameter_stability"] == {
        "distinct_parameter_sets": 1,
        "modal_params": GRID[0],
        "modal_share": 1.0,
    }


def test_stitched_interval_brackets_the_point():
    res = rolling_walk_forward(_trend(1000), 0.001, grid=GRID, n_folds=4)
    block = res["out_of_sample_stitched"]
    ci = block["sharpe_interval"]
    assert ci["low"] <= block["sharpe_ratio"] <= ci["high"]
    assert ci["point"] == pytest.approx(block["sharpe_ratio"], abs=1e-6)


def test_stitched_is_deterministic_for_a_seed():
    a = rolling_walk_forward(_trend(1000), 0.001, grid=GRID, n_folds=4, seed=11)
    b = rolling_walk_forward(_trend(1000), 0.001, grid=GRID, n_folds=4, seed=11)
    assert a["out_of_sample_stitched"]["sharpe_interval"] == b["out_of_sample_stitched"]["sharpe_interval"]


def test_a_cell_too_long_for_the_first_fold_can_still_win_a_later_one():
    close = _trend(1000)
    grid = GRID + [{"momentum_lookback": 20, "ma_window": 380}]
    res = rolling_walk_forward(close, 0.001, grid=grid, n_folds=4, min_train_ratio=0.3)
    tested = [f["combinations_tested"] for f in res["folds"]]
    # 300 bars in the first fold cannot fit a 380-bar window; later folds can.
    assert tested[0] == len(GRID)
    assert tested[-1] == len(grid)
