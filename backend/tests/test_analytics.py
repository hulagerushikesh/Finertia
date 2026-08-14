"""Monthly, annual, and rolling views of a backtest."""

import numpy as np
import pandas as pd
import pytest

from analytics import monthly_returns, annual_returns, rolling_sharpe


def daily(values, start="2020-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


class TestMonthlyReturns:
    def test_one_entry_per_calendar_month(self):
        r = monthly_returns(daily([0.001] * 70))  # Jan + Feb + a little March
        months = {(e["year"], e["month"]) for e in r}
        assert months == {(2020, 1), (2020, 2), (2020, 3)}

    def test_compounds_rather_than_sums(self):
        # Two +10% days compound to 21%, not 20%.
        r = monthly_returns(daily([0.10, 0.10]))
        assert r[0]["return"] == pytest.approx(0.21, abs=1e-6)

    def test_negative_month_reported_negative(self):
        r = monthly_returns(daily([-0.05, -0.05]))
        assert r[0]["return"] < 0

    def test_flat_month_is_zero(self):
        r = monthly_returns(daily([0.0] * 20))
        assert r[0]["return"] == pytest.approx(0.0)

    def test_empty_series_returns_empty_list(self):
        assert monthly_returns(pd.Series([], dtype=float, index=pd.DatetimeIndex([]))) == []

    def test_spans_a_year_boundary(self):
        r = monthly_returns(daily([0.001] * 40, start="2020-12-15"))
        assert {(e["year"], e["month"]) for e in r} == {(2020, 12), (2021, 1)}


class TestAnnualReturns:
    def test_one_entry_per_year(self):
        strat = daily([0.001] * 400)
        bench = daily([0.002] * 400)
        r = annual_returns(strat, bench)
        assert [e["year"] for e in r] == [2020, 2021]

    def test_reports_both_series(self):
        strat = daily([0.01] * 10)
        bench = daily([0.02] * 10)
        r = annual_returns(strat, bench)
        assert r[0]["strategy"] == pytest.approx((1.01 ** 10) - 1, abs=1e-6)
        assert r[0]["benchmark"] == pytest.approx((1.02 ** 10) - 1, abs=1e-6)

    def test_strategy_can_lose_while_benchmark_gains(self):
        r = annual_returns(daily([-0.01] * 10), daily([0.01] * 10))
        assert r[0]["strategy"] < 0 < r[0]["benchmark"]

    def test_empty_series_returns_empty_list(self):
        empty = pd.Series([], dtype=float, index=pd.DatetimeIndex([]))
        assert annual_returns(empty, empty) == []

    def test_missing_benchmark_year_defaults_to_zero(self):
        strat = daily([0.001] * 400)                      # 2020 and 2021
        bench = daily([0.001] * 10)                       # 2020 only
        r = annual_returns(strat, bench)
        assert r[1]["year"] == 2021
        assert r[1]["benchmark"] == 0.0


class TestRollingSharpe:
    def test_empty_until_the_window_fills(self):
        assert rolling_sharpe(daily([0.01] * 30), window=60) == []

    def test_emits_one_point_per_bar_after_warmup(self):
        rng = np.random.default_rng(0)
        s = daily(rng.normal(0.001, 0.01, 200))
        pts = rolling_sharpe(s, window=60)
        assert len(pts) == 200 - 60 + 1

    def test_positive_drift_gives_positive_sharpe(self):
        rng = np.random.default_rng(1)
        s = daily(rng.normal(0.004, 0.005, 200))
        assert rolling_sharpe(s, window=60)[-1]["value"] > 0

    def test_negative_drift_gives_negative_sharpe(self):
        rng = np.random.default_rng(2)
        s = daily(rng.normal(-0.004, 0.005, 200))
        assert rolling_sharpe(s, window=60)[-1]["value"] < 0

    def test_constant_returns_produce_no_points(self):
        # Zero variance makes Sharpe infinite; those points are dropped, not emitted.
        assert rolling_sharpe(daily([0.01] * 100), window=60) == []

    def test_dates_are_iso_formatted_and_ordered(self):
        rng = np.random.default_rng(3)
        pts = rolling_sharpe(daily(rng.normal(0.001, 0.01, 120)), window=60)
        dates = [p["date"] for p in pts]
        assert dates == sorted(dates)
        assert len(dates[0]) == 10 and dates[0].count("-") == 2

    def test_no_nan_or_infinite_values_leak_through(self):
        rng = np.random.default_rng(4)
        s = daily(np.concatenate([np.zeros(70), rng.normal(0.001, 0.01, 130)]))
        assert all(np.isfinite(p["value"]) for p in rolling_sharpe(s, window=60))
