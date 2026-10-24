"""The real API, in-process and offline from production.

Scripts that quote figures on the site (reproduce_writeup.py,
build_stock_pages.py) call the route handlers through FastAPI's TestClient, so
the numbers come from exactly the code production serves. Only auth, the
Firestore user and run documents and the rate limiters' shared store are
faked, and prices are a fresh yfinance download (PRICE_CACHE=off): nothing
here may read or write production Firestore.

Import this before anything imports `main`.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ["PRICE_CACHE"] = "off"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

PRO = {"role": "user", "isActive": True, "plan": "pro", "totalRuns": 0}


class _Doc:
    def get(self):
        return self

    exists = False

    def to_dict(self):
        return {}

    def set(self, *a, **k):
        pass

    def update(self, *a, **k):
        pass


class _Collection:
    def document(self, *a, **k):
        return _Doc()

    def add(self, *a, **k):
        return (None, _Doc())


class _Batch:
    """One write result per write, so ratelimit.FirestoreStore.hit can read its
    counters (always zero here) instead of falling back with a warning."""

    def __init__(self):
        self.n = 0

    def set(self, *a, **k):
        self.n += 1

    def update(self, *a, **k):
        self.n += 1

    def commit(self):
        zero = SimpleNamespace(transform_results=[SimpleNamespace(integer_value=0)])
        return [zero] * self.n


class _Db:
    def collection(self, *a, **k):
        return _Collection()

    # /api/backtest writes the run and the usage counters in one batch.
    def batch(self):
        return _Batch()


main.verify_token = lambda token: {"uid": "reproduce", "email": "reproduce@example.com"}
main.get_user_profile = lambda uid: PRO
main.get_db = lambda: _Db()


def offline_client() -> TestClient:
    return TestClient(main.app, raise_server_exceptions=True)


def post(client: TestClient, route: str, body: dict):
    """One authenticated call, with the rate limiters reset so a long script never trips them."""
    for limiter in (main.ip_limiter, main.backtest_limiter, main.validate_limiter):
        limiter._hits.clear()
    return client.post(route, json=body, headers={"Authorization": "Bearer x"})
