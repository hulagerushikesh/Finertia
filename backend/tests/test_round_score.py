"""scripts/round_score.score: the Returned and "more than asked" columns."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from round_score import score  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")


def run(uid, when, ticker="AAPL", strategy="momentum", tickers=None):
    r = {"uid": uid, "createdAt": datetime.fromisoformat(when).replace(tzinfo=timezone.utc), "strategy": strategy}
    if tickers:
        r["tickers"] = tickers
    else:
        r["ticker"] = ticker
    return r


def one(runs):
    (row,) = score(runs, IST)
    return row


def test_one_run_is_neither_returned_nor_more():
    row = one([run("a", "2026-10-12T10:00")])
    assert row["runs"] == 1 and not row["returned"] and not row["more_than_asked"]


def test_a_second_ticker_or_rule_on_the_first_day_is_more_than_asked():
    assert one([run("a", "2026-10-12T10:00"), run("a", "2026-10-12T11:00", ticker="MSFT")])["more_than_asked"]
    assert one([run("a", "2026-10-12T10:00"), run("a", "2026-10-12T11:00", strategy="macd")])["more_than_asked"]
    assert one([run("a", "2026-10-12T10:00"), run("a", "2026-10-12T11:00", tickers=["AAPL", "MSFT"])])["more_than_asked"]


def test_the_same_run_twice_is_not_more_than_asked():
    assert not one([run("a", "2026-10-12T10:00"), run("a", "2026-10-12T10:05")])["more_than_asked"]


def test_returned_needs_a_later_day_within_seven():
    assert one([run("a", "2026-10-12T10:00"), run("a", "2026-10-19T10:00")])["returned"]
    assert not one([run("a", "2026-10-12T10:00"), run("a", "2026-10-20T10:00")])["returned"]


def test_days_are_read_in_the_testers_time_zone():
    # 20:00 and 21:00 UTC on the 12th are 01:30 and 02:30 IST on the 13th: one
    # day, so no return; 17:00 UTC (22:30 IST, the 12th) then 19:00 UTC
    # (00:30 IST, the 13th) is two days.
    assert not one([run("a", "2026-10-12T20:00"), run("a", "2026-10-12T21:00")])["returned"]
    assert one([run("a", "2026-10-12T17:00"), run("a", "2026-10-12T19:00")])["returned"]


def test_later_runs_do_not_count_toward_the_first_day():
    row = one([run("a", "2026-10-12T10:00"), run("a", "2026-10-14T10:00", ticker="MSFT")])
    assert not row["more_than_asked"] and row["runs_first_day"] == 1 and row["runs"] == 2


def test_rows_by_first_day_and_runs_without_a_uid_ignored():
    rows = score([run("b", "2026-10-13T10:00"), run("a", "2026-10-14T10:00"), {"createdAt": None}], IST)
    assert [r["uid"] for r in rows] == ["b", "a"]
