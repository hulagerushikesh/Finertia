"""The API is served twice: /api/v1 (the documented contract) and /api (the
original paths, for the current front end and links already shared).

FastAPI keeps an included router as one lazy entry in app.routes, so the
routes are read from the routers themselves (main.ROUTERS) and checked by
sending real requests.
"""

import os
import re

os.environ.setdefault("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")

from fastapi.routing import APIRoute  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import core  # noqa: E402
import main  # noqa: E402

UNROUTED = {"detail": "Not Found"}  # Starlette's own 404, before any handler


def _routes():
    return [r for m in main.ROUTERS for r in m.router.routes if isinstance(r, APIRoute)]


def test_every_route_answers_under_both_prefixes():
    client = TestClient(main.app, raise_server_exceptions=False)
    routes = _routes()
    assert len(routes) >= 20
    for route in routes:
        path = re.sub(r"\{[^}]+\}", "x", route.path)
        for method in route.methods:
            for prefix in ("/api", "/api/v1"):
                core.ip_limiter._hits.clear()
                r = client.request(method, prefix + path)
                unrouted = r.status_code == 404 and r.json() == UNROUTED
                assert not unrouted, f"{method} {prefix}{path} is not mounted"


def test_schema_documents_only_v1():
    paths = main.app.openapi()["paths"]
    assert len(paths) >= 20
    assert all(p.startswith("/api/v1/") for p in paths)


def test_health_answers_on_both():
    client = TestClient(main.app)
    for path in ("/api/health", "/api/v1/health"):
        r = client.get(path)
        assert r.status_code == 200 and r.json()["status"] == "ok"
