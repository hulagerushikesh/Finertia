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
from schemas import BacktestRequest  # noqa: E402


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
            id = doc._path.split("/", 1)[1]

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
        # Firestore refuses an update to a document that does not exist.
        if self._path not in self._store:
            raise RuntimeError(f"404 No document to update: {self._path}")
        # Increment sentinels are objects, not numbers. Recording the call is
        # enough — what matters to these tests is that a write was attempted.
        self._store[self._path].update(
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

    # The query surface the routes use, on the documents in this collection:
    # equality filters, one ordering, offset, limit, projection, count().
    def _query(self):
        return FakeQuery(self._store, self._name)

    def where(self, *a, **k):
        return self._query().where(*a, **k)

    def order_by(self, *a, **k):
        return self._query().order_by(*a, **k)

    def stream(self):
        return self._query().stream()


class FakeQuery:
    def __init__(self, store, name, filters=(), order=None, skip=0, take=None):
        self._store, self._name = store, name
        self._filters, self._order, self._skip, self._take = filters, order, skip, take

    def _with(self, **changes):
        q = FakeQuery(self._store, self._name, self._filters, self._order, self._skip, self._take)
        for key, value in changes.items():
            setattr(q, key, value)
        return q

    def where(self, field=None, op=None, value=None, *, filter=None):
        if filter is not None:
            field, op, value = filter.field_path, filter.op_string, filter.value
        assert op == "==", "only equality filters are faked"
        return self._with(_filters=self._filters + ((field, value),))

    def order_by(self, field, direction="ASCENDING"):
        return self._with(_order=(field, direction))

    def offset(self, n):
        return self._with(_skip=n)

    def limit(self, n):
        return self._with(_take=n)

    def select(self, fields):
        return self

    def _matching(self):
        prefix = f"{self._name}/"
        rows = [(k, v) for k, v in self._store.items() if k.startswith(prefix)]
        rows = [(k, v) for k, v in rows if all(v.get(f) == val for f, val in self._filters)]
        if self._order:
            field, direction = self._order
            rows.sort(key=lambda kv: kv[1].get(field) or 0, reverse=direction == "DESCENDING")
        return rows

    def stream(self):
        rows = self._matching()[self._skip:]
        if self._take is not None:
            rows = rows[: self._take]
        return iter([FakeDoc(self._store, k).get() for k, _ in rows])

    def count(self, alias=None):
        n = len(self._matching())

        class Agg:
            @staticmethod
            def get():
                class R:
                    pass
                r = R()
                r.alias, r.value = alias, n
                return [[r]]
        return Agg()


class FakeBatch:
    """Writes applied on commit, which is counted: one commit is one trip."""

    def __init__(self, db):
        self._db, self._ops = db, []

    def set(self, ref, data, merge=False):
        self._ops.append((ref, data, merge))

    def commit(self):
        self._db.commits += 1
        for ref, data, merge in self._ops:
            ref.set({k: v for k, v in data.items() if not hasattr(v, "value")}, merge=merge)


class FakeDb:
    def __init__(self):
        self.store = {}
        self.commits = 0
        self.get_all_calls = 0

    def collection(self, name):
        return FakeCollection(self.store, name)

    def batch(self):
        return FakeBatch(self)

    def get_all(self, refs):
        self.get_all_calls += 1
        return [ref.get() for ref in refs]


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
    # One database per test, so a test can look at what a route wrote.
    db = FakeDb()
    state["db"] = db
    monkeypatch.setattr(main, "get_db", lambda: db)
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
    assert client.get("/api/health").json() == {"status": "ok", "commit": None, "revision": None}


def test_health_names_the_deployed_commit_and_revision(api, monkeypatch):
    """The release checklist reads these to prove what production is serving."""
    client, _ = api
    monkeypatch.setenv("GIT_SHA", "b1fc3ff0123456789abcdef0123456789abcdef0")
    monkeypatch.setenv("K_REVISION", "finertia-api-00021-abc")
    body = client.get("/api/health").json()
    assert body["commit"] == "b1fc3ff0123456789abcdef0123456789abcdef0"
    assert body["revision"] == "finertia-api-00021-abc"


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


def _server_timing(response) -> dict:
    """`Server-Timing` as {name: duration}."""
    out = {}
    for part in response.headers["Server-Timing"].split(", "):
        name, dur = part.split(";")[:2]
        out[name] = float(dur.removeprefix("dur="))
    return out


def test_a_backtest_says_where_its_time_went(api):
    """Every wait on the token check and the database is named, so a slow
    production request can be read rather than guessed at."""
    client, _ = api
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 200
    steps = _server_timing(r)
    for name in ("auth", "profile", "ratelimit", "run_write", "other", "total"):
        assert name in steps, name
    assert steps["total"] >= sum(v for k, v in steps.items() if k != "total") - 1


def test_the_request_log_carries_the_step_timings(api, caplog):
    client, _ = api
    with caplog.at_level("INFO", logger="finertia"):
        client.get("/api/history", headers=AUTH)
    line = next(r for r in caplog.records if r.getMessage() == "request")
    assert set(line.timings_ms) >= {"auth", "profile", "history_read"}
    assert line.instance_request >= 1


def test_public_routes_still_get_a_total(api):
    client, _ = api
    assert "total" in _server_timing(client.get("/api/health"))


# Routes allowed to stay `async def`: they never block. Anything else that is
# async runs its Firestore and engine calls on the event loop and stalls every
# other request on the instance while it waits.
_ASYNC_ROUTES = {"health", "list_plans", "list_strategies", "stripe_webhook"}


def test_blocking_routes_run_in_worker_threads():
    import inspect
    from fastapi.routing import APIRoute

    async_routes = {
        r.endpoint.__name__
        for r in main.app.routes
        if isinstance(r, APIRoute) and inspect.iscoroutinefunction(r.endpoint)
    }
    assert async_routes <= _ASYNC_ROUTES, async_routes - _ASYNC_ROUTES


def test_a_slow_backtest_does_not_hold_up_other_requests(api, monkeypatch):
    """Two backtests that each wait 1 s on "the database", then a health
    check sent while they wait. Served one at a time, the health check waits
    for both and the pair takes over 2 s. In worker threads the waits overlap."""
    import asyncio
    import time as _time

    import httpx

    def slow_prices(t, s, e):
        _time.sleep(1.0)  # a blocking wait, like a Firestore round trip
        return _prices()

    monkeypatch.setattr(main, "fetch_ohlcv", slow_prices)

    async def scenario():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            started = _time.perf_counter()

            async def backtest():
                r = await c.post("/api/backtest", json=BACKTEST, headers=AUTH)
                return r, _time.perf_counter() - started

            async def health():
                await asyncio.sleep(0.3)  # both backtests are now waiting
                r = await c.get("/api/health")
                return r, _time.perf_counter() - started

            return await asyncio.gather(backtest(), backtest(), health())

    (b1, t1), (b2, t2), (h, th) = asyncio.run(scenario())
    assert b1.status_code == b2.status_code == h.status_code == 200
    # Sent at 0.3 s; measured from the start, since a blocked event loop would
    # not even get to send it until the backtests finished.
    assert th < 0.8, f"health answered at {th:.2f}s, behind the backtests"
    assert max(t1, t2) < 1.8, f"backtests took {max(t1, t2):.2f}s; they ran one after the other"


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


def test_admin_routes_accept_an_admin(api, monkeypatch):
    # The queries themselves need real Firestore aggregations; they are tested
    # against the emulator in test_admin_queries_firestore.py. This is the gate.
    client, state = api
    state["profile"] = dict(ADMIN)
    monkeypatch.setattr(main, "platform_stats", lambda db: {"total_users": 0})
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


@pytest.fixture
def admin_db(api, monkeypatch):
    """The api fixture with one shared fake database holding a target user.

    The default fixture builds a fresh FakeDb on every get_db() call, which is
    right for routes that only write; a patch reads back what it wrote.
    """
    client, state = api
    state["profile"] = dict(ADMIN)
    db = FakeDb()
    db.store["users/t1"] = {"uid": "t1", "email": "t@example.com", **FREE}
    monkeypatch.setattr(main, "get_db", lambda: db)
    return client, state, db


def test_admin_can_grant_and_remove_pro(admin_db):
    client, _, db = admin_db
    r = client.patch("/api/admin/users/t1", json={"plan": "pro"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["plan"] == "pro"
    # Stamped, so a comped account is never counted as a paying one.
    assert db.store["users/t1"]["planSource"] == "admin"

    r = client.patch("/api/admin/users/t1", json={"plan": "free"}, headers=AUTH)
    assert r.status_code == 200
    assert db.store["users/t1"]["plan"] == "free"


def test_admin_plan_must_be_a_real_plan(admin_db):
    client, _, db = admin_db
    r = client.patch("/api/admin/users/t1", json={"plan": "enterprise"}, headers=AUTH)
    assert r.status_code == 400
    assert "plan" not in db.store["users/t1"]


def test_a_user_cannot_grant_themselves_pro(admin_db):
    client, state, db = admin_db
    state["profile"] = dict(FREE)
    r = client.patch("/api/admin/users/t1", json={"plan": "pro"}, headers=AUTH)
    assert r.status_code == 403
    assert "plan" not in db.store["users/t1"]


def test_admin_plan_patch_on_a_missing_user_is_404(admin_db):
    client, _, _ = admin_db
    r = client.patch("/api/admin/users/nobody", json={"plan": "pro"}, headers=AUTH)
    assert r.status_code == 404


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


def test_backtest_carries_the_regime_breakdown(api):
    client, _ = api
    body = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    regimes = body["regimes"]
    assert regimes["computable"]
    assert set(regimes["regimes"]) == {"low", "mid", "high"}
    assert regimes["best_regime"] in regimes["regimes"]
    # And the second axis beside it: which way the market was going, plus
    # the two labels crossed into a 3 x 3 grid.
    assert set(regimes["trend"]["regimes"]) == {"down", "flat", "up"}
    assert set(regimes["joint"]["cells"]) == {"low", "mid", "high"}
    assert set(regimes["joint"]["cells"]["low"]) == {"down", "flat", "up"}


def test_backtest_carries_the_sharpe_difference_test(api):
    """The p-value that belongs between the two Sharpe ratios on the page."""
    client, _ = api
    body = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    test = body["benchmark_test"]
    assert test["computable"]
    assert test["benchmark"] == "buy_and_hold"
    assert 0 < test["p_value"] <= 1
    assert test["difference"] == pytest.approx(
        test["strategy_sharpe"] - test["benchmark_sharpe"], abs=1e-3
    )
    # Not the headline Sharpe: that one is geometric, and the block says which
    # pair the p-value actually belongs to.
    assert "sqrt(252)" in test["sharpe_definition"]


def test_backtest_carries_the_cost_sensitivity_block(api):
    """How far the cost assumption can be wrong before the edge is gone."""
    client, _ = api
    body = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    block = body["cost_sensitivity"]
    # BACKTEST leaves transaction_cost off, so this is the schema default.
    assumed = BacktestRequest(**BACKTEST).transaction_cost
    assert block["assumed_cost"] == pytest.approx(assumed)
    assert block["status"] in {"measured", "unprofitable", "no_trades"}
    # The curve is priced in multiples of what the user asked for, so their own
    # assumption is always one of the points on it.
    costs = [p["cost"] for p in block["curve"]]
    assert costs == sorted(costs)
    assert any(c == pytest.approx(assumed) for c in costs)
    if block["status"] == "measured":
        assert block["headroom"] == pytest.approx(
            block["breakeven_cost"] / assumed, rel=1e-3
        )


def test_the_sharpe_test_is_stable_across_identical_runs(api):
    """Its seed comes from the request, so the same backtest returns the same
    p-value — a number that drifted every refresh would teach the reader it
    was arbitrary."""
    client, _ = api
    first = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    again = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    assert first["benchmark_test"] == again["benchmark_test"]


def test_validation_carries_the_rolling_walk_forward(api):
    client, state = api
    state["profile"] = dict(PRO)
    body = client.post("/api/validate", json=BACKTEST, headers=AUTH).json()
    rolling = body["rolling_walk_forward"]
    assert len(rolling["folds"]) == 4
    assert rolling["verdict"] in {"consistent", "regime_dependent", "failed"}
    # One verdict per fold, each with the market's own move beside it.
    assert all("benchmark_return" in f for f in rolling["folds"])
    # And the stitched out-of-sample record split by volatility regime,
    # with the trend label and the vol x trend grid beside it.
    stitched = rolling["out_of_sample_stitched"]["regimes"]
    assert "trend" in stitched and "joint" in stitched


def test_rolling_folds_is_a_request_knob(api):
    client, state = api
    state["profile"] = dict(PRO)
    body = client.post(
        "/api/validate", json={**BACKTEST, "rolling_folds": 2}, headers=AUTH
    ).json()
    assert body["rolling_walk_forward"]["n_folds"] == 2
    assert client.post(
        "/api/validate", json={**BACKTEST, "rolling_folds": 1}, headers=AUTH
    ).status_code == 422


def test_rolling_too_short_degrades_instead_of_failing_the_run(api, monkeypatch):
    """The single split fits in ~250 bars; eight folds do not. The rest of the
    validation response is still worth returning."""
    client, state = api
    state["profile"] = dict(PRO)
    monkeypatch.setattr(main, "fetch_ohlcv", lambda t, s, e: _prices(days=260))
    r = client.post("/api/validate", json={**BACKTEST, "rolling_folds": 8}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["walk_forward"]["verdict"]
    assert body["rolling_walk_forward"] == {
        "computable": False,
        "reason": body["rolling_walk_forward"]["reason"],
    }
    assert "fewer folds" in body["rolling_walk_forward"]["reason"]


PORTFOLIO = {"tickers": ["AAPL", "MSFT"], "start": "2020-01-01", "end": "2022-01-01",
             "strategy": "momentum"}


def test_portfolio_carries_the_cost_sensitivity_block(api):
    """The breakeven must survive a real re-run of the whole endpoint at it.

    Anything weaker only checks the solver against its own arithmetic. This
    posts the number back as `transaction_cost` and reads the Sharpe off the
    response the user would actually get.
    """
    client, state = api
    state["profile"] = dict(PRO)
    body = client.post("/api/portfolio", json=PORTFOLIO, headers=AUTH).json()
    block = body["cost_sensitivity"]
    assert block["status"] in {"measured", "unprofitable", "no_trades"}

    if block["status"] == "measured":
        again = client.post(
            "/api/portfolio",
            json={**PORTFOLIO, "transaction_cost": block["breakeven_cost"]},
            headers=AUTH,
        ).json()
        assert again["metrics"]["sharpe_ratio"] == pytest.approx(0.0, abs=1e-4)

    # And every point on the curve is a real run at that cost, not a rescale.
    for point in block["curve"]:
        rerun = client.post(
            "/api/portfolio", json={**PORTFOLIO, "transaction_cost": point["cost"]}, headers=AUTH
        ).json()
        assert rerun["metrics"]["sharpe_ratio"] == pytest.approx(
            point["sharpe_ratio"], abs=1e-6
        )


def test_portfolio_carries_the_sharpe_test_against_the_held_basket(api):
    client, state = api
    state["profile"] = dict(PRO)
    body = client.post("/api/portfolio", json=PORTFOLIO, headers=AUTH).json()
    test = body["benchmark_test"]
    assert test["computable"]
    assert test["bars"] == body["aligned_bars"]


def test_portfolio_validation_is_refused_on_the_free_plan(api):
    client, _ = api
    r = client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH)
    assert r.status_code == 402
    assert "pro" in r.json()["detail"].lower()


def test_portfolio_validation_carries_both_checks_for_the_book(api):
    client, state = api
    state["profile"] = dict(PRO)
    r = client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["tickers"] == ["AAPL", "MSFT"]
    assert body["weighting"] == "equal"
    wf = body["walk_forward"]
    assert wf["verdict"] in {"held_up", "weakened", "overfit", "failed", "inconclusive"}
    assert set(wf["legs"]) == {"AAPL", "MSFT"}
    assert wf["snooping"]["benchmark"] == "buy_and_hold_basket"
    # Same shape the single-ticker verdict card reads.
    for k in ("best_params", "best_out_of_sample", "deflated", "overfitting", "snooping"):
        assert k in wf
    pm = body["permutation"]
    assert pm["trials"] == 500
    assert set(pm["legs"]) == {"AAPL", "MSFT"}
    assert pm["null"].startswith("each leg")
    # Nothing was persisted: diagnostics do not count as runs in history.
    assert "rolling_walk_forward" not in body


def test_portfolio_validation_respects_the_plan_size_cap(api, monkeypatch):
    client, state = api
    state["profile"] = dict(PRO)
    monkeypatch.setattr(main, "max_portfolio_size", lambda profile: 1)
    r = client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH)
    assert r.status_code == 402
    assert "up to 1" in r.json()["detail"]


def test_portfolio_validation_shares_the_validate_rate_budget(api):
    client, state = api
    state["profile"] = dict(PRO)
    limit = main.validate_limiter.limit
    for _ in range(limit):
        assert client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH).status_code == 200
    assert client.post("/api/validate", json=BACKTEST, headers=AUTH).status_code == 429


def test_portfolio_validation_too_short_is_a_400(api, monkeypatch):
    client, state = api
    state["profile"] = dict(PRO)
    monkeypatch.setattr(main, "fetch_ohlcv", lambda t, s, e: _prices(days=40))
    r = client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH)
    assert r.status_code == 400


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


def test_backtest_carries_confidence_intervals(api):
    """The band has to arrive with the number it belongs to. If the route stops
    returning it the dashboard silently falls back to bare point estimates,
    which looks fine and is the thing this was built to stop."""
    client, _ = api
    body = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    ci = body["confidence_intervals"]
    assert ci["available"] is True
    band = ci["metrics"]["sharpe_ratio"]
    assert band["low"] <= band["point"] <= band["high"]
    assert band["point"] == body["metrics"]["sharpe_ratio"]


def test_confidence_intervals_are_not_a_paid_feature(api):
    """The free tier is the one most likely to read a Sharpe as a fact about the
    strategy, so it is the tier that most needs the interval. `api` signs in as
    a free user."""
    client, _ = api
    body = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    assert body["confidence_intervals"]["available"] is True


def test_the_same_backtest_returns_the_same_interval(api):
    """Seeded from the request, so a reload does not move the band."""
    client, _ = api
    first = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    second = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()
    assert first["confidence_intervals"]["metrics"] == second["confidence_intervals"]["metrics"]


def test_usage_reports_the_plan_and_the_counter(api):
    client, _ = api
    body = client.get("/api/me/usage", headers=AUTH).json()
    assert body["plan"] == "free"
    assert "limit" in body and "used" in body


# ---------------------------------------------------------------------------
# Account export and deletion (account.py runs against the emulator in
# test_account_firestore.py; these pin who may call it and how)
# ---------------------------------------------------------------------------


@pytest.fixture
def account_calls(api, monkeypatch):
    client, state = api
    calls = {"export": [], "delete": []}

    def fake_export(db, uid, email):
        calls["export"].append((uid, email))
        return {"exported_at": "2026-10-14T09:00:00+00:00", "account": {"uid": uid}, "runs": []}

    def fake_delete(db, uid, delete_auth_user):
        calls["delete"].append((uid, delete_auth_user))
        return {"runs": 3, "rate_limit_counters": 1}

    monkeypatch.setattr(main, "export_account", fake_export)
    monkeypatch.setattr(main, "delete_account", fake_delete)
    return client, state, calls


def _delete(client, body, headers=AUTH):
    return client.request("DELETE", "/api/me", json=body, headers=headers)


def test_export_needs_a_token(account_calls):
    client, _, calls = account_calls
    assert client.get("/api/me/export").status_code == 401
    assert calls["export"] == []


def test_export_is_the_callers_own_data_as_a_download(account_calls):
    client, _, calls = account_calls
    r = client.get("/api/me/export", headers=AUTH)
    assert r.status_code == 200
    assert calls["export"] == [("u1", "u1@example.com")]
    assert r.headers["content-disposition"] == 'attachment; filename="finertia-export-2026-10-14.json"'


def test_delete_needs_a_token(account_calls):
    client, _, calls = account_calls
    assert _delete(client, {"confirm": "u1@example.com"}, headers={}).status_code == 401
    assert calls["delete"] == []


def test_delete_needs_the_email_typed_back(account_calls):
    client, _, calls = account_calls
    assert _delete(client, {"confirm": "someone-else@example.com"}).status_code == 400
    assert _delete(client, {}).status_code == 422
    assert calls["delete"] == []


def test_delete_removes_the_callers_account_and_reports_counts(account_calls):
    client, _, calls = account_calls
    r = _delete(client, {"confirm": "  U1@Example.com "})
    assert r.status_code == 200
    assert r.json() == {"deleted": True, "runs": 3, "rate_limit_counters": 1}
    uid, deleter = calls["delete"][0]
    assert uid == "u1"
    assert deleter is main.delete_auth_user  # the real Auth deletion, not a no-op


def test_an_admin_cannot_delete_themselves(account_calls):
    client, state, calls = account_calls
    state["profile"] = dict(ADMIN)
    assert _delete(client, {"confirm": "u1@example.com"}).status_code == 409
    assert calls["delete"] == []


def test_a_paying_subscriber_must_cancel_first(account_calls):
    client, state, calls = account_calls
    state["profile"] = {**PRO, "planSource": "stripe"}
    assert _delete(client, {"confirm": "u1@example.com"}).status_code == 409
    assert calls["delete"] == []


def test_a_comped_pro_account_can_be_deleted(account_calls):
    client, state, calls = account_calls
    state["profile"] = {**PRO, "planSource": "admin"}
    assert _delete(client, {"confirm": "u1@example.com"}).status_code == 200
    assert len(calls["delete"]) == 1


def test_a_suspended_account_cannot_delete_through_the_api(account_calls):
    """Suspension is checked before anything else; support handles those."""
    client, state, calls = account_calls
    state["profile"] = dict(SUSPENDED)
    assert _delete(client, {"confirm": "u1@example.com"}).status_code == 403
    assert calls["delete"] == []


# ---------------------------------------------------------------------------
# The free plan's monthly validation (FREE_VALIDATIONS_PER_MONTH)
# ---------------------------------------------------------------------------


@pytest.fixture
def allowance(api, monkeypatch):
    """Switch the free validation on and record what the routes take and give
    back. The transaction itself is tested against the emulator in
    test_validation_allowance_firestore.py."""
    client, state = api
    calls = {"reserve": [], "release": [], "grant": True}

    def reserve(db, uid, limit, now=None):
        calls["reserve"].append((uid, limit))
        return {"period": main.current_period(), "used": 1} if calls["grant"] else None

    def release(db, uid, period):
        calls["release"].append((uid, period))

    monkeypatch.setattr(main, "FREE_VALIDATIONS_PER_MONTH", 1)
    monkeypatch.setattr(main.validation_allowance, "reserve", reserve)
    monkeypatch.setattr(main.validation_allowance, "release", release)
    return client, state, calls


def test_free_validation_is_off_by_default():
    """Off unless the deployment switches it on: testers keep the Pro wall."""
    assert main.FREE_VALIDATIONS_PER_MONTH == 0


def test_a_free_user_gets_one_validation_when_switched_on(allowance):
    client, _, calls = allowance
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["free_validations_remaining"] == 0
    assert calls["reserve"] == [("u1", 1)]
    assert calls["release"] == []


def test_a_used_free_validation_is_refused_without_taking_another(allowance):
    client, state, calls = allowance
    state["profile"] = {**FREE, "validationsThisPeriod": 1,
                        "validationPeriod": main.current_period()}
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 402
    assert "free validation" in r.json()["detail"]
    assert calls["reserve"] == []


def test_losing_the_race_for_the_last_slot_is_a_402(allowance):
    """The profile read said yes; the transaction, which is the real check,
    said no — a concurrent request took it first."""
    client, _, calls = allowance
    calls["grant"] = False
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 402
    assert "free validation" in r.json()["detail"]


def test_a_validation_that_fails_gives_the_slot_back(allowance, monkeypatch):
    client, _, calls = allowance

    def bad_ticker(t, s, e):
        raise ValueError("No data for ZZZZ")

    monkeypatch.setattr(main, "fetch_ohlcv", bad_ticker)
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 400
    assert calls["release"] == [("u1", main.current_period())]


def test_a_crash_mid_validation_gives_the_slot_back(allowance, monkeypatch):
    client, _, calls = allowance

    def boom(*a, **k):
        raise RuntimeError("engine fell over")

    monkeypatch.setattr(main, "walk_forward", boom)
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 500
    assert calls["release"] == [("u1", main.current_period())]


def test_pro_validates_without_touching_the_allowance(allowance):
    client, state, calls = allowance
    state["profile"] = dict(PRO)
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 200
    assert "free_validations_remaining" not in r.json()
    assert calls["reserve"] == []


def test_a_refusal_after_the_plan_check_costs_nothing(allowance):
    """Out of runs: refused with the run-quota 402, and the free validation
    is still there for next month's first run."""
    client, state, calls = allowance
    state["profile"] = {**FREE, "runsThisPeriod": 10_000, "quotaPeriod": main.current_period()}
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 402
    assert calls["reserve"] == []


def test_a_free_basket_validation_takes_the_slot(allowance, monkeypatch):
    client, _, calls = allowance
    monkeypatch.setattr(main, "fetch_ohlcv", lambda t, s, e: _prices(days=260))
    r = client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["free_validations_remaining"] == 0
    assert calls["reserve"] == [("u1", 1)]


def test_an_oversized_free_basket_is_refused_before_the_slot_is_taken(allowance, monkeypatch):
    client, _, calls = allowance
    monkeypatch.setattr(main, "max_portfolio_size", lambda profile: 1)
    r = client.post("/api/portfolio/validate", json=PORTFOLIO, headers=AUTH)
    assert r.status_code == 402
    assert calls["reserve"] == []


def test_usage_reports_the_free_validations(allowance):
    client, state, _ = allowance
    body = client.get("/api/me/usage", headers=AUTH).json()
    assert (body["validations_used"], body["validations_limit"], body["validations_remaining"]) == (0, 1, 1)
    state["profile"] = dict(PRO)
    body = client.get("/api/me/usage", headers=AUTH).json()
    assert (body["validations_limit"], body["validations_remaining"]) == (None, None)


# ---------------------------------------------------------------------------
# Database round trips (system design A3)
# ---------------------------------------------------------------------------


def test_a_backtest_saves_the_run_and_its_counters_in_one_commit(api):
    client, state = api
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 200
    db = state["db"]
    assert db.commits == 1
    assert f"runs/{r.json()['runId']}" in db.store
    assert db.store["users/u1"]["quotaPeriod"] == main.current_period()


def test_a_run_without_a_profile_document_still_succeeds(api):
    """Feedback #12: an update() on a missing users/{uid} failed after the run
    was saved. The counters are merged in, creating the document."""
    client, state = api
    state["profile"] = {}
    assert "users/u1" not in state["db"].store
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 200
    assert state["db"].store["users/u1"]["runsThisPeriod"] == 1


def test_a_portfolio_records_its_run_without_a_profile_document(api):
    client, state = api
    state["profile"] = {}
    assert client.post("/api/portfolio", json=PORTFOLIO, headers=AUTH).status_code == 200
    assert "users/u1" in state["db"].store


def test_a_portfolio_takes_its_rate_slots_all_at_once(api, monkeypatch):
    """Refused as a whole, it takes nothing: a single backtest still fits."""
    client, state = api
    state["profile"] = dict(PRO)
    monkeypatch.setattr(main.backtest_limiter, "limit", 3)
    four = {**PORTFOLIO, "tickers": ["AAPL", "MSFT", "GOOG", "AMZN"]}
    r = client.post("/api/portfolio", json=four, headers=AUTH)
    assert r.status_code == 429 and "portfolio legs" in r.json()["detail"]
    assert client.post("/api/backtest", json=BACKTEST, headers=AUTH).status_code == 200


def test_a_suspended_account_gets_403_even_when_rate_limited(api, monkeypatch):
    client, state = api
    monkeypatch.setattr(main.backtest_limiter, "limit", 1)
    client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    state["profile"] = dict(SUSPENDED)
    assert client.post("/api/backtest", json=BACKTEST, headers=AUTH).status_code == 403


def test_the_profile_and_rate_limit_are_read_at_the_same_time(api, monkeypatch):
    import time as _time

    client, state = api

    def slow_profile(uid):
        _time.sleep(0.5)
        return state["profile"]

    def slow_check(key, now=None, cost=1):
        _time.sleep(0.5)
        return {"allowed": True, "remaining": 1, "retry_after": 0.0}

    monkeypatch.setattr(main, "get_user_profile", slow_profile)
    monkeypatch.setattr(main.backtest_limiter, "check", slow_check)
    started = _time.perf_counter()
    r = client.post("/api/backtest", json=BACKTEST, headers=AUTH)
    assert r.status_code == 200
    steps = _server_timing(r)
    assert steps["profile"] >= 490 and steps["ratelimit"] >= 490
    # One after the other would be 1.0 s before any work.
    assert _time.perf_counter() - started < 0.85


def test_portfolio_legs_fetch_their_prices_together(api, monkeypatch):
    import time as _time

    client, state = api
    state["profile"] = dict(PRO)

    def slow_prices(t, s, e):
        _time.sleep(0.5)
        return _prices()

    monkeypatch.setattr(main, "fetch_ohlcv", slow_prices)
    three = {**PORTFOLIO, "tickers": ["AAPL", "MSFT", "GOOG"]}
    started = _time.perf_counter()
    assert client.post("/api/portfolio", json=three, headers=AUTH).status_code == 200
    assert _time.perf_counter() - started < 1.2  # serial: 1.5 s of waiting


def test_a_portfolio_reports_the_first_bad_ticker_in_the_users_order(api, monkeypatch):
    client, state = api
    state["profile"] = dict(PRO)

    def prices(t, s, e):
        if t in ("MSFT", "GOOG"):
            raise ValueError(f"No data found for {t}")
        return _prices()

    monkeypatch.setattr(main, "fetch_ohlcv", prices)
    three = {**PORTFOLIO, "tickers": ["AAPL", "MSFT", "GOOG"]}
    r = client.post("/api/portfolio", json=three, headers=AUTH)
    assert r.status_code == 400 and r.json()["detail"].startswith("MSFT:")


def test_compare_reads_every_run_in_one_trip(api):
    client, state = api
    ids = [client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()["runId"] for _ in range(2)]
    r = client.post("/api/compare", json={"run_ids": ids}, headers=AUTH)
    assert r.status_code == 200
    assert state["db"].get_all_calls == 1


def test_compare_a_missing_run_is_404(api):
    client, state = api
    run_id = client.post("/api/backtest", json=BACKTEST, headers=AUTH).json()["runId"]
    r = client.post("/api/compare", json={"run_ids": [run_id, "nope"]}, headers=AUTH)
    assert r.status_code == 404


def test_lock_contention_on_the_free_validation_is_a_409_not_a_500(allowance, monkeypatch):
    """Several validations from one account at once: the transaction can run
    out of retries. The losers are told to try again; nothing was taken."""
    client, _, calls = allowance

    def contended(db, uid, limit, now=None):
        raise main.validation_allowance.Contended(uid)

    monkeypatch.setattr(main.validation_allowance, "reserve", contended)
    r = client.post("/api/validate", json=BACKTEST, headers=AUTH)
    assert r.status_code == 409
    assert r.headers["Retry-After"] == "2"
    assert calls["release"] == []


# ---------------------------------------------------------------------------
# History by page (system design A4)
# ---------------------------------------------------------------------------


def _seed_runs(db, uid, n, start=0):
    for i in range(start, start + n):
        db.store[f"runs/{uid}-{i}"] = {
            "runId": f"{uid}-{i}", "uid": uid, "ticker": "AAPL", "createdAt": i,
            "metrics": {"total_return": 0.1, "sharpe_ratio": 1.0, "max_drawdown": -0.1, "cagr": 0.05},
        }


def test_history_returns_one_page_newest_first_and_the_full_total(api):
    client, state = api
    _seed_runs(state["db"], "u1", 25)
    _seed_runs(state["db"], "someone-else", 5)
    body = client.get("/api/history?limit=10&offset=10", headers=AUTH).json()
    assert body["total"] == 25
    assert [r["runId"] for r in body["runs"]] == [f"u1-{i}" for i in range(14, 4, -1)]
    # Only what the list shows.
    assert set(body["runs"][0]["metrics"]) == {"total_return", "sharpe_ratio", "max_drawdown"}


def test_history_past_the_end_is_an_empty_page(api):
    client, state = api
    _seed_runs(state["db"], "u1", 3)
    body = client.get("/api/history?limit=20&offset=20", headers=AUTH).json()
    assert body == {"runs": [], "total": 3}


def test_history_reads_the_page_not_every_run(api, monkeypatch):
    """The page and the count are two queries; nothing streams the whole
    collection any more."""
    import history

    client, state = api
    _seed_runs(state["db"], "u1", 50)
    streamed = []
    real_stream = FakeQuery.stream

    def counting_stream(self):
        docs = list(real_stream(self))
        streamed.append(len(docs))
        return iter(docs)

    monkeypatch.setattr(FakeQuery, "stream", counting_stream)
    client.get("/api/history?limit=20", headers=AUTH)
    assert streamed == [20]
