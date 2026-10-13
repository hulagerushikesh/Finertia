"""Sentry reporting: off by default, and what it sends is trimmed.

The end-to-end tests start the real SDK with a transport that records envelopes
instead of sending them, then drive the real app, so they check exactly what
would leave the server.
"""

import pytest

import monitoring
from monitoring import init_sentry, scrub


def test_off_without_a_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert init_sentry() is False


def test_off_against_the_emulators(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://k@o1.ingest.us.sentry.io/1")
    assert init_sentry(emulator=True) is False


def test_scrub_keeps_only_harmless_request_fields():
    event = {
        "request": {
            "url": "https://api/x/api/admin/users?search=a@b.com",
            "query_string": "search=a@b.com",
            "data": {"ticker": "AAPL"},
            "cookies": {"s": "1"},
            "env": {"REMOTE_ADDR": "1.2.3.4"},
            "headers": {"Authorization": "Bearer t", "Cookie": "s=1", "X-Request-Id": "r1",
                        "User-Agent": "ua", "X-Forwarded-For": "1.2.3.4"},
        },
        "user": {"id": "u1", "email": "a@b.com", "ip_address": "1.2.3.4"},
    }
    out = scrub(event)
    assert out["request"] == {"url": "https://api/x/api/admin/users",
                              "headers": {"X-Request-Id": "r1", "User-Agent": "ua"}}
    assert out["user"] == {"id": "u1"}


# ---------------------------------------------------------------------------
# End to end through the app
# ---------------------------------------------------------------------------

sentry_sdk = pytest.importorskip("sentry_sdk")
from sentry_sdk.transport import Transport  # noqa: E402


class Recorder(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.events = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.type == "event":
                self.events.append(item.payload.json)


@pytest.fixture
def api_admin(monkeypatch):
    import os

    os.environ.setdefault("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")
    import main
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "verify_token", lambda t: {"uid": "admin1", "email": "admin1@example.com"})
    monkeypatch.setattr(main, "get_user_profile", lambda uid: {"role": "admin", "isActive": True})
    main.ip_limiter._hits.clear()
    return TestClient(main.app, raise_server_exceptions=False)


@pytest.fixture
def reporting(monkeypatch):
    recorder = Recorder()
    monkeypatch.setenv("SENTRY_DSN", "https://k@o1.ingest.us.sentry.io/1")
    assert init_sentry(transport=recorder)
    yield recorder
    sentry_sdk.get_client().close()
    # init() with no dsn falls back to SENTRY_DSN, which is still set here —
    # that would switch reporting back on, over the network, for every later
    # test. Clear it first.
    monkeypatch.delenv("SENTRY_DSN")
    sentry_sdk.init()
    assert sentry_sdk.get_client().transport is None


def _flush():
    sentry_sdk.get_client().flush(timeout=2)


def test_an_unhandled_error_is_reported_with_id_and_trimmed(api_admin, reporting):
    client = api_admin
    r = client.post("/api/admin/sentry-test?probe=a@b.com", headers={
        "Authorization": "Bearer secret-token", "X-Request-Id": "req-777"})
    assert r.status_code == 500
    _flush()

    assert len(reporting.events) == 1
    ev = reporting.events[0]
    assert ev["exception"]["values"][-1]["type"] == "SentryTestError"
    assert ev["tags"]["request_id"] == "req-777"
    assert ev["user"] == {"id": "admin1"}
    sent = repr(ev)
    for leak in ("secret-token", "a@b.com", "admin1@example.com"):
        assert leak not in sent, leak
    # No local variables in frames.
    frames = ev["exception"]["values"][-1]["stacktrace"]["frames"]
    assert all("vars" not in f for f in frames)


def test_expected_errors_are_not_reported(api_admin, reporting):
    """4xx answers (402 upgrade, 429 wait, 403) are the product working."""
    client = api_admin
    assert client.get("/api/admin/stats", headers={"Authorization": "nope"}).status_code == 401
    _flush()
    assert reporting.events == []
