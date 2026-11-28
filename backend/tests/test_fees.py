"""Market cost models (fees.py) and how a request resolves them."""

import json
from pathlib import Path

import pytest

import fees
from schemas import BacktestRequest
from tests.test_routes import AUTH, api  # noqa: F401 — the fixture

BASE = {"ticker": "AAPL", "start": "2020-01-01", "end": "2022-06-01", "strategy": "momentum"}


def test_india_delivery_adds_up_charge_by_charge():
    b = fees.breakdown("india", slippage_bps=0)
    # STT 0.1% both sides; stamp 0.015% on buys; exchange 0.00307% and SEBI
    # 0.0001% both sides; GST 18% on those two.
    gst = 0.18 * (0.0000307 + 0.000001)
    assert b["buy"] == pytest.approx(0.001 + 0.00015 + 0.0000307 + 0.000001 + gst)
    assert b["sell"] == pytest.approx(0.001 + 0.0000307 + 0.000001 + gst)
    assert b["per_side"] == pytest.approx((b["buy"] + b["sell"]) / 2)
    assert b["round_trip"] == pytest.approx(b["buy"] + b["sell"])
    # About 22.5 bps a round trip before slippage — STT is most of it.
    assert 0.00222 < b["round_trip"] < 0.00228


def test_us_is_slippage_plus_the_sec_fee_on_sales():
    b = fees.breakdown("us", slippage_bps=2)
    assert b["buy"] == pytest.approx(0.0002)
    assert b["sell"] == pytest.approx(0.0002 + 20.60 / 1_000_000)
    assert [c["id"] for c in b["charges"]][-1] == "slippage"


def test_an_unknown_model_is_named():
    with pytest.raises(ValueError, match="flat, auto, us, india"):
        fees.breakdown("uk")


def test_a_market_model_replaces_the_typed_cost():
    req = BacktestRequest(**BASE, cost_model="india", slippage_bps=3, transaction_cost=0.05)
    assert req.transaction_cost == pytest.approx(fees.per_side("india", 3))
    assert req.cost_params() == {"cost_model": "india", "slippage_bps": 3}


def test_flat_keeps_the_typed_cost_and_ignores_slippage():
    req = BacktestRequest(**BASE, transaction_cost=0.002, slippage_bps=9)
    assert req.transaction_cost == 0.002
    assert req.slippage_bps == fees.DEFAULT_SLIPPAGE_BPS
    with pytest.raises(ValueError, match="cost_model must be one of"):
        BacktestRequest(**BASE, cost_model="crypto")


def test_the_front_end_table_matches_this_module():
    """The workspace shows the breakdown from a JSON copy; it must not drift."""
    copy = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "costModels.json"
    assert json.loads(copy.read_text()) == json.loads(json.dumps(fees.describe()))


def test_a_run_saves_how_its_cost_was_chosen_and_compare_redraws_it(api):  # noqa: F811
    client, state = api
    india = client.post("/api/backtest", json={**BASE, "cost_model": "india"}, headers=AUTH).json()
    flat = client.post("/api/backtest", json=BASE, headers=AUTH).json()
    saved = state["db"].store[f"runs/{india['runId']}"]["params"]
    assert saved["cost_model"] == "india"
    assert saved["transaction_cost"] == pytest.approx(fees.per_side("india"))
    # Dearer than the 10 bps default, so the same run ends lower.
    assert india["metrics"]["total_return"] < flat["metrics"]["total_return"]
    r = client.post("/api/compare", json={"run_ids": [india["runId"], flat["runId"]]}, headers=AUTH)
    assert r.status_code == 200, r.text
    assert r.json()["chart"][-1][india["runId"]] == india["equity_curve"][-1]["strategy"]


# ── auto: each symbol pays its own market's cost ────────────────────────────

def test_auto_reads_the_market_from_the_symbol():
    assert fees.market_for("RELIANCE.NS") == "india"
    assert fees.market_for("tcs.bo") == "india"
    assert fees.market_for("AAPL") == "us" and fees.market_for("BRK-B") == "us"
    india = BacktestRequest(**{**BASE, "ticker": "RELIANCE.NS"}, cost_model="auto")
    us = BacktestRequest(**BASE, cost_model="auto")
    assert india.transaction_cost == pytest.approx(fees.per_side("india"))
    assert us.transaction_cost == pytest.approx(fees.per_side("us"))


def test_a_mixed_basket_charges_each_leg_its_own_market(api):  # noqa: F811
    from schemas import PortfolioRequest
    from tests.test_routes import PORTFOLIO

    body = {**PORTFOLIO, "tickers": ["AAPL", "RELIANCE.NS"], "cost_model": "auto"}
    req = PortfolioRequest(**body)
    legs = req.leg_costs()
    assert legs["AAPL"] == pytest.approx(fees.per_side("us"))
    assert legs["RELIANCE.NS"] == pytest.approx(fees.per_side("india"))
    assert req.transaction_cost == pytest.approx((legs["AAPL"] + legs["RELIANCE.NS"]) / 2)

    client, _ = api
    auto = client.post("/api/portfolio", json=body, headers=AUTH).json()
    all_us = client.post("/api/portfolio", json={**body, "cost_model": "us"}, headers=AUTH).json()
    all_in = client.post("/api/portfolio", json={**body, "cost_model": "india"}, headers=AUTH).json()
    # Between the two single-market books, and the cost curve's 1× point is
    # the book as run.
    r = lambda b: b["metrics"]["total_return"]  # noqa: E731
    assert r(all_in) < r(auto) < r(all_us)
    one_x = auto["cost_sensitivity"]["curve"][2]
    assert one_x["total_return"] == pytest.approx(r(auto), abs=1e-6)


def test_a_mixed_basket_validates_with_per_leg_costs(api):  # noqa: F811
    from tests.test_routes import PORTFOLIO, PRO

    client, state = api
    state["profile"] = dict(PRO)
    body = {**PORTFOLIO, "tickers": ["AAPL", "RELIANCE.NS"], "cost_model": "auto"}
    r = client.post("/api/portfolio/validate", json=body, headers=AUTH)
    assert r.status_code == 200, r.text
