"""Plans and fair-use quotas.

Finertia is a free, non-commercial personal project (DECISIONS 24 Nov): the
price data is Yahoo Finance's, which may be used for personal, non-commercial
purposes only. So there is one public plan, free for everyone, and its limits
are fair-use limits that protect the shared server and the data source, not a
paywall. The second tier, "unlimited", is never sold: an admin can grant it
(to the author, or to someone testing), and it is not listed publicly.

Deliberately free of Stripe and Firebase imports so the rules can be tested
without credentials or a network.

Quotas are counted per calendar month in UTC. Storing a counter plus the month
it belongs to means checking a quota is a single document read rather than a
query over every run the user has ever made.
"""

from datetime import datetime, timezone

FREE = "free"
# Stored as "pro" on existing user documents; the id stays so they keep working.
PRO = "pro"

PLANS = {
    FREE: {
        "label": "Free",
        "price_monthly": 0,
        "monthly_runs": 100,
        "max_portfolio_size": 10,
        # Walk-forward and the permutation test each cost hundreds of backtests,
        # so they have their own monthly fair-use allowance, a deployment
        # setting (FREE_VALIDATIONS_PER_MONTH in api/core.py).
        "validation": False,
        "features": [
            "100 backtests a month",
            "Walk-forward validation and permutation tests, within a monthly fair-use limit",
            "All three strategies, on US and Indian stocks",
            "Stop-loss, take-profit, volatility sizing",
            "Portfolios up to 10 holdings",
            "Run comparison, CSV export and shareable links",
        ],
    },
    PRO: {
        "label": "Unlimited",
        # Never sold; granted by an admin only. See the module docstring.
        "price_monthly": 0,
        "monthly_runs": None,  # None means no cap
        "max_portfolio_size": 10,
        "validation": True,
        "features": [
            "No monthly limits (granted by an admin, not sold)",
        ],
    },
}

PLAN_NAMES = tuple(PLANS)
# The plans shown to the public: only the free one.
PUBLIC_PLAN_NAMES = (FREE,)


def normalise_plan(name: str | None) -> str:
    """Map a stored plan value onto a known plan.

    Anything unrecognised — a missing field on an old user document, or a plan
    that was retired — falls back to free. Failing open to Pro would hand out
    the paid tier on a typo.
    """
    if not name:
        return FREE
    cleaned = str(name).strip().lower()
    return cleaned if cleaned in PLANS else FREE


def plan_for(profile: dict | None) -> dict:
    """The plan definition for a user profile, with its name attached."""
    name = normalise_plan((profile or {}).get("plan"))
    return {"name": name, **PLANS[name]}


def current_period(now: datetime | None = None) -> str:
    """The quota bucket a run counts against, as 'YYYY-MM' in UTC.

    UTC rather than local time so a user travelling across a date line cannot
    reset their own quota, and so the boundary is the same for everyone.
    """
    now = now or datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def runs_used(profile: dict | None, now: datetime | None = None) -> int:
    """Runs already counted in the current period.

    A counter stamped with a previous month reads as zero rather than being
    reset by a write — nothing has to run at midnight on the first, and a user
    whose month rolled over while idle is simply back at zero on next read.
    """
    profile = profile or {}
    if profile.get("quotaPeriod") != current_period(now):
        return 0
    return int(profile.get("runsThisPeriod", 0) or 0)


def check_quota(profile: dict | None, now: datetime | None = None) -> dict:
    """Whether the user may start another run, and what is left.

    Returns {allowed, used, limit, remaining, plan}. `limit` and `remaining` are
    None on an uncapped plan.
    """
    plan = plan_for(profile)
    used = runs_used(profile, now)
    limit = plan["monthly_runs"]

    if limit is None:
        return {"allowed": True, "used": used, "limit": None, "remaining": None, "plan": plan["name"]}

    remaining = max(0, limit - used)
    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "plan": plan["name"],
    }


def may_validate(profile: dict | None) -> bool:
    """Whether this plan includes the overfitting checks without a cap."""
    return bool(plan_for(profile)["validation"])


def validations_used(profile: dict | None, now: datetime | None = None) -> int:
    """Free validations already taken in the current period.

    Same stale-period rule as `runs_used`. Clamped at zero: the counter is
    server-owned, but a negative value must never read as extra allowance.
    """
    profile = profile or {}
    if profile.get("validationPeriod") != current_period(now):
        return 0
    return max(0, int(profile.get("validationsThisPeriod", 0) or 0))


def check_validation_quota(
    profile: dict | None, free_allowance: int, now: datetime | None = None
) -> dict:
    """Whether the user may run a validation, and what is left of the free one.

    Pro validates without a cap. The free plan gets `free_allowance` a month,
    a deployment setting rather than a plan constant so it can stay at zero
    while a tester round is running and be switched on without a code change.

    Returns {allowed, used, limit, remaining, plan}; `limit` and `remaining`
    are None when uncapped.
    """
    plan = plan_for(profile)
    if plan["validation"]:
        return {"allowed": True, "used": 0, "limit": None, "remaining": None, "plan": plan["name"]}
    limit = max(0, int(free_allowance))
    used = validations_used(profile, now)
    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "plan": plan["name"],
    }


def max_portfolio_size(profile: dict | None) -> int:
    """Largest basket this plan may run."""
    return int(plan_for(profile)["max_portfolio_size"])


def public_plans() -> list[dict]:
    """The publicly listed plans (the free one only) for the limits page."""
    return [{"id": name, **PLANS[name]} for name in PUBLIC_PLAN_NAMES]
