"""End-to-end tests for the HTTP layer.

Every other test file exercises a pure function. This one exercises the part
that decides who is allowed to call it: token handling, suspension, admin
gating, quota and entitlement enforcement, rate limiting, and how failures are
turned into status codes.

Nothing here touches Firebase or the network. `verify_token`, the profile
lookup, the Firestore client, and the price fetch are all replaced, so the
suite runs in CI with no credentials — the same rule the rest of the tests
follow.
"""

import os

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# main refuses to import without this, by design — a server that starts without
# credentials and fails on the first request is worse than one that will not
# start. A placeholder satisfies the guard; the SDK is never initialised because
# every function that would touch it is replaced below.
os.environ.setdefault("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")

import main  # noqa: E402


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _prices(days: int = 600, start: str = "2020-01-01") -> pd.DataFrame:
    """A deterministic upward-drifting series, long enough to clear warm-up."""
    idx = pd.bdate_range(start=start, periods=days)
    steps = np.sin(np.arange(days) / 9.0) * 0.9 + 0.12
    close = 100 + np.cumsum(steps)
    return pd.DataFrame({"Close": close, "Open": close, "High": close * 1.01,
                         "Low": close * 0.99, "Volume": 1_000_000}, index=idx)


class FakeDoc:
    def __init__(self, store, path):
        self._store, self._path = store, path

    def get(self):
        doc = self

        class Snap:
            exists = doc._path in doc._store

            @staticmethod
            def to_dict():
                return dict(doc._store.get(doc._path, {}))
        return Snap()

    def set(self, data, merge=False):
        if merge:
            self._store.setdefault(self._path, {}).update(data)
        else:
            self._store[self._path] = dict(data)

    def update(self, data):
        # Increment sentinels are objects, not numbers. Recording the call is
        # enough — what matters to these tests is that a write was attempted.
        self._store.setdefault(self._path, {}).update(
            {k: v for k, v in data.items() if not hasattr(v, "value")}
        )


class FakeCollection:
    def __init__(self, store, name):
        self._store, self._name = store, name

    def document(self, doc_id):
        return FakeDoc(self._store, f"{self._name}/{doc_id}")

    def add(self, data):
        key = f"{self._name}/generated-{len(self._store)}"
        self._store[key] = dict(data)
        return (None, FakeDoc(self._store, key))

    # History and admin listing chain these; returning self keeps the chain
    # valid and `stream()` yields nothing, which the routes handle.
    def where(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def offset(self, *a, **k):
        return self

    def stream(self):
        return iter(())


class FakeDb:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        return FakeCollection(self.store, name)


FREE = {"role": "user", "isActive": True, "totalRuns": 0}
PRO = {"role": "user", "isActive": True, "plan": "pro", "totalRuns": 0}
ADMIN = {"role": "admin", "isActive": True, "totalRuns": 0}
SUSPENDED = {"role": "user", "isActive": False}


@pytest.fixture
def api(monkeypatch):
    """A TestClient whose auth, database, and market data are all fakes.

    Returns (client, state) where state["profile"] can be reassigned per test
    to change who is calling.
    """
    state = {"profile": dict(FREE), "uid": "u1"}

    monkeypatch.setattr(
        main, "verify_token",
        lambda token: {"uid": state["uid"], "email": f"{state['uid']}@example.com"},
    )
    monkeypatch.setattr(main, "get_user_profile", lambda uid: state["profile"])
    monkeypatch.setattr(main, "get_db", lambda: FakeDb())
    monkeypatch.setattr(main, "fetch_ohlcv", lambda t, s, e: _prices())

    # Module-level singletons persist across tests in the same process, so one
    # test's traffic would otherwise spend another's budget. reset() drops a
    # single key by design; clearing every key is a test-only need, so it reaches
    # past the public API rather than widening it for one caller.
    for limiter in (main.ip_limiter, main.backtest_limiter, main.validate_limiter):
        limiter._hits.clear()

    # raise_server_exceptions=False makes the client behave like a real one:
    # an unhandled error comes back as the 500 the exception handler produces,
    # instead of being re-raised into the test. Without it the global handler —
    # the thing that decides what a user sees when something breaks — cannot be
    # tested at all.
    return TestClient(main.app, raise_server_exceptions=False), state


AUTH = {"Authorization": "Bearer fake-token"}
BACKTEST = {"ticker": "AAPL", "start": "2020-01-01", "end": "2022-01-01",
            "strategy": "momentum"}


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------


def test_health_needs_no_auth(api):
    client, _ = api
    assert client.get("/api/health").json() == {"status": "ok"}


def test_plans_and_strategies_are_public(api):
    client, _ = api
    assert client.get("/api/plans").status_code == 200
    assert client.get("/api/strategies").status_code == 200


def test_every_response_carries_a_request_id(api):
    """The id is what ties a user's error report to a line in the logs."""
    client, _ = api
    assert client.get("/api/health").headers.get("X-Request-Id")


def test_a_supplied_request_id_is_preserved(api):
    client, _ = api
    r = client.get("/api/health", headers={"X-Request-Id": "trace-me"})
    assert r.headers["X-Request-Id"] == "trace-me"


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "fake-token"},       # no scheme
    {"Authorization": "Basic fake-token"},  # wrong scheme
])
def test_backtest_rejects_missing_or_malformed_tokens(api, headers):
    client, _ = api
    assert client.post("/api/backtest", json=BACKTEST, headers=headers).status_code == 401


def test_suspended_accounts_are_refused(api):
    """403 at the auth dependency, so no route needs its own check."""
    client, state = api
    state["profile"] = dict(SUSPENDED)
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 403
    assert "suspended" in r.json()["detail"].lower()


def test_suspension_closes_every_authenticated_route(api):
    client, state = api
    state["profile"] = dict(SUSPENDED)
    for method, path in [("get", "/api/me/usage"), ("get", "/api/history"),
                         ("post", "/api/backtest")]:
        r = getattr(client, method)(path, headers=AUTH, **({"json": BACKTEST} if method == "post" else {}))
        assert r.status_code == 403, path


# ---------------------------------------------------------------------------
# Admin gating — the frontend AdminRoute is a convenience, this is the control
# ---------------------------------------------------------------------------


def test_admin_routes_reject_a_normal_user(api):
    client, _ = api
    r = client.get("/api/admin/stats", headers=AUTH)
    assert r.status_code == 403
    assert "admin" in r.json()["detail"].lower()


def test_admin_routes_accept_an_admin(api):
    client, state = api
    state["profile"] = dict(ADMIN)
    assert client.get("/api/admin/stats", headers=AUTH).status_code == 200


def test_role_comes_from_the_profile_not_the_token(api, monkeypatch):
    """A forged role claim inside the token must not grant admin.

    The role is read from the Firestore profile — the document the security
    rules now protect — so a token claiming admin gets nowhere.
    """
    client, state = api
    state["profile"] = dict(FREE)
    monkeypatch.setattr(
        main, "verify_token",
        lambda token: {"uid": "u1", "email": "u1@example.com", "role": "admin"},
    )
    assert client.get("/api/admin/stats", headers=AUTH).status_code == 403


# ---------------------------------------------------------------------------
# Quota and entitlement — 402, deliberately distinct from the limiter's 429
# ---------------------------------------------------------------------------


def test_free_plan_over_quota_gets_402(api):
    client, state = api
    state["profile"] = {**FREE, "runsThisPeriod": 10_000,
                        "quotaPeriod": main.current_period()}
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 402
    assert "upgrade" in r.json()["detail"].lower()


def test_a_stale_quota_period_reads_as_zero(api):
    """No midnight job resets counters; a previous month's stamp is ignored."""
    client, state = api
    state["profile"] = {**FREE, "runsThisPeriod": 10_000, "quotaPeriod": "1999-01"}
    assert client.post("/api/backtest", json=BACKTEST, headers=AUTH).status_code == 200


def test_validation_is_refused_on_the_free_plan(api):
    client, _ = api
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 402
    assert "pro" in r.json()["detail"].lower()


def test_validation_is_allowed_on_pro(api):
    client, state = api
    state["profile"] = dict(PRO)
    assert client.post("/api/validate", json=BACKTEST, headers=AUTH).status_code == 200


def test_pro_is_not_capped_by_the_free_quota(api):
    client, state = api
    state["profile"] = {**PRO, "runsThisPeriod": 10_000,
                        "quotaPeriod": main.current_period()}
    assert client.post("/api/backtest", json=BACKTEST, headers=AUTH).status_code == 200


# ---------------------------------------------------------------------------
# Rate limiting — 429, and it must not be confusable with 402
# ---------------------------------------------------------------------------


def test_backtest_burst_gets_429_with_retry_after(api):
    client, _ = api
    main.backtest_limiter._hits.clear()
    limit = main.backtest_limiter.limit

    for _ in range(limit):
        assert client.post("/api/backtest", json=BACKTEST, headers=AUTH).status_code == 200

    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) >= 1


def test_over_quota_and_over_rate_limit_are_different_codes(api):
    """The client shows "upgrade" for one and "wait" for the other, so a
    collision here would put the wrong message in front of a paying user."""
    client, state = api
    state["profile"] = {**FREE, "runsThisPeriod": 10_000,
                        "quotaPeriod": main.current_period()}
    quota = client.post("/api/backtest", json=BACKTEST, headers=AUTH)

    state["profile"] = dict(PRO)
    main.backtest_limiter._hits.clear()
    for _ in range(main.backtest_limiter.limit):
        client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    burst = client.post("/api/backtest", json=BACKTEST, headers=AUTH)

    assert (quota.status_code, burst.status_code) == (402, 429)


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


def test_unknown_ticker_becomes_400_not_500(api, monkeypatch):
    client, _ = api

    def boom(ticker, start, end):
        raise ValueError(f"No data found for {ticker}")
    monkeypatch.setattr(main, "fetch_ohlcv", boom)

    r = client.post("/api/backtest", json={**BACKTEST, "ticker": "NOPE"}, headers=AUTH)
    assert r.status_code == 400
    assert "NOPE" in r.json()["detail"]


def test_too_little_history_is_explained_not_just_rejected(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(main, "fetch_ohlcv", lambda t, s, e: _prices(days=20))
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 400
    assert "not enough history" in r.json()["detail"].lower()


def test_invalid_request_body_is_rejected_before_any_work(api, monkeypatch):
    client, _ = api

    def should_not_run(*a, **k):
        raise AssertionError("fetched data for a request that failed validation")
    monkeypatch.setattr(main, "fetch_ohlcv", should_not_run)

    r = client.post("/api/backtest", json={**BACKTEST, "start": "2025-01-01",
                                           "end": "2020-01-01"}, headers=AUTH)
    assert r.status_code == 422


def test_an_unexpected_error_returns_500_carrying_the_request_id(api, monkeypatch):
    """The generic body is deliberate; the id is what makes it diagnosable."""
    client, _ = api

    def explode(*a, **k):
        raise RuntimeError("something internal")
    monkeypatch.setattr(main, "fetch_ohlcv", explode)

    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 500
    assert "something internal" not in r.text
    assert r.headers.get("X-Request-Id")


# ---------------------------------------------------------------------------
# A successful run, so the failure tests above are not the only shape covered
# ---------------------------------------------------------------------------


def test_backtest_returns_metrics_and_a_curve(api):
    client, _ = api
    body = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    assert "metrics" in body and "equity_curve" in body
    assert body["metrics"]["total_return"] is not None


def test_usage_reports_the_plan_and_the_counter(api):
    client, _ = api
    body = client.get("/api/me/usage", headers=AUTH).json()
    assert body["plan"] == "free"
    assert "limit" in body and "used" in body
