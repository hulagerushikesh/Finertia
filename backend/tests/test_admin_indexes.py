"""Every multi-field aggregation in admin_queries has its composite index.

The emulator does not enforce indexes, so the emulator tests passed while
production answered the Overview's averages with FAILED_PRECONDITION ("The
query requires an index") from rev 00021 until 13 Oct. Firestore needs a
composite index for an aggregation over two or more fields; this test reads
firestore.indexes.json and fails if one is missing.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import admin_queries

INDEXES = json.loads((Path(__file__).resolve().parents[2] / "firestore.indexes.json").read_text())


def _composites():
    return {
        (ix["collectionGroup"], frozenset(f["fieldPath"] for f in ix["fields"]))
        for ix in INDEXES["indexes"]
    }


def test_every_multi_field_aggregation_is_indexed(monkeypatch):
    calls = []

    def fake_aggregate(query, **aggs):
        fields = frozenset(f for _, *rest in aggs.values() for f in rest)
        calls.append((query.collection_name, fields))
        return {alias: 0 for alias in aggs}

    def collection(name):
        q = MagicMock()
        q.collection_name = name
        q.where.return_value = q
        q.order_by.return_value.limit.return_value.select.return_value.stream.return_value = []
        return q

    db = MagicMock()
    db.collection.side_effect = collection
    monkeypatch.setattr(admin_queries, "_aggregate", fake_aggregate)

    admin_queries.platform_stats(db)

    multi = [(c, f) for c, f in calls if len(f) >= 2]
    assert multi, "platform_stats no longer averages two fields at once; drop this test or its index"
    missing = [c for c in multi if c not in _composites()]
    assert not missing, f"no composite index in firestore.indexes.json for {missing}"
