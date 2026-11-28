"""Saved rules (api/routes/saved_rules.py): save, list, rename, delete, limits."""

import pytest

from api.routes import saved_rules
from tests.test_routes import AUTH, api  # noqa: F401 — the fixture

RULE = {
    "direction": "long",
    "entry": {"all": [{"left": {"ind": "rsi", "n": 14}, "op": "<", "right": {"value": 30}}]},
    "exit": {"all": [{"left": {"ind": "rsi", "n": 14}, "op": ">", "right": {"value": 55}}]},
}


def save(client, name="RSI dip", rule=RULE):
    return client.post("/api/rules", json={"name": name, "rule": rule}, headers=AUTH)


def test_a_rule_is_saved_listed_and_comes_back_runnable(api):  # noqa: F811
    client, state = api
    r = save(client, "  RSI   dip ")
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["name"] == "RSI dip"  # spaces tidied
    listed = client.get("/api/rules", headers=AUTH).json()
    assert listed["max"] == saved_rules.MAX_SAVED
    assert [x["name"] for x in listed["rules"]] == ["RSI dip"]
    # The stored rule is the validator's canonical form, so it runs as saved.
    bt = client.post("/api/backtest", json={
        "ticker": "AAPL", "start": "2020-01-01", "end": "2022-06-01",
        "strategy": "rules", "rule": listed["rules"][0]["rule"],
    }, headers=AUTH)
    assert bt.status_code == 200, bt.text
    assert state["db"].store[f"rules/{saved['id']}"]["uid"] == "u1"


def test_a_broken_rule_is_refused_with_the_reason(api):  # noqa: F811
    client, _ = api
    r = save(client, rule={**RULE, "direction": "up"})
    assert r.status_code == 422 and "direction must be long or short" in r.text
    assert save(client, name="   ").status_code == 422


def test_names_are_unique_per_user_ignoring_case(api):  # noqa: F811
    client, state = api
    assert save(client, "RSI dip").status_code == 201
    assert save(client, "rsi DIP").status_code == 409
    state["uid"] = "u2"  # someone else may use the same name
    assert save(client, "RSI dip").status_code == 201


def test_the_library_is_capped(api, monkeypatch):  # noqa: F811
    client, _ = api
    monkeypatch.setattr(saved_rules, "MAX_SAVED", 2)
    assert save(client, "a").status_code == 201
    assert save(client, "b").status_code == 201
    r = save(client, "c")
    assert r.status_code == 400 and "up to 2" in r.json()["detail"]


def test_rename_and_replace_a_rule(api):  # noqa: F811
    client, _ = api
    rid = save(client, "RSI dip").json()["id"]
    save(client, "Other")
    assert client.patch(f"/api/rules/{rid}", json={"name": "other"}, headers=AUTH).status_code == 409
    short = {**RULE, "direction": "short"}
    r = client.patch(f"/api/rules/{rid}", json={"name": "RSI pop", "rule": short}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["name"] == "RSI pop" and r.json()["rule"]["direction"] == "short"


def test_someone_elses_rule_reads_as_missing(api):  # noqa: F811
    client, state = api
    rid = save(client).json()["id"]
    state["uid"] = "intruder"
    assert client.get("/api/rules", headers=AUTH).json()["rules"] == []
    assert client.patch(f"/api/rules/{rid}", json={"name": "mine"}, headers=AUTH).status_code == 404
    assert client.delete(f"/api/rules/{rid}", headers=AUTH).status_code == 404
    state["uid"] = "u1"
    assert client.delete(f"/api/rules/{rid}", headers=AUTH).status_code == 204
    assert client.get("/api/rules", headers=AUTH).json()["rules"] == []


def test_rules_need_a_token(api):  # noqa: F811
    client, _ = api
    assert client.get("/api/rules").status_code == 401
