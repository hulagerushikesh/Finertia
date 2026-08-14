"""Portfolio construction — alignment, weighting, aggregation, attribution."""

import numpy as np
import pandas as pd
import pytest

from portfolio import (
    align_closes,
    equal_weights,
    inverse_vol_weights,
    combine,
    contribution_summary,
    diversification_ratio,
)


def dates(n, start="2022-01-03"):
    return pd.date_range(start, periods=n, freq="B")


def series(values, start="2022-01-03"):
    return pd.Series(values, index=dates(len(values), start), dtype=float)


def frame(cols: dict, start="2022-01-03"):
    n = len(next(iter(cols.values())))
    return pd.DataFrame(cols, index=dates(n, start), dtype=float)


class TestAlignment:
    def test_identical_calendars_keep_every_bar(self):
        out = align_closes({"A": series([1, 2, 3]), "B": series([4, 5, 6])})
        assert len(out) == 3
        assert list(out.columns) == ["A", "B"]

    def test_keeps_only_shared_dates(self):
        a = series([1, 2, 3, 4])                      # starts 2022-01-03
        b = series([9, 9, 9], start="2022-01-04")     # starts a day later
        out = align_closes({"A": a, "B": b})
        assert len(out) == 3
        assert out.index[0] == pd.Timestamp("2022-01-04")

    def test_a_late_listing_truncates_the_portfolio(self):
        # This is the cost of an inner join and the caller must surface it.
        long_history = series([1] * 10)
        late = series([1] * 3, start="2022-01-12")
        out = align_closes({"OLD": long_history, "NEW": late})
        assert len(out) == 3

    def test_no_overlap_raises_a_clear_error(self):
        a = series([1, 2, 3])
        b = series([1, 2, 3], start="2023-06-01")
        with pytest.raises(ValueError, match="no overlapping trading days"):
            align_closes({"A": a, "B": b})

    def test_empty_input_is_rejected(self):
        with pytest.raises(ValueError, match="No tickers"):
            align_closes({})

    def test_a_gap_in_one_series_drops_that_bar_rather_than_filling_it(self):
        # Forward-filling would invent a flat return on a non-trading day, which
        # lowers measured volatility and flatters every risk metric.
        a = series([1, 2, 3, 4])
        b = pd.Series([1, np.nan, 3, 4], index=dates(4), dtype=float)
        out = align_closes({"A": a, "B": b})
        assert len(out) == 3


class TestEqualWeights:
    def test_every_asset_gets_one_over_n(self):
        w = equal_weights(["A", "B", "C", "D"], dates(5))
        assert (w == 0.25).all().all()

    def test_weights_sum_to_one_on_every_bar(self):
        w = equal_weights(["A", "B", "C"], dates(5))
        assert np.allclose(w.sum(axis=1), 1.0)

    def test_rejects_an_empty_book(self):
        with pytest.raises(ValueError, match="No tickers"):
            equal_weights([], dates(3))


class TestInverseVolWeights:
    def test_the_quieter_asset_gets_the_bigger_weight(self):
        rets = frame({
            "CALM": [0.001, -0.001] * 30,
            "WILD": [0.05, -0.05] * 30,
        })
        w = inverse_vol_weights(rets, window=10)
        assert w["CALM"].iloc[-1] > w["WILD"].iloc[-1]

    def test_weights_always_sum_to_one(self):
        rets = frame({"A": [0.01, -0.02] * 30, "B": [0.03, -0.01] * 30})
        w = inverse_vol_weights(rets, window=10)
        assert np.allclose(w.sum(axis=1), 1.0)

    def test_warmup_falls_back_to_equal_weight(self):
        # Sizing to zero would silently shorten the period being measured.
        rets = frame({"A": [0.01, -0.01] * 30, "B": [0.02, -0.02] * 30})
        w = inverse_vol_weights(rets, window=10)
        assert np.allclose(w.iloc[0], 0.5)

    def test_never_uses_the_current_bar(self):
        # A volatility explosion on the last bar must not reweight that bar.
        rets = frame({"A": [0.01] * 30 + [0.9], "B": [0.01] * 31})
        w = inverse_vol_weights(rets, window=10)
        assert w["A"].iloc[-1] == pytest.approx(w["A"].iloc[-2])

    def test_a_zero_volatility_asset_does_not_take_the_whole_book(self):
        rets = frame({"FLAT": [0.0] * 40, "MOVER": [0.01, -0.01] * 20})
        w = inverse_vol_weights(rets, window=10)
        assert np.isfinite(w.to_numpy()).all()
        assert w["FLAT"].max() <= 1.0

    def test_max_weight_actually_caps_concentration(self):
        # Regression: clip-then-renormalise scaled the capped asset straight
        # back up (0.998 -> 0.997) and the cap achieved nothing.
        rets = frame({
            "CALM": [0.0001, -0.0001] * 30,
            "WILD": [0.08, -0.08] * 30,
        })
        w = inverse_vol_weights(rets, window=10, max_weight=0.6)
        assert w["CALM"].max() <= 0.6 + 1e-9

    def test_capped_weights_still_sum_to_one(self):
        rets = frame({"A": [0.0001, -0.0001] * 30, "B": [0.08, -0.08] * 30})
        w = inverse_vol_weights(rets, window=10, max_weight=0.6)
        assert np.allclose(w.sum(axis=1), 1.0)

    def test_freed_weight_goes_to_the_asset_with_room(self):
        rets = frame({"A": [0.0001, -0.0001] * 30, "B": [0.08, -0.08] * 30})
        w = inverse_vol_weights(rets, window=10, max_weight=0.6)
        assert w["B"].iloc[-1] == pytest.approx(0.4, abs=1e-9)

    def test_capping_holds_across_three_assets(self):
        rets = frame({
            "A": [0.0001, -0.0001] * 30,
            "B": [0.0002, -0.0002] * 30,
            "C": [0.09, -0.09] * 30,
        })
        w = inverse_vol_weights(rets, window=10, max_weight=0.5)
        assert w.max().max() <= 0.5 + 1e-9
        assert np.allclose(w.sum(axis=1), 1.0)

    def test_a_cap_too_small_to_fill_the_book_is_rejected(self):
        # Two assets capped at 0.4 hold at most 0.8; silently returning weights
        # that sum to 0.8 would understate every return.
        rets = frame({"A": [0.01] * 20, "B": [0.01] * 20})
        with pytest.raises(ValueError, match="cannot fill a book"):
            inverse_vol_weights(rets, window=10, max_weight=0.4)

    @pytest.mark.parametrize("kwargs,msg", [
        ({"window": 1}, "window"),
        ({"max_weight": 0}, "max_weight"),
        ({"max_weight": 1.5}, "max_weight"),
    ])
    def test_rejects_nonsense_parameters(self, kwargs, msg):
        rets = frame({"A": [0.01] * 20, "B": [0.01] * 20})
        with pytest.raises(ValueError, match=msg):
            inverse_vol_weights(rets, **kwargs)


class TestCombine:
    def test_equal_weights_average_the_legs(self):
        legs = frame({"A": [0.10, 0.0], "B": [0.0, 0.10]})
        w = equal_weights(["A", "B"], legs.index)
        out = combine(legs, w)
        assert out["net_return"].tolist() == pytest.approx([0.05, 0.05])

    def test_equity_compounds_the_portfolio_return(self):
        legs = frame({"A": [0.10, 0.10], "B": [0.10, 0.10]})
        w = equal_weights(["A", "B"], legs.index)
        out = combine(legs, w)
        assert out["equity_curve"].iloc[-1] == pytest.approx(1.21)

    def test_offsetting_legs_produce_a_flat_portfolio(self):
        legs = frame({"A": [0.10, -0.10], "B": [-0.10, 0.10]})
        out = combine(legs, equal_weights(["A", "B"], legs.index))
        assert out["net_return"].abs().max() == pytest.approx(0.0)

    def test_drawdown_is_zero_while_climbing(self):
        legs = frame({"A": [0.01] * 5, "B": [0.01] * 5})
        out = combine(legs, equal_weights(["A", "B"], legs.index))
        assert out["drawdown"].abs().max() == pytest.approx(0.0)

    def test_drawdown_measures_from_the_peak(self):
        legs = frame({"A": [0.20, -0.20], "B": [0.20, -0.20]})
        out = combine(legs, equal_weights(["A", "B"], legs.index))
        assert out["drawdown"].iloc[-1] == pytest.approx(-0.20)

    def test_nan_leg_returns_contribute_nothing(self):
        legs = pd.DataFrame(
            {"A": [0.10, 0.10], "B": [np.nan, 0.10]}, index=dates(2), dtype=float
        )
        out = combine(legs, equal_weights(["A", "B"], legs.index))
        assert out["net_return"].iloc[0] == pytest.approx(0.05)

    def test_mismatched_columns_are_rejected(self):
        legs = frame({"A": [0.01], "B": [0.01]})
        w = equal_weights(["A", "C"], legs.index)
        with pytest.raises(ValueError, match="same tickers"):
            combine(legs, w)


class TestAttribution:
    def test_contributions_sum_to_the_arithmetic_total(self):
        legs = frame({"A": [0.10, 0.02], "B": [-0.04, 0.06]})
        out = combine(legs, equal_weights(["A", "B"], legs.index))
        summary = contribution_summary(out["contributions"])
        assert sum(summary.values()) == pytest.approx(out["net_return"].sum())

    def test_a_losing_leg_shows_a_negative_contribution(self):
        legs = frame({"WINNER": [0.10, 0.10], "LOSER": [-0.05, -0.05]})
        out = combine(legs, equal_weights(["WINNER", "LOSER"], legs.index))
        summary = contribution_summary(out["contributions"])
        assert summary["LOSER"] < 0 < summary["WINNER"]


class TestDiversificationRatio:
    def test_identical_legs_buy_no_diversification(self):
        legs = frame({"A": [0.02, -0.01, 0.03] * 10, "B": [0.02, -0.01, 0.03] * 10})
        w = equal_weights(["A", "B"], legs.index)
        out = combine(legs, w)
        assert diversification_ratio(legs, w, out["net_return"]) == pytest.approx(1.0, abs=1e-6)

    def test_imperfectly_correlated_legs_diversify(self):
        legs = frame({
            "A": [0.02, -0.01, 0.03, 0.00, -0.02] * 8,
            "B": [-0.01, 0.02, -0.005, 0.01, 0.015] * 8,
        })
        w = equal_weights(["A", "B"], legs.index)
        out = combine(legs, w)
        assert diversification_ratio(legs, w, out["net_return"]) > 1.0

    def test_perfectly_offsetting_legs_report_undefined_not_zero(self):
        # The ratio diverges here — the legs are maximally diversified. Reporting
        # 0.0 would read as "bought no diversification", the exact opposite.
        legs = frame({"A": [0.02, -0.02] * 15, "B": [-0.02, 0.02] * 15})
        w = equal_weights(["A", "B"], legs.index)
        out = combine(legs, w)
        assert diversification_ratio(legs, w, out["net_return"]) is None

    def test_a_motionless_portfolio_also_reports_undefined(self):
        legs = frame({"A": [0.0] * 10, "B": [0.0] * 10})
        w = equal_weights(["A", "B"], legs.index)
        out = combine(legs, w)
        assert diversification_ratio(legs, w, out["net_return"]) is None
