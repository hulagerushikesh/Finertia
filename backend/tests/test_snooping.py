"""Whole-grid inference (snooping.py) and its wiring into walk_forward.

A p-value is a number between 0 and 1, so almost any bootstrap returns one that
looks plausible. These pin the properties the three tests must have: the
snooping gap (the best of a null grid looks better alone than inside its grid),
Hansen's ordering of the three SPA p-values, stepdown finding exactly the
planted cell, and the family-wise error staying near alpha under the null.
"""

import numpy as np
import pandas as pd
import pytest

from snooping import MIN_OBS, _p, whole_grid_test
from validation import walk_forward

T = 1500
B = 400  # enough resolution for the assertions below, quick enough for CI


def _bench(seed, n=T):
    return np.random.default_rng(seed).normal(0.0004, 0.012, n)


def _null_grid(bench, n_cand, seed, beta_low=0.3):
    """Cells that hold a fraction of the benchmark plus their own noise — no
    cell has an edge over holding the benchmark outright."""
    rng = np.random.default_rng(seed)
    betas = rng.uniform(beta_low, 1.0, n_cand)
    return bench[:, None] * betas[None, :] + rng.normal(0, 0.004, (len(bench), n_cand))


# ── input contract ──────────────────────────────────────────────────────────

def test_shapes_are_checked():
    bench = _bench(0, 200)
    with pytest.raises(ValueError, match="one return per candidate bar"):
        whole_grid_test(np.zeros((200, 3)), bench[:-1])
    with pytest.raises(ValueError, match="one label per candidate"):
        whole_grid_test(np.zeros((200, 3)), bench, labels=[{}, {}])
    with pytest.raises(ValueError, match="alpha"):
        whole_grid_test(np.zeros((200, 3)), bench, alpha=1.0)
    with pytest.raises(ValueError, match="n_bootstrap"):
        whole_grid_test(np.zeros((200, 3)), bench, n_bootstrap=10)


def test_too_short_and_empty_are_not_computable():
    short = whole_grid_test(np.zeros((MIN_OBS - 1, 2)), np.zeros(MIN_OBS - 1))
    assert short["computable"] is False and "bars" in short["reason"]
    empty = whole_grid_test(np.zeros((200, 0)), np.zeros(200))
    assert empty["computable"] is False


def test_one_dimensional_candidate_is_a_grid_of_one():
    bench = _bench(1)
    out = whole_grid_test(bench * 0.5, bench, n_bootstrap=B, seed=1)
    assert out["computable"] and out["n_candidates"] == 1
    # With one cell the Reality Check IS the naive test — the same maximum.
    assert out["reality_check"]["p_value"] == out["best"]["p_value_naive"]


def test_p_value_never_reaches_zero():
    assert _p(np.zeros(999, dtype=bool)) == pytest.approx(1 / 1000)
    assert _p(np.ones(999, dtype=bool)) == 1.0


def test_deterministic_under_a_seed():
    bench = _bench(2)
    grid = _null_grid(bench, 8, seed=3)
    a = whole_grid_test(grid, bench, n_bootstrap=B, seed=9)
    b = whole_grid_test(grid, bench, n_bootstrap=B, seed=9)
    assert a == b


# ── the properties that make it a data-snooping test ───────────────────────

def test_snooping_gap_the_best_of_a_null_grid_looks_better_alone():
    """The whole point. On a grid with no edge, the best cell tested on its
    own is over-optimistic; with the grid inside the bootstrap it is not."""
    bench = _bench(4)
    out = whole_grid_test(_null_grid(bench, 16, seed=5), bench, n_bootstrap=B, seed=6)
    assert out["best"]["p_value_naive"] < out["reality_check"]["p_value"]
    assert out["best"]["p_value_naive"] < out["spa"]["p_value"]
    assert out["stepdown"]["n_beating_benchmark"] == 0
    assert out["verdict"] == "no_evidence"


def test_hansen_ordering_lower_le_consistent_le_upper():
    bench = _bench(7)
    for seed in range(3):
        out = whole_grid_test(_null_grid(bench, 12, seed=seed), bench, n_bootstrap=B, seed=seed)
        spa = out["spa"]
        assert spa["p_value_lower"] <= spa["p_value"] <= spa["p_value_upper"]


def test_padding_the_grid_with_bad_cells_hurts_rc_more_than_spa():
    """Hansen's complaint about the Reality Check: junk candidates recentred
    to zero inflate the null maximum. SPA leaves them at their own (negative)
    mean, so its p-value moves less when junk is added."""
    bench = _bench(8)
    rng = np.random.default_rng(8)
    good = bench + 0.0006 + rng.normal(0, 0.004, T)          # a real, modest edge
    junk = bench[:, None] - 0.002 + rng.normal(0, 0.02, (T, 15))  # loses, and noisy
    alone = whole_grid_test(good, bench, n_bootstrap=B, seed=1)
    padded = whole_grid_test(np.column_stack([good, junk]), bench, n_bootstrap=B, seed=1)
    rc_inflation = padded["reality_check"]["p_value"] - alone["reality_check"]["p_value"]
    spa_inflation = padded["spa"]["p_value"] - alone["spa"]["p_value"]
    assert padded["spa"]["poor_candidates_recentred"] > 0
    assert spa_inflation < rc_inflation


def test_stepdown_finds_exactly_the_planted_cell():
    bench = _bench(10)
    grid = _null_grid(bench, 16, seed=11)
    grid[:, 5] += 0.0015
    labels = [{"cell": k} for k in range(16)]
    out = whole_grid_test(grid, bench, labels=labels, n_bootstrap=B, seed=12)
    assert out["stepdown"]["beating_benchmark"] == [{"cell": 5}]
    assert out["best"]["params"] == {"cell": 5}
    assert out["verdict"] == "grid_beats_benchmark"
    surviving = [c["params"]["cell"] for c in out["cells"] if c["beats_benchmark"]]
    assert surviving == [5]
    # Cells come back best first.
    ts = [c["t_ratio"] for c in out["cells"]]
    assert ts == sorted(ts, reverse=True)


def test_stepdown_finds_two_planted_cells_and_adjusted_p_is_monotone():
    bench = _bench(13)
    grid = _null_grid(bench, 10, seed=14)
    grid[:, 2] += 0.0015
    grid[:, 7] += 0.0012
    out = whole_grid_test(grid, bench, n_bootstrap=B, seed=15)
    found = sorted(c["params"]["index"] for c in out["cells"] if c["beats_benchmark"])
    assert found == [2, 7]
    ps = [c["p_adjusted"] for c in out["cells"]]
    assert ps == sorted(ps)  # cells are best-first, so adjusted p is non-decreasing


def test_family_wise_error_is_near_alpha_under_the_null():
    """Across many null grids, the share where *any* cell is declared a
    winner at 5% should sit near 5%, not near 1 - 0.95^N."""
    false_positives = 0
    trials = 40
    for i in range(trials):
        bench = _bench(100 + i, n=800)
        out = whole_grid_test(_null_grid(bench, 12, seed=200 + i, beta_low=0.9), bench,
                              n_bootstrap=200, seed=300 + i)
        false_positives += out["stepdown"]["n_beating_benchmark"] > 0
    # 40 trials at p = 0.05: expect 2, binomial 95% upper bound is 5.
    assert false_positives <= 5


def test_flat_candidate_is_reported_but_not_studentised():
    bench = _bench(16)
    grid = _null_grid(bench, 4, seed=17)
    grid = np.column_stack([grid, bench])  # a cell that IS the benchmark: zero excess
    out = whole_grid_test(grid, bench, n_bootstrap=B, seed=18)
    assert out["n_candidates"] == 5 and out["n_studentised"] == 4
    flat = [c for c in out["cells"] if c["t_ratio"] is None]
    assert len(flat) == 1 and flat[0]["beats_benchmark"] is False


def test_reading_names_the_counts():
    bench = _bench(19)
    out = whole_grid_test(_null_grid(bench, 6, seed=20), bench, n_bootstrap=B, seed=21)
    assert out["reading"].startswith("The best of 6 cells")
    assert "No cell beats buy-and-hold" in out["reading"]


# ── wiring ──────────────────────────────────────────────────────────────────

def _prices(n=700, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, n))), index=idx)


def test_walk_forward_carries_the_block_and_labels_it_with_grid_params():
    wf = walk_forward(_prices(), 0.001)
    block = wf["snooping"]
    assert block["computable"] is True
    assert block["n_candidates"] == wf["combinations_tested"]
    assert block["benchmark"] == "buy_and_hold"
    grid_params = [r["params"] for r in wf["grid"]]
    assert all(c["params"] in grid_params for c in block["cells"])
    assert block["best"]["params"] in grid_params


def test_walk_forward_snooping_is_seeded_and_the_seed_matters():
    close = _prices()
    a = walk_forward(close, 0.001)["snooping"]
    b = walk_forward(close, 0.001)["snooping"]
    c = walk_forward(close, 0.001, seed=99)["snooping"]
    assert a == b
    assert a["reality_check"] != c["reality_check"] or a["spa"] != c["spa"]


# ── the two details a lazier implementation gets wrong ─────────────────────

def test_consistent_spa_is_strictly_below_upper_when_junk_is_present():
    """Hansen's consistent p leaves plainly poor cells at their negative
    mean. Recentring them to zero (the upper bound, and White's treatment)
    must give a larger p when the grid carries junk — otherwise the
    'consistent' variant is not doing anything."""
    rng = np.random.default_rng(0)
    bench = rng.normal(0.0004, 0.012, T)
    good = bench + 0.00045 + rng.normal(0, 0.004, T)
    junk = bench[:, None] - 0.003 + rng.normal(0, 0.02, (T, 15))
    spa = whole_grid_test(np.column_stack([good, junk]), bench, n_bootstrap=B, seed=1)["spa"]
    assert spa["poor_candidates_recentred"] == 15
    assert spa["p_value"] < spa["p_value_upper"]


def test_stepdown_tests_the_second_cell_against_the_rest_not_the_whole_grid():
    """With two cells, the second-ranked one is tested against the maximum
    over {itself} — so its adjusted p is exactly max(first's adjusted p, its
    own naive p). A single-step procedure tests it against both and comes
    out larger."""
    for s in range(4):
        rng = np.random.default_rng(30 + s)
        bench = rng.normal(0.0004, 0.012, T)
        a = bench + 0.0025 + rng.normal(0, 0.05, T)    # bigger mean, far bigger variance
        b = bench + 0.00028 + rng.normal(0, 0.004, T)  # smaller mean, tight -> ranks first on t
        cells = whole_grid_test(np.column_stack([a, b]), bench, n_bootstrap=B, seed=3)["cells"]
        first, second = cells
        assert second["p_adjusted"] == pytest.approx(max(first["p_adjusted"], second["p_naive"]))
        assert second["p_naive"] < first["p_naive"] or first["t_ratio"] > second["t_ratio"]
