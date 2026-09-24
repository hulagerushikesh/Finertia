"""Cost sensitivity, aimed at the two claims the module makes on the page.

The breakeven number is a promise: "run it again at this cost and the Sharpe
will be zero." So the central test does exactly that — takes the returned
breakeven, feeds it back through the real engine, and reads the Sharpe off
`compute_metrics`. Anything less checks the bisection against itself.

The second exposure is the shortcut. The bisection reconstructs net returns
instead of calling `apply_positions` forty times, which is a second copy of
the engine's cost arithmetic — including the bar-0 turnover rule that is easy
to leave out. One test pins the copy to the original.

Nine mutations, seven caught. The two survivors were both checked rather than
waved through, and neither is worth a test:

  `net <= -1.0` -> `net < -1.0` in the wipeout guard. Proven equivalent: the
  breakeven came back bit-identical on all 40 random position/return pairs,
  because log1p(-1.0) is -inf and the growth sum is -inf either way. The guard
  buys a suppressed divide-by-zero warning, not a different answer.

  Bracketing at the wipeout cost exactly instead of a hair below it. Not
  equivalent — 12 of 40 cases moved — but by at most 1.9e-12 in cost, which is
  a hundred-millionth of a basis point and an order of magnitude inside the
  module's own bisection tolerance. A test that caught this would be pinning
  float noise.
"""

import numpy as np
import pandas as pd
import pytest

from costs import (
    CURVE_ABSOLUTE,
    CURVE_MULTIPLES,
    _log_growth,
    _turnover,
    _wipeout_cost,
    breakeven_cost,
    cost_sensitivity,
)
from engine import apply_positions
from metrics import compute_metrics


def _sharpe_at(position, returns, cost):
    out = apply_positions(position, returns, cost)
    return compute_metrics(
        out["net_return"].fillna(0),
        out["equity_curve"].fillna(1),
        out["drawdown"].fillna(0),
        out["position"],
    )["sharpe_ratio"]


@pytest.fixture
def winning():
    """A strategy with a real edge and real turnover.

    Drift is positive on the bars it holds, so there is something for costs to
    eat; it flips often enough that the cost is not a rounding error.
    """
    rng = np.random.default_rng(11)
    n = 600
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    returns = pd.Series(rng.normal(0.0012, 0.012, n), index=idx)
    position = pd.Series(np.where(np.arange(n) % 7 < 4, 1.0, 0.0), index=idx)
    return position, returns


def test_the_breakeven_cost_actually_zeroes_the_sharpe(winning):
    position, returns = winning
    cost, status = breakeven_cost(position, returns)
    assert status == "measured"
    assert cost > 0
    assert _sharpe_at(position, returns, cost) == pytest.approx(0.0, abs=1e-4)


def test_either_side_of_the_breakeven_straddles_zero(winning):
    """A root is only meaningful if the function crosses there."""
    position, returns = winning
    cost, _ = breakeven_cost(position, returns)
    assert _sharpe_at(position, returns, cost * 0.9) > 0
    assert _sharpe_at(position, returns, cost * 1.1) < 0


def test_the_fast_path_matches_the_engine(winning):
    """The bisection's reconstructed net return is the engine's, bar 0 included."""
    position, returns = winning
    gross = (position * returns.fillna(0.0)).to_numpy(dtype=float)
    turnover = _turnover(position).to_numpy(dtype=float)
    for cost in (0.0, 0.0005, 0.004, 0.02):
        engine_net = apply_positions(position, returns, cost)["net_return"].fillna(0)
        assert np.allclose(gross - turnover * cost, engine_net.to_numpy())
        assert _log_growth(gross, turnover, cost) == pytest.approx(
            float(np.log1p(engine_net.to_numpy()).sum())
        )


def test_bar_zero_turnover_is_charged():
    """A position that opens on bar 0 has nothing to diff against.

    engine.py measures that bar from flat. If the shortcut dropped the rule it
    would silently hand back a breakeven that is too generous.
    """
    idx = pd.date_range("2020-01-01", periods=5, freq="B")
    position = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0], index=idx)
    returns = pd.Series([0.01] * 5, index=idx)
    assert _turnover(position).iloc[0] == 1.0
    # One unit of turnover over the whole path, so the cost bites exactly once.
    assert _log_growth(position * returns, _turnover(position).to_numpy(), 0.01) < (
        _log_growth(position * returns, _turnover(position).to_numpy(), 0.0)
    )


def test_a_strategy_that_never_trades_has_no_breakeven():
    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    position = pd.Series(0.0, index=idx)
    returns = pd.Series(0.001, index=idx)
    cost, status = breakeven_cost(position, returns)
    assert status == "no_trades"
    assert cost is None


def test_a_losing_strategy_reports_no_edge_rather_than_a_breakeven():
    """Costs are not what killed it, so there is no headroom to quote."""
    rng = np.random.default_rng(3)
    n = 400
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    returns = pd.Series(rng.normal(-0.002, 0.01, n), index=idx)
    position = pd.Series(np.where(np.arange(n) % 5 < 3, 1.0, 0.0), index=idx)
    cost, status = breakeven_cost(position, returns)
    assert status == "unprofitable"
    assert cost == 0.0
    assert cost_sensitivity(position, returns, 0.001)["headroom"] is None


def test_the_breakeven_stays_below_the_wipeout_bound(winning):
    """Past the wipeout the annualised return is pinned at -1 and the root
    would be an artefact of that pin rather than a crossing."""
    position, returns = winning
    gross = (position * returns.fillna(0.0)).to_numpy(dtype=float)
    turnover = _turnover(position).to_numpy(dtype=float)
    cost, _ = breakeven_cost(position, returns)
    assert 0 < cost < _wipeout_cost(gross, turnover)


def test_headroom_is_the_breakeven_over_the_assumption(winning):
    position, returns = winning
    out = cost_sensitivity(position, returns, 0.001)
    assert out["status"] == "measured"
    assert out["headroom"] == pytest.approx(out["breakeven_cost"] / 0.001, rel=1e-3)


def test_the_curve_is_what_a_rerun_would_show(winning):
    """Each point must equal a real backtest at that cost, not a rescaling."""
    position, returns = winning
    assumed = 0.001
    out = cost_sensitivity(position, returns, assumed)
    assert [p["cost"] for p in out["curve"]] == [
        round(assumed * m, 8) for m in CURVE_MULTIPLES
    ]
    for point in out["curve"]:
        assert point["sharpe_ratio"] == pytest.approx(
            _sharpe_at(position, returns, point["cost"]), abs=1e-6
        )


def test_the_curve_falls_as_costs_rise(winning):
    position, returns = winning
    sharpes = [p["sharpe_ratio"] for p in cost_sensitivity(position, returns, 0.001)["curve"]]
    assert sharpes == sorted(sharpes, reverse=True)


def test_a_zero_cost_assumption_falls_back_to_absolute_levels(winning):
    """Multiples of zero are all zero, which would make five identical points."""
    position, returns = winning
    out = cost_sensitivity(position, returns, 0.0)
    assert [p["cost"] for p in out["curve"]] == [round(c, 8) for c in CURVE_ABSOLUTE]
    assert out["headroom"] is None
    assert out["breakeven_cost"] > 0


def test_more_turnover_lowers_the_breakeven():
    """The same edge spread over twice the trades survives half the charge."""
    rng = np.random.default_rng(5)
    n = 500
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    returns = pd.Series(rng.normal(0.0015, 0.01, n), index=idx)
    steady = pd.Series(np.where(np.arange(n) % 20 < 10, 1.0, 0.0), index=idx)
    churny = pd.Series(np.where(np.arange(n) % 4 < 2, 1.0, 0.0), index=idx)
    assert breakeven_cost(churny, returns)[0] < breakeven_cost(steady, returns)[0]


def test_the_wipeout_bound_is_the_smallest_cost_that_breaks_the_curve(winning):
    """It brackets the bisection, so it has to be the FIRST bar to go under.

    Taking the max instead would still converge — the growth function is -inf
    above the true bound either way — which is exactly why this needs asserting
    against the definition rather than against the root it produces.
    """
    position, returns = winning
    gross = (position * returns.fillna(0.0)).to_numpy(dtype=float)
    turnover = _turnover(position).to_numpy(dtype=float)
    bound = _wipeout_cost(gross, turnover)
    assert _log_growth(gross, turnover, bound * (1 - 1e-6)) > -np.inf
    assert _log_growth(gross, turnover, bound * (1 + 1e-6)) == -np.inf


def test_an_edge_of_exactly_nothing_is_not_an_edge():
    """Growth of exactly zero before costs sits on the guard's boundary.

    Flat returns with real turnover make sum(log1p(net)) exactly 0.0 at zero
    cost — no float slop. The strategy has nothing for a cost to eat, so the
    honest answer is "unprofitable", not a breakeven of approximately zero
    dressed up as a measurement.
    """
    idx = pd.date_range("2020-01-01", periods=3, freq="B")
    position = pd.Series([1.0, 0.0, 1.0], index=idx)
    returns = pd.Series([0.0, 0.0, 0.0], index=idx)
    gross = (position * returns).to_numpy(dtype=float)
    assert _log_growth(gross, _turnover(position).to_numpy(), 0.0) == 0.0
    cost, status = breakeven_cost(position, returns)
    assert status == "unprofitable"
    assert cost == 0.0
