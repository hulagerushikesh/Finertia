"""Subscription plans and usage quotas.

Deliberately free of Stripe and Firebase imports so the entitlement rules can be
tested without credentials or a network. Billing knows about plans; plans do not
know about billing.

Quotas are counted per calendar month in UTC. Storing a counter plus the month
it belongs to means checking a quota is a single document read rather than a
query over every run the user has ever made.
"""

from datetime import datetime, timezone

FREE = "free"
PRO = "pro"

PLANS = {
    FREE: {
        "label": "Free",
        "price_monthly": 0,
        "monthly_runs": 50,
        "max_portfolio_size": 3,
        # Walk-forward and the permutation test are the product's actual
        # differentiator, and each one costs hundreds of backtests in CPU.
        "validation": False,
        "features": [
            "50 backtests a month",
            "All three strategies",
            "Stop-loss, take-profit, volatility sizing",
            "Portfolios up to 3 holdings",
            "CSV export and shareable links",
        ],
    },
    PRO: {
        "label": "Pro",
        "price_monthly": 12,
        "monthly_runs": None,  # None means no cap
        "max_portfolio_size": 10,
        "validation": True,
        "features": [
            "Unlimited backtests",
            "Walk-forward validation and permutation tests",
            "Portfolios up to 10 holdings",
            "Run comparison",
            "Priority support",
        ],
    },
}

PLAN_NAMES = tuple(PLANS)


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
    """Whether this plan includes the overfitting checks."""
    return bool(plan_for(profile)["validation"])


def max_portfolio_size(profile: dict | None) -> int:
    """Largest basket this plan may run."""
    return int(plan_for(profile)["max_portfolio_size"])


def public_plans() -> list[dict]:
    """Plan definitions for the pricing page — no internal fields."""
    return [{"id": name, **PLANS[name]} for name in PLAN_NAMES]
