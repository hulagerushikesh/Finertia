"""Rate limiter tests.

Every test injects `now` rather than sleeping, so the whole file runs in
milliseconds and the clock is exact instead of approximate.
"""

import pytest

from ratelimit import RateLimiter


class TestConstruction:
    def test_rejects_zero_limit(self):
        with pytest.raises(ValueError, match="at least 1"):
            RateLimiter(limit=0, window_seconds=60)

    def test_rejects_negative_window(self):
        with pytest.raises(ValueError, match="positive"):
            RateLimiter(limit=5, window_seconds=-1)


class TestBasicBudget:
    def test_allows_up_to_the_limit(self):
        rl = RateLimiter(limit=3, window_seconds=60)
        assert [rl.check("a", now=t)["allowed"] for t in (0, 1, 2)] == [True, True, True]

    def test_blocks_the_one_past_the_limit(self):
        rl = RateLimiter(limit=3, window_seconds=60)
        for t in (0, 1, 2):
            rl.check("a", now=t)
        assert rl.check("a", now=3)["allowed"] is False

    def test_remaining_counts_down_to_zero(self):
        rl = RateLimiter(limit=3, window_seconds=60)
        assert [rl.check("a", now=t)["remaining"] for t in (0, 1, 2)] == [2, 1, 0]

    def test_keys_have_independent_budgets(self):
        rl = RateLimiter(limit=2, window_seconds=60)
        rl.check("a", now=0)
        rl.check("a", now=0)
        assert rl.check("a", now=0)["allowed"] is False
        assert rl.check("b", now=0)["allowed"] is True


class TestSlidingWindow:
    def test_slot_frees_when_the_oldest_hit_ages_out(self):
        rl = RateLimiter(limit=2, window_seconds=10)
        rl.check("a", now=0)
        rl.check("a", now=5)
        assert rl.check("a", now=9)["allowed"] is False
        # At t=11 the hit from t=0 is outside the 10s window.
        assert rl.check("a", now=11)["allowed"] is True

    def test_a_hit_exactly_at_the_window_edge_has_expired(self):
        rl = RateLimiter(limit=1, window_seconds=10)
        rl.check("a", now=0)
        assert rl.check("a", now=10)["allowed"] is True

    def test_window_is_not_a_fixed_bucket(self):
        # The failure this guards: with fixed buckets a caller fires `limit`
        # requests at the end of one bucket and `limit` more at the start of the
        # next, doubling the real rate.
        rl = RateLimiter(limit=3, window_seconds=60)
        for t in (58, 59, 60):
            assert rl.check("a", now=t)["allowed"] is True
        for t in (61, 62, 63):
            assert rl.check("a", now=t)["allowed"] is False

    def test_retry_after_points_at_the_oldest_hit_expiring(self):
        rl = RateLimiter(limit=1, window_seconds=60)
        rl.check("a", now=100)
        verdict = rl.check("a", now=130)
        assert verdict["retry_after"] == pytest.approx(30.0)

    def test_rejected_attempts_do_not_extend_the_lockout(self):
        # If a blocked attempt were recorded, a client polling every second
        # would keep pushing its own window forward and never recover.
        rl = RateLimiter(limit=1, window_seconds=10)
        rl.check("a", now=0)
        for t in range(1, 10):
            assert rl.check("a", now=t)["allowed"] is False
        assert rl.check("a", now=10)["allowed"] is True


class TestHousekeeping:
    def test_reset_clears_a_single_key(self):
        rl = RateLimiter(limit=1, window_seconds=60)
        rl.check("a", now=0)
        rl.check("b", now=0)
        rl.reset("a")
        assert rl.check("a", now=1)["allowed"] is True
        assert rl.check("b", now=1)["allowed"] is False

    def test_reset_on_an_unknown_key_is_a_no_op(self):
        rl = RateLimiter(limit=1, window_seconds=60)
        rl.reset("never-seen")  # must not raise

    def test_prune_drops_only_fully_expired_keys(self):
        rl = RateLimiter(limit=5, window_seconds=10)
        rl.check("old", now=0)
        rl.check("recent", now=8)
        assert rl.prune(now=12) == 1
        assert rl.tracked_keys == 1

    def test_prune_does_not_forget_a_key_still_inside_its_window(self):
        rl = RateLimiter(limit=1, window_seconds=10)
        rl.check("a", now=0)
        rl.prune(now=5)
        assert rl.check("a", now=6)["allowed"] is False

    def test_tracked_keys_grows_with_distinct_callers(self):
        rl = RateLimiter(limit=5, window_seconds=60)
        for i in range(7):
            rl.check(f"caller-{i}", now=0)
        assert rl.tracked_keys == 7


class TestRealClock:
    def test_defaults_to_wall_clock_when_now_is_omitted(self):
        rl = RateLimiter(limit=2, window_seconds=60)
        assert rl.check("a")["allowed"] is True
        assert rl.check("a")["allowed"] is True
        assert rl.check("a")["allowed"] is False
