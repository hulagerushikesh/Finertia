"""admin_queries against the Firestore emulator (aggregations need the real thing).

Skipped unless FIRESTORE_EMULATOR_HOST is set; CI runs it inside
`firebase emulators:exec` in the E2E job. Each test uses its own Firestore
database name so data from one never leaks into another's counts.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="needs the Firestore emulator"
)

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)  # a Wednesday


@pytest.fixture
def db():
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore

    # A fresh project id per test is a fresh, empty emulator namespace.
    return firestore.Client(project=f"demo-{uuid.uuid4().hex[:10]}", credentials=AnonymousCredentials())


def add_run(db, uid, ticker, created, sharpe=None, ret=None):
    doc = {"uid": uid, "ticker": ticker, "createdAt": created}
    if sharpe is not None:
        doc["metrics"] = {"sharpe_ratio": sharpe, "total_return": ret}
    db.collection("runs").add(doc)


def add_user(db, uid, email, created):
    db.collection("users").document(uid).set({"uid": uid, "email": email, "createdAt": created})


def test_stats_counts_averages_and_windows(db):
    from admin_queries import platform_stats

    add_user(db, "a", "a@x.com", NOW)
    add_user(db, "b", "b@x.com", NOW)
    add_run(db, "a", "AAPL", NOW - timedelta(hours=1), sharpe=1.0, ret=0.2)      # today
    add_run(db, "a", "AAPL", NOW - timedelta(days=1), sharpe=0.5, ret=0.1)       # Tue, this week
    add_run(db, "b", "MSFT", NOW - timedelta(days=10), sharpe=-0.5, ret=-0.1)    # older
    add_run(db, "b", "AAPL", NOW - timedelta(days=20))                            # no metrics

    s = platform_stats(db, now=NOW)
    assert s["total_users"] == 2
    assert s["total_runs"] == 4
    assert s["runs_today"] == 1
    assert s["runs_this_week"] == 2
    assert s["top_tickers"] == [{"ticker": "AAPL", "count": 3}, {"ticker": "MSFT", "count": 1}]
    assert s["top_tickers_window"] == 4
    # The run with no metrics is not averaged in as zeros.
    assert s["avg_sharpe"] == pytest.approx(1.0 / 3, abs=1e-4)
    assert s["avg_total_return"] == pytest.approx(0.2 / 3, abs=1e-4)


def test_stats_on_an_empty_project(db):
    from admin_queries import platform_stats

    s = platform_stats(db, now=NOW)
    assert (s["total_users"], s["total_runs"], s["avg_sharpe"], s["top_tickers"]) == (0, 0, 0.0, [])


def test_users_page_newest_first_with_total(db):
    from admin_queries import list_users

    for i in range(5):
        add_user(db, f"u{i}", f"u{i}@x.com", NOW - timedelta(days=i))
    out = list_users(db, limit=2, offset=1)
    assert out["total"] == 5
    assert [u["uid"] for u in out["users"]] == ["u1", "u2"]


def test_users_search_is_a_case_insensitive_prefix(db):
    from admin_queries import list_users

    add_user(db, "a", "rushi@x.com", NOW)
    add_user(db, "b", "rushikesh@y.com", NOW)
    add_user(db, "c", "ann@rushi.com", NOW)
    out = list_users(db, limit=50, offset=0, search="  RUSHI ")
    assert out["total"] == 2
    assert sorted(u["uid"] for u in out["users"]) == ["a", "b"]


def test_runs_filters_and_pages(db):
    from admin_queries import list_runs

    for i in range(4):
        add_run(db, "a", "AAPL", NOW - timedelta(hours=i))
    add_run(db, "a", "MSFT", NOW)
    add_run(db, "b", "AAPL", NOW)

    assert list_runs(db, 50, 0)["total"] == 6
    by_user = list_runs(db, 50, 0, uid="a")
    assert by_user["total"] == 5
    both = list_runs(db, limit=2, offset=1, uid="a", ticker="aapl")
    assert both["total"] == 4
    assert [r["createdAt"] for r in both["runs"]] == [NOW - timedelta(hours=1), NOW - timedelta(hours=2)]
