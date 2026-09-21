"""Trend regimes: label by the direction of the market's trailing window,
break the strategy's return down by label, and cross it with volatility."""

import numpy as np
import pandas as pd
import pytest

from regimes import (
    LABELS,
    MIN_BARS,
    MIN_CELL_BARS,
    TREND_WINDOW,
    TRENDS,
    joint_breakdown,
    label_regimes,
    label_trend,
    regime_breakdown,
    trend_breakdown,
)


def _idx(n, start="2019-01-01"):
    return pd.bdate_range(start, periods=n)


def _drift(n=600, mu=0.0, vol=0.01, seed=0):
    rng = np.random.default_rng(seed)
    return pd.Series(mu + vol * rng.standard_normal(n), index=_idx(n))


def _market(n=900, seed=0):
    """Three volatility blocks, each split into a rising, a falling and a
    flat stretch whose drift scales with the block's vol, so every one of the
    nine vol x trend cells is populated and unambiguous."""
    rng = np.random.default_rng(seed)
    third = n // 3
    vols = np.concatenate([np.full(third, 0.004), np.full(third, 0.012), np.full(n - 2 * third, 0.030)])
    sign = np.zeros(n)
    for b in range(3):
        lo = b * third
        sub = third // 3
        sign[lo : lo + sub] = 1.0
        sign[lo + sub : lo + 2 * sub] = -1.0
    return pd.Series(sign * 0.5 * vols + vols * rng.standard_normal(n), index=_idx(n))


# --- labels -------------------------------------------------------------


def test_first_window_bars_carry_no_label():
    lab = label_trend(_drift())
    assert lab["trend"].iloc[: TREND_WINDOW - 1].isna().all()
    assert lab["trend_z"].iloc[: TREND_WINDOW - 1].isna().all()
    assert lab["trend"].iloc[TREND_WINDOW - 1] in TRENDS


def test_z_is_the_t_statistic_of_the_windows_mean_return():
    m = _drift()
    lab = label_trend(m, window=60)
    t = 200
    w = m.iloc[t - 59 : t + 1]
    expected = w.sum() / (w.std() * np.sqrt(60))
    assert lab["trend_z"].iloc[t] == pytest.approx(expected, rel=1e-9)
    assert lab["trend_z"].iloc[t] == pytest.approx(w.mean() / (w.std() / np.sqrt(60)), rel=1e-9)


def test_trend_return_is_the_compounded_window_return():
    m = _drift()
    lab = label_trend(m, window=60)
    t = 200
    assert lab["trend_return"].iloc[t] == pytest.approx((1 + m.iloc[t - 59 : t + 1]).prod() - 1, rel=1e-9)


def test_a_steady_drift_reads_up_or_down():
    up = label_trend(_drift(mu=0.002, vol=0.005))["trend"].dropna()
    down = label_trend(_drift(mu=-0.002, vol=0.005))["trend"].dropna()
    assert (up == "up").mean() > 0.95
    assert (down == "down").mean() > 0.95


def test_zero_mean_noise_is_mostly_flat():
    """z is roughly standard normal under no drift, so about two thirds of
    bars sit inside +-1 sigma."""
    lab = label_trend(_drift(n=3000, mu=0.0))["trend"].dropna()
    assert 0.55 < (lab == "flat").mean() < 0.8
    assert (lab == "up").sum() > 0 and (lab == "down").sum() > 0


def test_the_same_move_is_a_trend_in_calm_and_noise_in_turbulence():
    calm = label_trend(_drift(mu=0.002, vol=0.005))["trend"].dropna()
    loud = label_trend(_drift(mu=0.002, vol=0.05))["trend"].dropna()
    assert (calm == "up").mean() > 0.95
    assert (loud == "flat").mean() > 0.6


def test_a_window_with_no_variance_has_no_direction():
    m = pd.Series(0.001, index=_idx(200))
    lab = label_trend(m)
    assert (lab["trend"].dropna() == "flat").all()
    assert (lab["trend_z"].dropna() == 0).all()


def test_labels_sit_exactly_on_the_sigma_cut():
    lab = label_trend(_drift(n=3000), sigma=1.0).dropna()
    assert lab.loc[lab["trend"] == "up", "trend_z"].min() > 1.0
    assert lab.loc[lab["trend"] == "down", "trend_z"].max() < -1.0
    assert lab.loc[lab["trend"] == "flat", "trend_z"].abs().max() <= 1.0


def test_a_wider_cut_calls_more_bars_flat():
    m = _drift(n=3000)
    narrow = (label_trend(m, sigma=0.5)["trend"] == "flat").mean()
    wide = (label_trend(m, sigma=2.0)["trend"] == "flat").mean()
    assert wide > narrow


def test_floors():
    with pytest.raises(ValueError, match="at least 20"):
        label_trend(_drift(), window=10)
    with pytest.raises(ValueError, match="positive"):
        label_trend(_drift(), sigma=0)


# --- breakdown ----------------------------------------------------------


def test_a_strategy_that_earns_only_in_rising_markets_says_so():
    m = _market()
    lab = label_trend(m)["trend"]
    pos = (lab == "up").astype(float)
    net = pos * 0.003
    r = trend_breakdown(net, pos, m)
    assert r["computable"]
    assert r["best_regime"] == "up"
    assert r["regimes"]["up"]["sharpe_ratio"] > 5
    assert r["regimes"]["down"]["sharpe_ratio"] == 0.0
    assert r["regimes"]["down"]["time_in_market"] == 0.0


def test_contributions_sum_to_the_arithmetic_total_of_labelled_bars():
    m = _market()
    net = _drift(n=len(m), mu=0.0005, vol=0.008, seed=3)
    pos = pd.Series(1.0, index=m.index)
    r = trend_breakdown(net, pos, m)
    labelled = label_trend(m)["trend"].notna()
    assert sum(v["contribution"] for v in r["regimes"].values()) == pytest.approx(net[labelled].sum(), abs=1e-5)
    assert sum(v["share_of_bars"] for v in r["regimes"].values()) == pytest.approx(1.0, abs=1e-5)
    assert r["labelled_bars"] + r["unlabelled_bars"] == len(m)


def test_rows_carry_the_mean_z_on_the_right_side_of_the_cut():
    m = _market()
    net = _drift(n=len(m), seed=4)
    r = trend_breakdown(net, pd.Series(1.0, index=m.index), m)
    assert r["regimes"]["up"]["mean_trend_z"] > 1
    assert r["regimes"]["down"]["mean_trend_z"] < -1
    assert abs(r["regimes"]["flat"]["mean_trend_z"]) <= 1
    assert r["regimes"]["up"]["mean_trend_return"] > 0 > r["regimes"]["down"]["mean_trend_return"]


def test_labels_come_from_the_market_not_the_strategy():
    m = _market()
    a = trend_breakdown(_drift(n=len(m), seed=1), pd.Series(1.0, index=m.index), m)
    b = trend_breakdown(_drift(n=len(m), mu=0.01, seed=2), pd.Series(1.0, index=m.index), m)
    for k in TRENDS:
        assert a["regimes"][k]["bars"] == b["regimes"][k]["bars"]


def test_too_short_degrades():
    m = _drift(n=TREND_WINDOW + MIN_BARS - 5)
    r = trend_breakdown(m * 0, pd.Series(1.0, index=m.index), m)
    assert r["computable"] is False
    assert "too short" in r["reason"]


# --- vol x trend --------------------------------------------------------


def test_joint_cells_partition_the_doubly_labelled_bars():
    m = _market()
    vol = label_regimes(m)["regime"]
    trend = label_trend(m)["trend"]
    net = _drift(n=len(m), seed=5)
    r = joint_breakdown(net, vol, trend)
    assert r["computable"]
    cells = r["cells"]
    assert set(cells) == set(LABELS) and all(set(cells[v]) == set(TRENDS) for v in LABELS)
    assert sum(cells[v][t]["bars"] for v in LABELS for t in TRENDS) == r["labelled_bars"]
    assert r["labelled_bars"] == int((vol.notna() & trend.notna()).sum())
    both = pd.DataFrame({"v": vol, "t": trend}).dropna()
    for v in LABELS:
        for t in TRENDS:
            assert cells[v][t]["bars"] == int(((both["v"] == v) & (both["t"] == t)).sum())


def test_every_cell_of_the_designed_market_is_scored():
    m = _market()
    r = joint_breakdown(_drift(n=len(m), seed=5), label_regimes(m)["regime"], label_trend(m)["trend"])
    assert r["scored_cells"] == 9
    for v in LABELS:
        for t in TRENDS:
            assert r["cells"][v][t]["bars"] >= MIN_CELL_BARS
            assert r["cells"][v][t]["sharpe_ratio"] is not None


def test_a_sparse_cell_reports_its_count_and_no_sharpe():
    m = _drift(n=900, mu=0.0, vol=0.01)
    vol = label_regimes(m)["regime"]
    # Force one cell to be nearly empty: relabel all but 5 of the low-vol
    # bars' trend as flat.
    trend = label_trend(m)["trend"].copy()
    low_up = trend[(vol == "low") & (trend == "up")].index
    trend.loc[low_up[5:]] = "flat"
    r = joint_breakdown(m, vol, trend)
    assert r["cells"]["low"]["up"]["bars"] == 5
    assert r["cells"]["low"]["up"]["sharpe_ratio"] is None
    assert r["scored_cells"] < 9


def test_calm_and_rising_is_found_when_that_is_where_the_return_is():
    """The case the label exists for: a strategy that earns only in calm,
    rising markets — invisible to the vol label alone, which would just
    say 'calm'."""
    m = _market()
    vol = label_regimes(m)["regime"]
    trend = label_trend(m)["trend"]
    pos = ((vol == "low") & (trend == "up")).astype(float)
    net = pos * 0.002 + _drift(n=len(m), vol=0.001, seed=6)
    r = joint_breakdown(net, vol, trend)
    assert (r["best_cell"]["vol"], r["best_cell"]["trend"]) == ("low", "up")
    assert r["best_cell"]["sharpe_ratio"] == r["cells"]["low"]["up"]["sharpe_ratio"]
    assert r["sharpe_spread"] == pytest.approx(r["best_cell"]["sharpe_ratio"] - r["worst_cell"]["sharpe_ratio"], abs=1e-6)
    # And the trend block alone already points the right way.
    t = trend_breakdown(net, pos, m)
    assert t["best_regime"] == "up"


def test_regime_breakdown_carries_both_axes():
    m = _market()
    net = _drift(n=len(m), seed=7)
    pos = pd.Series(1.0, index=m.index)
    r = regime_breakdown(net, pos, m)
    assert r["computable"]
    assert r["trend"]["computable"] and r["joint"]["computable"]
    assert set(r["trend"]["regimes"]) == set(TRENDS)
    assert r["trend"] == trend_breakdown(net, pos, m)
    assert r["joint"] == joint_breakdown(net, label_regimes(m)["regime"], label_trend(m)["trend"])


def test_regime_breakdown_degrades_trend_when_the_vol_label_still_fits():
    """Vol needs 63 labelled bars on a 21 window; trend needs 63 on a 60
    window. In between, vol reads and trend does not."""
    n = 100
    m = _drift(n=n)
    r = regime_breakdown(m, pd.Series(1.0, index=m.index), m)
    assert r["computable"]
    assert r["trend"]["computable"] is False
    assert r["joint"]["computable"] is False
