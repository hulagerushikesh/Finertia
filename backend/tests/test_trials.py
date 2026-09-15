"""Effective number of trials (trials.py) and its wiring into walk_forward."""

import numpy as np
import pandas as pd
import pytest

from deflated import deflated_sharpe_ratio
from trials import effective_trials_clusters, effective_trials_eigen
from validation import walk_forward

T = 600


@pytest.fixture
def rng():
    return np.random.default_rng(7)


def _noisy_copies(base, k, rng, noise=0.001):
    return np.column_stack([base + rng.normal(0, noise, len(base)) for _ in range(k)])


# ── the two limits every estimator has to get right ────────────────────────

def test_identical_candidates_are_one_trial(rng):
    base = rng.normal(0, 0.01, T)
    m = np.column_stack([base] * 6)
    assert effective_trials_eigen(m)["n_effective"] == 1.0
    c = effective_trials_clusters(m)
    assert c["n_effective"] == 1 and c["clusters"] == [[0, 1, 2, 3, 4, 5]]


def test_independent_candidates_are_n_trials(rng):
    m = rng.normal(0, 0.01, (T, 12))
    assert effective_trials_eigen(m)["n_effective"] == pytest.approx(12.0, abs=0.5)
    c = effective_trials_clusters(m)
    assert c["n_effective"] == 12
    assert len(c["clusters"]) == 12


def test_two_blocks_of_near_copies(rng):
    """The case the module exists for: a 16-cell grid that is really two trials."""
    a, b = rng.normal(0, 0.01, T), rng.normal(0, 0.01, T)
    m = np.hstack([_noisy_copies(a, 8, rng), _noisy_copies(b, 8, rng)])
    c = effective_trials_clusters(m)
    assert c["n_effective"] == 2
    assert sorted(map(sorted, c["clusters"])) == [list(range(8)), list(range(8, 16))]
    assert c["silhouette"] > 0.8
    # Li & Ji errs high on tight blocks — the small eigenvalues each add a
    # fraction — but it must land well under the raw count.
    e = effective_trials_eigen(m)["n_effective"]
    assert 2.0 <= e <= 4.0


def test_estimates_are_bounded_by_the_raw_count(rng):
    m = rng.normal(0, 0.01, (T, 9)) + rng.normal(0, 0.01, (T, 1))  # one shared factor
    e = effective_trials_eigen(m)["n_effective"]
    c = effective_trials_clusters(m)["n_effective"]
    assert 1.0 <= e <= 9.0
    assert 1 <= c <= 9


# ── hygiene ────────────────────────────────────────────────────────────────

def test_flat_candidates_are_dropped_and_indices_stay_original(rng):
    a = rng.normal(0, 0.01, T)
    m = np.column_stack([a, np.zeros(T), a * 1.0001, np.zeros(T)])
    c = effective_trials_clusters(m)
    assert c["n_candidates"] == 2
    assert c["clusters"] == [[0, 2]]
    assert effective_trials_eigen(m)["n_candidates"] == 2


def test_all_flat_is_not_computable():
    m = np.zeros((T, 4))
    assert effective_trials_eigen(m)["computable"] is False
    assert effective_trials_clusters(m)["computable"] is False


def test_single_candidate():
    m = np.random.default_rng(0).normal(0, 0.01, (T, 1))
    assert effective_trials_eigen(m)["n_effective"] == 1.0
    assert effective_trials_clusters(m)["n_effective"] == 1


def test_near_copies_are_one_blob_not_n_singletons(rng):
    """Three candidates at rho ~0.99 have no silhouette structure either way;
    the absolute distance says they are one trial."""
    a = rng.normal(0.0005, 0.01, T)
    m = _noisy_copies(a, 3, rng)
    c = effective_trials_clusters(m)
    assert c["n_effective"] == 1 and c["clusters"] == [[0, 1, 2]]
    avg = m.mean(axis=1)
    expected = avg.mean() / avg.std(ddof=1)
    assert c["cluster_sharpes"][0] == pytest.approx(expected, rel=1e-9)


# ── the deflation under an effective N ─────────────────────────────────────

def test_lower_n_lowers_the_bar_and_raises_the_dsr(rng):
    trials = list(rng.normal(0.5, 0.3, 16))
    sel = rng.normal(0.0004, 0.01, 800)
    raw = deflated_sharpe_ratio(trials, sel)
    eff = deflated_sharpe_ratio(trials, sel, n_trials_effective=4)
    assert eff["n_trials"] == 4
    assert eff["expected_max_sharpe"] < raw["expected_max_sharpe"]
    assert eff["deflated_sharpe_ratio"] >= raw["deflated_sharpe_ratio"]


def test_effective_n_outside_range_is_refused(rng):
    trials = list(rng.normal(0.5, 0.3, 8))
    sel = rng.normal(0.0004, 0.01, 800)
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(trials, sel, n_trials_effective=9)
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(trials, sel, n_trials_effective=0)


def test_cluster_spread_replaces_trial_spread(rng):
    trials = list(rng.normal(0.5, 0.3, 16))
    sel = rng.normal(0.0004, 0.01, 800)
    wide = deflated_sharpe_ratio(trials, sel, n_trials_effective=3,
                                 trial_sharpes_effective=[0.1, 0.9, 1.7])
    tight = deflated_sharpe_ratio(trials, sel, n_trials_effective=3,
                                  trial_sharpes_effective=[0.5, 0.55, 0.6])
    assert wide["sharpe_std_across_trials"] > tight["sharpe_std_across_trials"]
    assert wide["expected_max_sharpe"] > tight["expected_max_sharpe"]


# ── wiring ─────────────────────────────────────────────────────────────────

def _close(rng, n=1000):
    idx = pd.bdate_range("2019-01-01", periods=n)
    return pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.012, n)), index=idx)


def test_walk_forward_reports_effective_trials(rng):
    wf = walk_forward(_close(rng), transaction_cost=0.001, strategy="momentum")
    e = wf["deflated"]["effective_trials"]
    assert e["computable"] is True
    assert e["n_trials_raw"] == wf["combinations_tested"]
    assert 1 <= e["n_trials_lower_bound"] <= e["n_trials_effective"] <= e["n_trials_raw"]
    for k in ("under_raw", "under_eigen", "under_clusters", "under_effective"):
        assert set(e[k]) >= {"n_trials", "expected_max_sharpe", "deflated_sharpe_ratio", "verdict"}
    assert e["under_raw"]["n_trials"] == e["n_trials_raw"]
    assert e["under_effective"]["n_trials"] == e["n_trials_effective"]


def test_headline_is_the_larger_estimate(rng):
    """Lowering N flatters a result, so when the estimates disagree the
    tool keeps the higher bar."""
    wf = walk_forward(_close(rng), transaction_cost=0.001, strategy="bollinger")
    e = wf["deflated"]["effective_trials"]
    assert e["n_trials_effective"] == max(
        round(e["eigen"]["n_effective"]), e["clusters"]["n_effective"]
    )


def test_gap_is_never_negative(rng):
    """A smaller N can only lower the bar, so the deflated Sharpe under the
    effective count is never below the raw one."""
    for strat in ("momentum", "macd", "bollinger"):
        e = walk_forward(_close(rng), transaction_cost=0.001, strategy=strat)["deflated"]["effective_trials"]
        if e.get("dsr_gap") is not None:
            assert e["dsr_gap"] >= -1e-9


def test_raw_deflation_is_unchanged_by_the_new_block(rng):
    """Adding the measurement must not move the number that was already
    there — the raw figure stays the raw figure."""
    close = _close(rng)
    wf = walk_forward(close, transaction_cost=0.001, strategy="momentum")
    d = wf["deflated"]
    assert d["n_trials"] == wf["combinations_tested"]
    assert d["effective_trials"]["under_raw"]["deflated_sharpe_ratio"] == d["deflated_sharpe_ratio"]
    assert d["effective_trials"]["under_raw"]["expected_max_sharpe"] == d["expected_max_sharpe"]
