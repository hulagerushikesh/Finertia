"""Plan entitlements and monthly quota accounting."""

from datetime import datetime, timezone

import pytest

from plans import (
    FREE,
    PRO,
    PLANS,
    normalise_plan,
    plan_for,
    current_period,
    runs_used,
    check_quota,
    may_validate,
    max_portfolio_size,
    public_plans,
)


def at(year, month, day=15):
    return datetime(year, month, day, tzinfo=timezone.utc)


def profile(plan=FREE, used=0, period="2026-08"):
    return {"plan": plan, "runsThisPeriod": used, "quotaPeriod": period}


class TestNormalisePlan:
    @pytest.mark.parametrize("name", [FREE, PRO])
    def test_known_plans_pass_through(self, name):
        assert normalise_plan(name) == name

    def test_case_and_whitespace_are_normalised(self):
        assert normalise_plan("  PRO ") == PRO

    @pytest.mark.parametrize("bad", [None, "", "enterprise", "admin", "  "])
    def test_anything_unknown_falls_back_to_free(self, bad):
        # Failing open to Pro would hand out the paid tier on a typo or a
        # retired plan name.
        assert normalise_plan(bad) == FREE

    def test_a_profile_with_no_plan_field_is_free(self):
        assert plan_for({})["name"] == FREE

    def test_a_missing_profile_is_free(self):
        assert plan_for(None)["name"] == FREE


class TestPeriod:
    def test_period_is_year_and_month(self):
        assert current_period(at(2026, 8)) == "2026-08"

    def test_single_digit_months_are_padded(self):
        assert current_period(at(2026, 3)) == "2026-03"

    def test_december_and_january_are_different_buckets(self):
        assert current_period(at(2026, 12)) != current_period(at(2027, 1))


class TestRunsUsed:
    def test_counts_runs_stamped_with_the_current_period(self):
        assert runs_used(profile(used=7, period="2026-08"), at(2026, 8)) == 7

    def test_a_stale_period_reads_as_zero(self):
        # No midnight job has to run: last month's counter simply stops counting.
        assert runs_used(profile(used=40, period="2026-07"), at(2026, 8)) == 0

    def test_a_missing_counter_reads_as_zero(self):
        assert runs_used({"plan": FREE}, at(2026, 8)) == 0

    def test_a_null_counter_reads_as_zero(self):
        assert runs_used({"quotaPeriod": "2026-08", "runsThisPeriod": None}, at(2026, 8)) == 0


class TestQuota:
    def test_a_fresh_free_user_may_run(self):
        q = check_quota(profile(used=0), at(2026, 8))
        assert q["allowed"] and q["remaining"] == PLANS[FREE]["monthly_runs"]

    def test_remaining_counts_down(self):
        q = check_quota(profile(used=10), at(2026, 8))
        assert q["remaining"] == PLANS[FREE]["monthly_runs"] - 10

    def test_the_run_that_hits_the_limit_is_refused(self):
        limit = PLANS[FREE]["monthly_runs"]
        assert check_quota(profile(used=limit), at(2026, 8))["allowed"] is False

    def test_one_below_the_limit_is_allowed(self):
        limit = PLANS[FREE]["monthly_runs"]
        assert check_quota(profile(used=limit - 1), at(2026, 8))["allowed"] is True

    def test_remaining_never_goes_negative(self):
        # A plan downgrade can leave a counter above the new limit.
        q = check_quota(profile(used=999), at(2026, 8))
        assert q["remaining"] == 0

    def test_a_new_month_restores_the_full_quota(self):
        exhausted = profile(used=PLANS[FREE]["monthly_runs"], period="2026-07")
        assert check_quota(exhausted, at(2026, 8))["allowed"] is True

    def test_pro_is_uncapped(self):
        q = check_quota(profile(plan=PRO, used=100_000), at(2026, 8))
        assert q["allowed"] and q["limit"] is None and q["remaining"] is None

    def test_quota_reports_the_plan_it_applied(self):
        assert check_quota(profile(plan=PRO), at(2026, 8))["plan"] == PRO

    def test_an_unknown_plan_gets_the_free_quota(self):
        rogue = {"plan": "unlimited", "runsThisPeriod": 60, "quotaPeriod": "2026-08"}
        assert check_quota(rogue, at(2026, 8))["allowed"] is False


class TestEntitlements:
    def test_validation_is_a_paid_feature(self):
        assert may_validate(profile(plan=FREE)) is False
        assert may_validate(profile(plan=PRO)) is True

    def test_an_unknown_plan_does_not_unlock_validation(self):
        assert may_validate({"plan": "enterprise"}) is False

    def test_portfolio_size_differs_by_plan(self):
        assert max_portfolio_size(profile(plan=FREE)) < max_portfolio_size(profile(plan=PRO))

    def test_free_portfolio_cap_is_below_the_api_maximum(self):
        # The API allows 10; the free plan must be a real restriction.
        assert max_portfolio_size(profile(plan=FREE)) < 10


class TestPublicPlans:
    def test_every_plan_is_listed(self):
        assert {p["id"] for p in public_plans()} == set(PLANS)

    def test_each_carries_a_label_price_and_features(self):
        for p in public_plans():
            assert p["label"] and isinstance(p["price_monthly"], int)
            assert len(p["features"]) > 0

    def test_free_is_free_and_pro_is_not(self):
        prices = {p["id"]: p["price_monthly"] for p in public_plans()}
        assert prices[FREE] == 0 and prices[PRO] > 0
