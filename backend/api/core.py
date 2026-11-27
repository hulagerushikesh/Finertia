"""Shared runtime for the API: configuration, rate limits, quotas, auth.

Everything a route needs that is not the route itself. The names in the
"seams" import below are looked up as `core.<name>` by the route modules, so a
test or an offline script that replaces one here replaces it everywhere.
"""

import contextvars
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from dotenv import load_dotenv
from fastapi import Header, HTTPException, Request
from firebase_admin import firestore

from logging_config import configure_logging
from plans import (
    check_quota,
    check_validation_quota,
    current_period,
)
import validation_allowance
from ratelimit import FirestoreCounterStore, RateLimiter, SharedRateLimiter
from firebase_admin_init import verify_token, get_user_profile, get_db, emulator_mode
from monitoring import set_user as sentry_set_user
from timing import step

# Seams. Not used in this module: the route modules call them as core.<name>,
# so a test or an offline script replaces each in one place. The other seams
# (get_db, verify_token, get_user_profile, current_period and the two settings
# below) are used here as well.
from account import delete_account, export_account  # noqa: F401
from admin_queries import platform_stats  # noqa: F401
from data import fetch_ohlcv  # noqa: F401
from firebase_admin_init import delete_auth_user  # noqa: F401
from plans import max_portfolio_size  # noqa: F401
from validation import walk_forward  # noqa: F401

# ---------------------------------------------------------------------------
# Startup configuration checks — fail loudly rather than at first request
# ---------------------------------------------------------------------------

# Local dev convenience: in production (Cloud Run) the env vars are already set
# and no .env file exists, so this is a no-op there.
#
# The end-to-end suite runs against the Firebase emulators and must not read a
# developer's .env: it would pull real keys into a test server, and it would
# make a run on a laptop differ from the same run on a CI runner, which has no
# .env. The emulators need no service account either.
EMULATOR = emulator_mode()
if not EMULATOR:
    load_dotenv()

REQUIRED_ENV_VARS = () if EMULATOR else ("FIREBASE_SERVICE_ACCOUNT_JSON",)

_missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
if _missing:
    raise RuntimeError(
        "Missing required environment variable(s): "
        + ", ".join(_missing)
        + ". Copy .env.example to backend/.env and fill in the values from the "
        "Firebase Console (Project Settings → Service accounts → Generate new "
        "private key)."
    )

log = configure_logging(os.environ.get("LOG_LEVEL", "INFO"))

_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5174")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]
# Staging only: Vercel preview builds get a new hostname per commit, so a
# fixed list cannot name them. Unset in production, where only the listed
# origins (and the same-origin /api rewrite) apply.
ALLOWED_ORIGIN_REGEX = os.environ.get("ALLOWED_ORIGIN_REGEX") or None

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------

# Two layers. The IP limit is the blunt one — it catches an unauthenticated
# flood before any Firebase token verification happens, which is itself a
# network call worth protecting. The compute limits are per user, because a
# backtest fetches market data and a validation run sweeps a parameter grid
# 500+ times; those cost real CPU and are worth metering per account rather
# than per address (an office behind one NAT would otherwise share a budget).
def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        log.warning("Ignoring non-numeric %s=%r, using default", name, raw, extra={"env_var": name})
        return default


def _rate_store():
    """Firestore for the per-user limits when there is a Firestore to use.

    Same rule as the price cache: a service account or the emulator. Without
    either (a dev machine, the unit tests) the limiters stay in-process.
    RATE_LIMIT_STORE=memory forces that too.
    """
    if os.environ.get("RATE_LIMIT_STORE", "firestore").lower() == "memory":
        return None
    if os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return FirestoreCounterStore(get_db)
    return None


# The per-IP limit runs on every request, so it stays in-process: a Firestore
# round trip on each page load is not worth a ceiling that is already only a
# flood guard. The per-user limits gate the expensive endpoints, where one
# extra round trip is small next to the run, and they hold across instances.
ip_limiter = RateLimiter(limit=_int_env("RATE_LIMIT_IP_PER_MIN", 120), window_seconds=60)
backtest_limiter = SharedRateLimiter(
    "backtest", limit=_int_env("RATE_LIMIT_BACKTEST_PER_MIN", 20), window_seconds=60, store_factory=_rate_store
)
validate_limiter = SharedRateLimiter(
    "validate", limit=_int_env("RATE_LIMIT_VALIDATE_PER_MIN", 5), window_seconds=60, store_factory=_rate_store
)


# Signed out, so metered per address, and only on a cache miss: a link going
# round a group chat is computed once, then served from share.cache and the CDN.
# An index scan runs up to a hundred backtests in one request.
scan_limiter = SharedRateLimiter(
    "scan", limit=_int_env("RATE_LIMIT_SCAN_PER_MIN", 3), window_seconds=60, store_factory=_rate_store
)
share_limiter = RateLimiter(limit=_int_env("RATE_LIMIT_SHARE_PER_MIN", 10), window_seconds=60)


def client_ip(request: Request) -> str:
    """Best-effort caller address.

    Behind Cloud Run the socket peer is the load balancer, so the real caller is
    the first entry of X-Forwarded-For. That header is spoofable in general, but
    Google's proxy appends rather than trusts, and the fallback keeps local dev
    working where the header is absent.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_quota(user: dict) -> dict:
    """Refuse the run if the account is out of monthly quota.

    Separate from the rate limiter: that one protects the server from bursts,
    this one is the monthly fair-use limit. A 402 rather than a 429 so the
    client can tell "slow down for a minute" apart from "this month is used
    up". Nothing is for sale (DECISIONS 24 Nov, personal project), so the
    message never offers an upgrade.
    """
    quota = check_quota(user.get("profile"))
    if not quota["allowed"]:
        raise HTTPException(
            status_code=402,
            detail=(
                f"You have used all {quota['limit']} runs for this month. Finertia is a "
                "free personal project, so runs have a fair-use limit; the counter "
                "resets at the start of next month."
            ),
        )
    return quota


def record_run(db, uid: str, profile: dict, batch=None) -> None:
    """Increment the usage counters for a completed run.

    The period stamp is rewritten every time so a counter left over from an
    earlier month is replaced rather than added to — `runs_used` already reads a
    stale period as zero, and this is what makes the stored value agree.

    A merge, not an update: an update fails on a user with no profile document,
    which turned a run that had already been saved into a 500 (feedback #12).

    Given a `batch`, the write joins it instead of going out on its own, so a
    backtest saves its run and its counters in one round trip.
    """
    period = current_period()
    updates = {
        "totalRuns": firestore.Increment(1),
        "lastLoginAt": firestore.SERVER_TIMESTAMP,
        "quotaPeriod": period,
    }
    if (profile or {}).get("quotaPeriod") == period:
        updates["runsThisPeriod"] = firestore.Increment(1)
    else:
        updates["runsThisPeriod"] = 1

    ref = db.collection("users").document(uid)
    if batch is not None:
        batch.set(ref, updates, merge=True)
        return
    with step("user_write"):
        ref.set(updates, merge=True)


# Validations a month on the free plan, a fair-use limit: each one costs
# hundreds of backtests of CPU and many price reads. A deployment setting, not
# a plan constant, so it can be changed without a code change; 0 switches
# validation off for free accounts. The Deploy workflow sets it explicitly.
FREE_VALIDATIONS_PER_MONTH = max(0, _int_env("FREE_VALIDATIONS_PER_MONTH", 10))

# Whether a portfolio run is kept in History like a single-ticker one. Off
# until the tester round closes, so the live product does not change under
# the testers; History and the admin views read either kind of document.
SAVE_PORTFOLIO_RUNS = os.environ.get("SAVE_PORTFOLIO_RUNS", "").lower() in ("1", "true")

_VALIDATION_OFF_DETAIL = (
    "Walk-forward validation and the permutation test are switched off on this "
    "deployment. Each run sweeps a parameter grid and then reshuffles the signals "
    "hundreds of times, so they cost far more than a single backtest."
)


def _validation_used_up(limit: int) -> HTTPException:
    noun = "validation" if limit == 1 else f"{limit} validations"
    return HTTPException(
        status_code=402,
        detail=(
            f"You have used your {noun} for this month. Each one costs hundreds of "
            "backtests, so validation has a fair-use limit; it resets at the start "
            "of next month."
        ),
    )


def check_validation_allowed(user: dict) -> None:
    """Refuse a validation the plan does not allow, before any other check
    that might be worth telling the user about first. It takes no slot."""
    quota = check_validation_quota(user["profile"], FREE_VALIDATIONS_PER_MONTH)
    if quota["allowed"]:
        return
    if quota["limit"] == 0:
        raise HTTPException(status_code=402, detail=_VALIDATION_OFF_DETAIL)
    raise _validation_used_up(quota["limit"])


def take_validation_slot(user: dict) -> dict | None:
    """Take one of the free plan's validations, atomically. None on Pro.

    Called last, after every check that can refuse the request, so a refusal
    never costs the user their validation. The profile read in
    `check_validation_allowed` can be stale under concurrent requests; the
    transaction in `validation_allowance.reserve` is the real check.
    """
    quota = check_validation_quota(user["profile"], FREE_VALIDATIONS_PER_MONTH)
    if quota["limit"] is None:
        return None
    try:
        with step("allowance"):
            taken = validation_allowance.reserve(get_db(), user["uid"], quota["limit"])
    except validation_allowance.Contended:
        # Several validations from one account at once; one of them wins the
        # slot. The others are told to retry, not shown a 500.
        raise HTTPException(
            status_code=409,
            detail="Another validation on your account is starting. Try again in a moment.",
            headers={"Retry-After": "2"},
        )
    if taken is None:
        raise _validation_used_up(quota["limit"])
    log.info("free validation taken", extra={"uid": user["uid"], "period": taken["period"]})
    return {**taken, "limit": quota["limit"]}


def give_back_validation_slot(user: dict, slot: dict | None) -> None:
    """Hand back a free validation whose run produced no result. A failure
    here is logged, not raised: the user should see the original error."""
    if slot is None:
        return
    try:
        validation_allowance.release(get_db(), user["uid"], slot["period"])
    except Exception:  # noqa: BLE001
        log.warning("could not give back a free validation", exc_info=True,
                    extra={"uid": user["uid"], "period": slot["period"]})


def with_allowance(result: dict, slot: dict | None) -> dict:
    """Tell a free user how many validations are left this month."""
    if slot is not None:
        result["free_validations_remaining"] = max(0, slot["limit"] - slot["used"])
    return result


def _check_limit(limiter: RateLimiter, key: str, cost: int = 1) -> dict:
    with step("ratelimit"):
        return limiter.check(key, cost=cost)


def _refuse_if_limited(verdict: dict, what: str) -> None:
    """Raise 429 with a Retry-After header if the check said no."""
    if not verdict["allowed"]:
        retry = max(1, int(round(verdict["retry_after"])))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached for {what}. Try again in {retry} second(s).",
            headers={"Retry-After": str(retry)},
        )


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


# For a request's independent database round trips. Each trip is mostly
# waiting on the network, so a few threads go a long way.
_io_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="io")


def in_parallel(*calls):
    """Run blocking calls at the same time and return their results in order.

    Each call runs in a copy of the caller's context, so its timing steps land
    in the same request's collector. An exception from any call is re-raised.
    """
    futures = [_io_pool.submit(contextvars.copy_context().run, call) for call in calls]
    return [f.result() for f in futures]


def inject_user(
    authorization: Optional[str] = Header(None),
    *,
    limit: tuple[RateLimiter, str, int] | None = None,
) -> dict:
    """Verify the Bearer token and return {uid, email, role}.

    Blocked accounts (isActive == False) are rejected with 403 here, so every
    authenticated route is closed to them without needing its own check.

    `limit` is (limiter, what, cost) for the routes behind a per-user rate
    limit. The limiter and the profile read are each a database round trip and
    need nothing from each other, so they run at the same time. The 403 for a
    blocked account still wins over a 429.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    with step("auth"):
        user = verify_token(token)
    uid = user["uid"]

    # A missing profile means the account was just created and the client has
    # not written users/{uid} yet — treat it as a normal active user.
    def read_profile() -> dict:
        with step("profile"):
            return get_user_profile(uid) or {}

    verdict = None
    if limit is None:
        profile = read_profile()
    else:
        limiter, what, cost = limit
        profile, verdict = in_parallel(read_profile, lambda: _check_limit(limiter, uid, cost))
    if profile.get("isActive") is False:
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Contact support if you believe this is an error.",
        )

    if verdict is not None:
        _refuse_if_limited(verdict, limit[1])

    user["role"] = profile.get("role", "user")
    sentry_set_user(uid)
    # Carried through so quota and entitlement checks do not each re-read the
    # same document. inject_user is the only place that reads it.
    user["profile"] = profile
    return user


def inject_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Like inject_user but also asserts the caller has admin role."""
    user = inject_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

