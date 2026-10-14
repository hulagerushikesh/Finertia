"""A user's run history, one page at a time.

The first version streamed every run the user had ever made, counted them
and sliced the page in Python: a user with 2,000 runs paid 2,000 document
reads and a multi-second wait on every visit to History. Now the page comes
from the database (`offset` + `limit`, projected to the fields the list
shows) and the total from a `count()` aggregation, billed about one read per
1,000 index entries. The two are independent round trips and go out
together.

`offset` still costs one read per skipped document, so deep pages are not
free; at 20 runs a page that only matters for someone paging far back.
Cursor pagination would remove it, at the price of an API change.

The page query uses the (uid, createdAt desc) index in
firestore.indexes.json; the count needs only the automatic one on uid.
tests/test_history_firestore.py runs both against the emulator.
"""

from google.cloud.firestore_v1.base_query import FieldFilter

from admin_queries import count

# What the History list shows. The full document (every metric, the
# confidence intervals) is fetched by run id when a run is opened.
FIELDS = [
    "runId", "ticker", "start", "end", "strategy", "params", "createdAt", "durationMs",
    "metrics.total_return", "metrics.sharpe_ratio", "metrics.max_drawdown",
]


def history_page(db, uid: str, limit: int, offset: int, run=lambda *calls: [c() for c in calls]) -> dict:
    """{runs, total} for `uid`, newest first. `run` executes the two queries;
    the API passes one that runs them at the same time."""
    mine = db.collection("runs").where(filter=FieldFilter("uid", "==", uid))
    page_query = mine.order_by("createdAt", direction="DESCENDING").offset(offset).limit(limit).select(FIELDS)

    docs, total = run(lambda: list(page_query.stream()), lambda: count(mine))

    runs = []
    for doc in docs:
        d = doc.to_dict()
        m = d.get("metrics", {}) or {}
        runs.append({
            "runId": d.get("runId"),
            "ticker": d.get("ticker"),
            "start": d.get("start"),
            "end": d.get("end"),
            # Runs created before the strategy selector existed have no field.
            "strategy": d.get("strategy", "momentum"),
            "params": d.get("params"),
            "metrics": {
                "total_return": m.get("total_return"),
                "sharpe_ratio": m.get("sharpe_ratio"),
                "max_drawdown": m.get("max_drawdown"),
            },
            "createdAt": d.get("createdAt"),
            "durationMs": d.get("durationMs"),
        })
    return {"runs": runs, "total": total}
