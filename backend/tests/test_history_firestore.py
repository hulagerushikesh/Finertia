"""history.history_page against the Firestore emulator: the page query with
its projection, and the count aggregation.

Skipped unless FIRESTORE_EMULATOR_HOST is set; CI runs it inside
`firebase emulators:exec` in the E2E job.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="needs the Firestore emulator"
)

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


@pytest.fixture
def db():
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore

    return firestore.Client(project=f"demo-{uuid.uuid4().hex[:10]}", credentials=AnonymousCredentials())


def add_run(db, uid, i):
    db.collection("runs").document(f"{uid}-{i}").set({
        "runId": f"{uid}-{i}", "uid": uid, "ticker": "AAPL", "start": "2020-01-01",
        "end": "2021-01-01", "strategy": "momentum", "params": {"lookback": 20},
        "createdAt": T0 + timedelta(minutes=i), "durationMs": 100,
        "metrics": {"total_return": 0.1 * i, "sharpe_ratio": 1.0, "max_drawdown": -0.1, "cagr": 0.05},
    })


def test_a_page_newest_first_with_the_total(db):
    from history import history_page

    for i in range(7):
        add_run(db, "a", i)
    add_run(db, "b", 0)
    body = history_page(db, "a", limit=3, offset=2)
    assert body["total"] == 7
    assert [r["runId"] for r in body["runs"]] == ["a-4", "a-3", "a-2"]
    first = body["runs"][0]
    assert first["metrics"] == {"total_return": pytest.approx(0.4), "sharpe_ratio": 1.0, "max_drawdown": -0.1}
    assert first["params"] == {"lookback": 20} and first["strategy"] == "momentum"


def test_no_runs_is_an_empty_page(db):
    from history import history_page

    assert history_page(db, "nobody", limit=20, offset=0) == {"runs": [], "total": 0}
