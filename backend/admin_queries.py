"""The admin panel's reads, bounded so they cost the same at 10 users or 100k.

The first versions streamed every `users` and every `runs` document on each
page view and counted, filtered and paginated in Python. That was fine for a
handful of accounts and is linear in everything ever stored: each admin page
load was billed one read per document in both collections, and the response
time grew with them.

Now:
- Counts and averages are Firestore aggregation queries (`count()`, `avg()`),
  billed about one read per 1,000 index entries scanned instead of one per
  document, and returning one number rather than the documents.
- Lists page in the database (`offset` + `limit`) rather than in memory.
- The one thing an aggregation cannot do — group by ticker — reads a fixed
  window of the most recent runs, projected to the `ticker` field.

Every query here is covered by an automatic single-field index or by an entry
in firestore.indexes.json. tests/test_admin_queries_firestore.py runs them
against the emulator.
"""

from datetime import datetime, timedelta, timezone

from google.cloud.firestore_v1.base_query import FieldFilter

DESC = "DESCENDING"

# How many recent runs the "top tickers" list is computed over. A ranking over
# every run ever made would mean reading every run, which is what this module
# exists to stop.
TOP_TICKER_WINDOW = 500


def _aggregate(query, **aggs) -> dict:
    """Run count/avg aggregations in one request: _aggregate(q, n=("count",),
    sharpe=("avg", "metrics.sharpe_ratio"))."""
    agg = None
    for alias, (kind, *field) in aggs.items():
        target = agg or query
        agg = getattr(target, kind)(*field, alias=alias)
    results = agg.get()
    return {r.alias: r.value for r in results[0]}


def count(query) -> int:
    """How many documents match `query`, as one aggregation round trip."""
    return int(_aggregate(query, n=("count",))["n"] or 0)


def platform_stats(db, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    users = db.collection("users")
    runs = db.collection("runs")

    # Runs with no metrics are left out of the averages (avg() skips a missing
    # field); the old loop counted them as zero and dragged the mean down.
    #
    # The count is a separate request on purpose. In one aggregation query
    # Firestore only considers documents that have EVERY field being averaged,
    # so a count alongside avg() silently drops runs without metrics.
    totals = _aggregate(
        runs,
        sharpe=("avg", "metrics.sharpe_ratio"),
        ret=("avg", "metrics.total_return"),
    )
    total_runs = count(runs)

    recent = (
        runs.order_by("createdAt", direction=DESC).limit(TOP_TICKER_WINDOW).select(["ticker"]).stream()
    )
    ticker_counts: dict[str, int] = {}
    window = 0
    for snap in recent:
        window += 1
        t = (snap.to_dict() or {}).get("ticker") or ""
        if t:
            ticker_counts[t] = ticker_counts.get(t, 0) + 1
    top = sorted(ticker_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    return {
        "total_users": count(users),
        "total_runs": total_runs,
        "runs_today": count(runs.where(filter=FieldFilter("createdAt", ">=", today_start))),
        "runs_this_week": count(runs.where(filter=FieldFilter("createdAt", ">=", week_start))),
        "top_tickers": [{"ticker": t, "count": c} for t, c in top],
        "top_tickers_window": window,
        "avg_sharpe": round(totals["sharpe"], 4) if totals["sharpe"] is not None else 0.0,
        "avg_total_return": round(totals["ret"], 4) if totals["ret"] is not None else 0.0,
    }


def list_users(db, limit: int, offset: int, search: str | None = None) -> dict:
    """Newest first, or, with `search`, emails starting with it.

    Prefix rather than substring: Firestore has no "contains" on strings, and a
    substring search would mean reading every user again. Firebase stores
    emails lower-cased, so the term is too.
    """
    users = db.collection("users")
    if search:
        term = search.strip().lower()
        query = (
            users.where(filter=FieldFilter("email", ">=", term))
            .where(filter=FieldFilter("email", "<", term + ""))
            .order_by("email")
        )
    else:
        query = users.order_by("createdAt", direction=DESC)

    total = count(query)
    page = [d.to_dict() for d in query.offset(offset).limit(limit).stream()]
    return {"users": page, "total": total}


def list_runs(db, limit: int, offset: int, uid: str | None = None, ticker: str | None = None) -> dict:
    """Newest first, optionally for one user and/or one ticker.

    The filtered orderings need the composite indexes in firestore.indexes.json.
    """
    query = db.collection("runs")
    if uid:
        query = query.where(filter=FieldFilter("uid", "==", uid))
    if ticker:
        query = query.where(filter=FieldFilter("ticker", "==", ticker.upper()))

    # Counted without the ordering: equality filters alone are served by the
    # automatic single-field indexes.
    total = count(query)
    ordered = query.order_by("createdAt", direction=DESC)
    page = [d.to_dict() for d in ordered.offset(offset).limit(limit).stream()]
    return {"runs": page, "total": total}
