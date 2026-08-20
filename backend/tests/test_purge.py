"""Tests for the purge-and-embargo gap at the split boundary.

The gap is arithmetic, so it is easy to get quietly wrong in a direction nobody
notices: an off-by-one that lets one contaminated bar through still produces a
plausible Sharpe ratio. These pin the properties that make the gap mean what it
claims — the halves never touch, the gap is only ever surrendered to keep a half
measurable, and surrendering it is always visible in the result.
"""

import math

import pytest

from purge import (
    EMBARGO_PCT,
    MAX_GAP_BARS,
    MIN_GAP_BARS,
    MIN_HALF_BARS,
    purged_split,
)


class TestTheGapExists:
    def test_the_halves_never_touch(self):
        b = purged_split(1260, 882)
        assert b["is_end"] < b["oos_start"]
        assert b["oos_start"] - b["is_end"] == 2 * b["purge_bars"]

    def test_purge_and_embargo_are_the_same_length(self):
        """Both sides remove the same straddling trade, so an asymmetry would
        mean one side is still counting bars the other already claimed."""
        for n, split in ((1260, 882), (600, 420), (900, 450)):
            b = purged_split(n, split)
            assert b["purge_bars"] == b["embargo_bars"]

    def test_the_gap_is_centred_on_the_nominal_split(self):
        b = purged_split(1000, 700)
        assert 700 - b["is_end"] == b["oos_start"] - 700

    def test_no_bar_belongs_to_both_halves(self):
        b = purged_split(1260, 882)
        in_sample = set(range(0, b["is_end"]))
        out_of_sample = set(range(b["oos_start"], 1260))
        assert not (in_sample & out_of_sample)
        assert len(in_sample) + len(out_of_sample) == 1260 - 2 * b["purge_bars"]


class TestSizing:
    def test_base_case_is_one_percent_of_the_period(self):
        # 1260 bars -> 13, comfortably inside the floor and the cap.
        assert purged_split(1260, 882)["purge_bars"] == math.ceil(EMBARGO_PCT * 1260)

    def test_floor_applies_to_short_periods(self):
        """1% of a one-year request is three bars — shorter than these
        strategies hold a position, so it would not clear the straddle."""
        b = purged_split(252, 176)
        assert math.ceil(EMBARGO_PCT * 252) < MIN_GAP_BARS
        assert b["purge_bars"] == MIN_GAP_BARS

    def test_cap_applies_to_long_periods(self):
        """Past about a month the gap costs more out-of-sample data than the
        bias it removes."""
        b = purged_split(10_000, 7000)
        assert b["purge_bars"] == MAX_GAP_BARS

    def test_gap_never_shrinks_as_the_period_grows(self):
        gaps = [purged_split(n, int(n * 0.7))["purge_bars"] for n in (100, 300, 600, 1260, 5000)]
        assert gaps == sorted(gaps)


class TestGivingUpTheGap:
    def test_a_half_is_never_taken_below_the_floor(self):
        """Thirty bars is the minimum either side needs for its metrics to mean
        anything. The gap yields to that, not the other way round."""
        for n in range(100, 400, 7):
            split = int(n * 0.7)
            assert min(split, n - split) >= MIN_HALF_BARS, "premise: both halves start legal"
            b = purged_split(n, split)
            assert b["is_end"] >= MIN_HALF_BARS
            assert n - b["oos_start"] >= MIN_HALF_BARS

    def test_a_half_already_under_the_floor_is_not_shrunk_further(self):
        """`purged_split` cannot rescue a split that arrived too short — that is
        `walk_forward`'s length check. What it must not do is make it worse."""
        b = purged_split(70, 49)  # out-of-sample is only 21 bars before any gap
        assert b["purge_bars"] == 0
        assert b["is_end"] == 49 and b["oos_start"] == 49

    def test_a_shortened_gap_is_always_reported(self):
        b = purged_split(80, 56)
        assert b["purge_bars"] == 0
        assert b["shortened"] is True
        assert b["applied"] is False

    def test_a_full_gap_is_not_flagged_as_shortened(self):
        b = purged_split(1260, 882)
        assert b["shortened"] is False
        assert b["applied"] is True

    def test_the_limiting_side_is_whichever_has_less_room(self):
        """An extreme ratio leaves one half nearly empty; the gap has to be
        sized off that half, not the roomy one."""
        b = purged_split(200, 180)  # only 20 bars after the split
        assert b["purge_bars"] == 0  # already under the floor, nothing to spare
        assert b["is_end"] == 180


class TestRejections:
    @pytest.mark.parametrize("n,split", [(100, 0), (100, 100), (100, 150), (100, -3)])
    def test_a_split_outside_the_series_is_rejected(self, n, split):
        with pytest.raises(ValueError, match="split_at"):
            purged_split(n, split)

    def test_an_empty_series_is_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            purged_split(0, 0)
