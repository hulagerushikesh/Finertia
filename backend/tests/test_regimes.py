"""Volatility regimes: label by the market's realised vol, break the
strategy's return down by label."""

import numpy as np
import pandas as pd
import pytest

from regimes import DEFAULT_WINDOW, MIN_BARS, TRADING_DAYS, label_regimes, regime_breakdown


def _idx(n, start="2019-01-01"):
    return pd.bdate_range(start, periods=n)


def _market(n=600, seed=0):
    """Three blocks of distinct volatility so the terciles are unambiguous."""
    rng = np.random.default_rng(seed)
    third = n // 3
    vols = np.concatenate([np.full(third, 0.004), np.full(third, 0.012), np.full(n - 2 * third, 0.030)])
    return pd.Series(vols * rng.standard_normal(n), index=_idx(n))


# --- labels -------------------------------------------------------------


def test_terciles_split_the_labelled_bars_three_ways():
    lab = label_regimes(_market())
    counts = lab["regime"].value_counts()
    labelled = lab["regime"].notna().sum()
    assert labelled == 600 - (DEFAULT_WINDOW - 1)
    for name in ("low", "mid", "high"):
        assert abs(counts[name] / labelled - 1 / 3) < 0.02


def test_first_window_bars_carry_no_label():
    lab = label_regimes(_market())
    assert lab["regime"].iloc[: DEFAULT_WINDOW - 1].isna().all()
    assert lab["regime"].iloc[DEFAULT_WINDOW - 1] is not None
    assert lab["realised_vol"].iloc[: DEFAULT_WINDOW - 1].isna().all()


def test_thresholds_are_the_cut_points_actually_used():
    lab = label_regimes(_market())
    thr = lab.attrs["thresholds"]
    v = lab.dropna()
    eps = 1e-6  # thresholds are reported rounded to 6 dp
    assert v.loc[v["regime"] == "low", "realised_vol"].max() <= thr["low_max"] + eps
    assert v.loc[v["regime"] == "mid", "realised_vol"].min() > thr["low_max"] - eps
    assert v.loc[v["regime"] == "mid", "realised_vol"].max() <= thr["high_min"] + eps
    assert v.loc[v["regime"] == "high", "realised_vol"].min() > thr["high_min"] - eps


def test_vol_is_the_trailing_window_std_annualised():
    m = _market()
    lab = label_regimes(m, window=21)
    t = 100
    expected = m.iloc[t - 20 : t + 1].std() * np.sqrt(TRADING_DAYS)
    assert lab["realised_vol"].iloc[t] == pytest.approx(expected, rel=1e-9)


def test_labels_follow_the_market_blocks():
    """Calm block → low, wild block → high, near enough that the label is
    doing what its name says."""
    lab = label_regimes(_market())["regime"]
    calm = lab.iloc[DEFAULT_WINDOW : 200]
    wild = lab.iloc[420:]
    assert (calm == "low").mean() > 0.9
    assert (wild == "high").mean() > 0.9


def test_too_few_bars_means_no_labels():
    lab = label_regimes(_market(n=MIN_BARS + DEFAULT_WINDOW - 5))
    assert lab["regime"].isna().all()
    assert lab.attrs["thresholds"]["low_max"] is None


def test_window_floor():
    with pytest.raises(ValueError, match="at least 5"):
        label_regimes(_market(), window=3)


# --- breakdown ------------------------------------------------------------


def _strategy_on(market, earns_in):
    """+0.5% on every bar of one regime, nothing elsewhere; long throughout."""
    lab = label_regimes(market)["regime"]
    net = pd.Series(np.where(lab == earns_in, 0.005, 0.0), index=market.index)
    pos = pd.Series(1.0, index=market.index)
    return net, pos


def test_a_strategy_that_earns_only_in_turbulence_says_so():
    m = _market()
    net, pos = _strategy_on(m, "high")
    b = regime_breakdown(net, pos, m)
    assert b["computable"]
    assert b["best_regime"] == "high"
    assert b["regimes"]["high"]["sharpe_ratio"] > 0
    assert b["regimes"]["low"]["contribution"] == 0.0
    assert b["regimes"]["high"]["share_of_return"] == pytest.approx(1.0)
    assert b["sharpe_spread"] > 0


def test_contributions_sum_to_the_arithmetic_total_of_labelled_bars():
    m = _market()
    rng = np.random.default_rng(3)
    net = pd.Series(0.01 * rng.standard_normal(len(m)), index=m.index)
    pos = pd.Series(rng.choice([-1.0, 0.0, 1.0], len(m)), index=m.index)
    b = regime_breakdown(net, pos, m)
    lab = label_regimes(m)["regime"]
    total = net[lab.notna()].sum()
    assert sum(r["contribution"] for r in b["regimes"].values()) == pytest.approx(total, abs=1e-5)
    assert sum(r["share_of_bars"] for r in b["regimes"].values()) == pytest.approx(1.0, abs=1e-5)
    assert b["labelled_bars"] + b["unlabelled_bars"] == len(net)


def test_regime_sharpe_is_mean_over_std_on_those_bars():
    m = _market()
    rng = np.random.default_rng(5)
    net = pd.Series(0.01 * rng.standard_normal(len(m)), index=m.index)
    pos = pd.Series(1.0, index=m.index)
    b = regime_breakdown(net, pos, m)
    lab = label_regimes(m)["regime"]
    seg = net[lab == "mid"]
    assert b["regimes"]["mid"]["sharpe_ratio"] == pytest.approx(
        seg.mean() / seg.std() * np.sqrt(TRADING_DAYS), abs=1e-5
    )
    mk = m[lab == "mid"]
    assert b["regimes"]["mid"]["market_sharpe_ratio"] == pytest.approx(
        mk.mean() / mk.std() * np.sqrt(TRADING_DAYS), abs=1e-5
    )


def test_labels_come_from_the_market_not_the_strategy():
    """A strategy that is flat everywhere has zero return variance. If the
    labels were computed on the strategy series they would collapse; on the
    market they are unaffected."""
    m = _market()
    net = pd.Series(0.0, index=m.index)
    pos = pd.Series(0.0, index=m.index)
    b = regime_breakdown(net, pos, m)
    assert b["computable"]
    assert all(b["regimes"][k]["bars"] > 0 for k in ("low", "mid", "high"))
    assert b["regimes"]["high"]["time_in_market"] == 0.0


def test_a_shorter_strategy_series_is_labelled_on_the_full_market():
    """Stitched out-of-sample series have gaps. The label for a bar must be
    the same whether or not the bars before it are in the strategy series."""
    m = _market()
    full = label_regimes(m)["regime"]
    keep = m.index[100:250].append(m.index[300:600])
    net = pd.Series(0.001, index=keep)
    pos = pd.Series(1.0, index=keep)
    b = regime_breakdown(net, pos, m)
    expected = full.loc[keep].value_counts()
    for name in ("low", "mid", "high"):
        assert b["regimes"][name]["bars"] == expected.get(name, 0)


def test_too_short_breakdown_degrades():
    m = _market(n=40)
    net = pd.Series(0.001, index=m.index)
    pos = pd.Series(1.0, index=m.index)
    b = regime_breakdown(net, pos, m)
    assert b == {"computable": False, "reason": b["reason"]}
    assert "too short" in b["reason"]


def test_share_of_return_is_undefined_when_the_total_is_nothing():
    m = _market()
    net = pd.Series(0.0, index=m.index)
    pos = pd.Series(1.0, index=m.index)
    b = regime_breakdown(net, pos, m)
    assert all(r["share_of_return"] is None for r in b["regimes"].values())
