"""Settings that make one image serve as staging (planning/DATA.md)."""

import sys

from fastapi.testclient import TestClient

import firebase_admin_init


def test_the_firestore_database_comes_from_the_environment(monkeypatch):
    seen = {}
    monkeypatch.setattr(firebase_admin_init, "_get_app", lambda: None)
    monkeypatch.setattr(
        firebase_admin_init.firestore, "client", lambda **kw: seen.setdefault("kw", kw) or "db"
    )
    monkeypatch.setenv("FIRESTORE_DATABASE", "staging")
    firebase_admin_init.get_db()
    assert seen["kw"] == {"database_id": "staging"}

    seen.clear()
    monkeypatch.delenv("FIRESTORE_DATABASE")
    firebase_admin_init.get_db()
    assert seen["kw"] == {}  # production: the (default) database


def _fresh_app(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    for name in ("main", "api.core"):
        sys.modules.pop(name, None)
    import main  # noqa: PLC0415

    return main


def test_a_preview_origin_is_allowed_only_where_the_pattern_is_set(monkeypatch):
    preview = "https://finertia-abc123-hulagerushikeshs-projects.vercel.app"
    # The originals go back afterwards, so every other test keeps patching
    # the same `api.core` the routes read.
    saved = {name: sys.modules.get(name) for name in ("main", "api.core")}
    try:
        main = _fresh_app(
            monkeypatch,
            ALLOWED_ORIGINS="https://finertia.hulage.in",
            ALLOWED_ORIGIN_REGEX=r"https://finertia-[a-z0-9-]+-hulagerushikeshs-projects\.vercel\.app",
        )
        client = TestClient(main.app)
        ok = client.options("/api/health", headers={"Origin": preview, "Access-Control-Request-Method": "GET"})
        assert ok.headers.get("access-control-allow-origin") == preview
        other = client.options("/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in other.headers

        monkeypatch.delenv("ALLOWED_ORIGIN_REGEX")
        main = _fresh_app(monkeypatch)
        client = TestClient(main.app)
        no = client.options("/api/health", headers={"Origin": preview, "Access-Control-Request-Method": "GET"})
        assert "access-control-allow-origin" not in no.headers
    finally:
        # Put the modules the other tests imported back as they were.
        monkeypatch.delenv("ALLOWED_ORIGIN_REGEX", raising=False)
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod
        import api  # noqa: PLC0415

        if saved["api.core"] is not None:
            api.core = saved["api.core"]
