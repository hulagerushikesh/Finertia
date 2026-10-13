"""The onboarding examples in frontend/src/data/sampleStrategies.json are
configs the API accepts and runs, on the free plan.

The request models ignore unknown fields, so a misspelt key in the JSON would
not fail a request: it would quietly run the default instead. Each key is
checked against the model first.
"""

import json
from pathlib import Path

import pytest

from schemas import BacktestRequest, PortfolioRequest
from test_routes import AUTH, FREE, _prices, api  # noqa: F401 — `api` is a fixture

import main

SAMPLES = json.loads(
    (Path(__file__).resolve().parents[2] / "frontend/src/data/sampleStrategies.json").read_text()
)["samples"]


def request_for(sample):
    params = dict(sample["params"])
    portfolio = params.pop("mode") == "portfolio"
    return ("/api/portfolio" if portfolio else "/api/backtest",
            PortfolioRequest if portfolio else BacktestRequest,
            params)


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_every_key_is_a_field_the_api_reads(sample):
    _, model, params = request_for(sample)
    assert set(params) <= set(model.model_fields), set(params) - set(model.model_fields)
    model(**params)  # and every value is inside the model's bounds


@pytest.mark.parametrize("sample", SAMPLES, ids=[s["id"] for s in SAMPLES])
def test_a_free_account_can_run_it(api, monkeypatch, sample):
    client, state = api
    state["profile"] = dict(FREE)
    monkeypatch.setattr(main, "fetch_ohlcv", lambda t, s, e: _prices(days=1500, start=s))
    path, _, params = request_for(sample)
    r = client.post(path, json=params, headers=AUTH)
    assert r.status_code == 200, r.json()
