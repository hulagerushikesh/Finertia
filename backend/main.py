"""FastAPI application — all routes, middleware, and backtest orchestration."""

import contextvars
import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from firebase_admin import firestore

from data import DataUnavailableError, fetch_ohlcv
from engine import compute_returns, apply_positions, compute_benchmark
from bootstrap import bootstrap_metrics, stable_seed
from costs import cost_sensitivity, portfolio_cost_sensitivity
from rolling import rolling_walk_forward
from regimes import regime_breakdown
from sharpe_test import sharpe_difference_test
from metrics import compute_metrics
from analytics import monthly_returns, annual_returns, rolling_sharpe
import billing
from logging_config import configure_logging, configure_sentry
from plans import (
    check_quota,
    check_validation_quota,
    current_period,
    max_portfolio_size,
    PLAN_NAMES,
    plan_for,
    public_plans,
)
import validation_allowance
from ratelimit import FirestoreCounterStore, RateLimiter, SharedRateLimiter
from risk import apply_stops, size_positions
from portfolio import (
    align_closes,
    equal_weights,
    inverse_vol_weights,
    combine,
    contribution_summary,
    diversification_ratio,
)
from schemas import (
    BacktestRequest,
    ValidateRequest,
    CompareRequest,
    PortfolioRequest,
    PortfolioValidateRequest,
    UserPatch,
    DeleteAccountRequest,
    RISK_KEYS,
)
from strategies import build_positions, longest_window, param_grid, STRATEGY_NAMES, STRATEGIES
from validation import walk_forward, permutation_test
from portfolio_validation import leg_positions, portfolio_walk_forward, portfolio_permutation_test
from firebase_admin_init import verify_token, get_user_profile, get_db, emulator_mode, delete_auth_user
from admin_queries import platform_stats, list_users, list_runs
from account import delete_account, export_account
from monitoring import init_sentry, set_user as sentry_set_user, tag_request
import timing
from timing import step

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
_EMULATOR = emulator_mode()
if not _EMULATOR:
    load_dotenv()

REQUIRED_ENV_VARS = () if _EMULATOR else ("FIREBASE_SERVICE_ACCOUNT_JSON",)

_missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
if _missing:
    raise RuntimeError(
        "Missing required environment variable(s): "
        + ", ".join(_missing)
        + ". Copy .env.example to backend/.env and fill in the values from the "
        "Firebase Console (Project Settings → Service accounts → Generate new "
        "private key)."
    )

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

log = configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
# Before the app exists, so the SDK's FastAPI integration sees it created.
init_sentry(emulator=_EMULATOR)

# Optional integrations, announced at startup so a misconfigured deployment is
# visible in the first log line rather than discovered when something breaks.
log.info(
    "starting",
    extra={
        "sentry": configure_sentry(),
        "billing": billing.is_configured(),
        "allowed_origins": os.environ.get("ALLOWED_ORIGINS", "http://localhost:5174"),
    },
)

app = FastAPI(title="Finertia API", version="1.0.0")

_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5174")
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Paths that only ever read tiny documents and are polled by the UI — holding
# them to the same budget as a backtest would break normal navigation.
_RATE_LIMIT_EXEMPT = {"/api/health", "/docs", "/openapi.json", "/redoc"}

_requests_seen = 0
_PRUNE_EVERY = 500



def _client_ip(request: Request) -> str:
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


def _enforce_quota(user: dict) -> dict:
    """Refuse the run if the account is out of monthly quota.

    Separate from the rate limiter: that one protects the server from bursts,
    this one is the product's billing boundary. A 402 rather than a 429 so the
    client can tell "slow down" apart from "upgrade".
    """
    quota = check_quota(user.get("profile"))
    if not quota["allowed"]:
        raise HTTPException(
            status_code=402,
            detail=(
                f"You have used all {quota['limit']} runs on the "
                f"{quota['plan']} plan this month. Upgrade for unlimited runs, "
                "or wait for the counter to reset at the start of next month."
            ),
        )
    return quota


def _record_run(db, uid: str, profile: dict, batch=None) -> None:
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


# The free plan's validations a month. A deployment setting, not a plan
# constant: it stays 0 (the Pro wall, as before) while a tester round is
# running, so every tester sees the same product, and is switched on with an
# env var afterwards.
FREE_VALIDATIONS_PER_MONTH = max(0, _int_env("FREE_VALIDATIONS_PER_MONTH", 0))

_PRO_ONLY_DETAIL = (
    "Walk-forward validation and the permutation test are Pro features. "
    "Each run sweeps a parameter grid and then reshuffles the signals "
    "hundreds of times, so they cost far more than a single backtest."
)


def _validation_used_up(limit: int) -> HTTPException:
    noun = "validation" if limit == 1 else f"{limit} validations"
    return HTTPException(
        status_code=402,
        detail=(
            f"You have used your free {noun} for this month. Pro validates "
            "without a limit, and the free allowance resets at the start of next month."
        ),
    )


def _check_validation_allowed(user: dict) -> None:
    """Refuse a validation the plan does not allow, before any other check
    that might be worth telling the user about first. It takes no slot."""
    quota = check_validation_quota(user["profile"], FREE_VALIDATIONS_PER_MONTH)
    if quota["allowed"]:
        return
    if quota["limit"] == 0:
        raise HTTPException(status_code=402, detail=_PRO_ONLY_DETAIL)
    raise _validation_used_up(quota["limit"])


def _take_validation_slot(user: dict) -> dict | None:
    """Take one of the free plan's validations, atomically. None on Pro.

    Called last, after every check that can refuse the request, so a refusal
    never costs the user their validation. The profile read in
    `_check_validation_allowed` can be stale under concurrent requests; the
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


def _give_back_validation_slot(user: dict, slot: dict | None) -> None:
    """Hand back a free validation whose run produced no result. A failure
    here is logged, not raised: the user should see the original error."""
    if slot is None:
        return
    try:
        validation_allowance.release(get_db(), user["uid"], slot["period"])
    except Exception:  # noqa: BLE001
        log.warning("could not give back a free validation", exc_info=True,
                    extra={"uid": user["uid"], "period": slot["period"]})


def _with_allowance(result: dict, slot: dict | None) -> dict:
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


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Attach a request id, apply the IP rate limit, and log one line per request.

    The id is echoed as X-Request-Id so a user reporting a failure can quote it
    and it can be found directly in the logs.
    """
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    tag_request(request_id)
    steps = timing.begin()
    started = time.perf_counter()
    path = request.url.path

    global _requests_seen
    _requests_seen += 1
    seen = _requests_seen
    if _requests_seen % _PRUNE_EVERY == 0:
        # Expired keys are only dropped when they are next looked up, so a
        # one-time visitor would otherwise sit in the dict forever. Sweeping on
        # a request counter avoids needing a background task.
        for limiter in (ip_limiter, backtest_limiter, validate_limiter):
            limiter.prune()

    if path not in _RATE_LIMIT_EXEMPT:
        verdict = ip_limiter.check(_client_ip(request))
        if not verdict["allowed"]:
            retry = max(1, int(round(verdict["retry_after"])))
            log.warning(
                "rate limited by ip",
                extra={"request_id": request_id, "path": path, "retry_after": retry},
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Too many requests. Try again in {retry} second(s)."},
                headers={"Retry-After": str(retry), "X-Request-Id": request_id},
            )

    try:
        response = await call_next(request)
    except Exception:
        # Log with the traceback, then re-raise so the exception handler below
        # produces the response. Logging here keeps the stack trace attached to
        # the same request id as the access log line.
        duration_ms = int((time.perf_counter() - started) * 1000)
        log.exception(
            "request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "duration_ms": duration_ms,
                **timing.as_log_fields(steps),
            },
        )
        raise

    total_ms = (time.perf_counter() - started) * 1000
    duration_ms = int(total_ms)
    response.headers["X-Request-Id"] = request_id
    response.headers["Server-Timing"] = timing.server_timing(steps, total_ms)
    log.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            # 1 on a fresh instance: separates cold starts from slow requests.
            "instance_request": seen,
            **timing.as_log_fields(steps),
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a clean JSON body instead of leaking a stack trace to the client.

    The request id goes in the body so a bug report carries the one string
    needed to find the full traceback in the logs.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Something went wrong on our side. Please try again.",
            "request_id": request_id,
        },
        headers={"X-Request-Id": request_id},
    )

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


# For a request's independent database round trips. Each trip is mostly
# waiting on the network, so a few threads go a long way.
_io_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="io")


def _in_parallel(*calls):
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
        profile, verdict = _in_parallel(read_profile, lambda: _check_limit(limiter, uid, cost))
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# Routes that touch Firestore, the price provider or the engine are plain
# `def`, not `async def`. Every one of those calls blocks, and in an
# `async def` it blocks the event loop: the instance then serves one request
# at a time, health checks included, while it waits on a database a quarter
# of a second away. FastAPI runs a plain `def` route in a worker thread, so
# one request's wait no longer holds up the rest. Only routes that never block
# stay `async` (tests/test_routes.py checks the list).


@app.get("/api/health")
async def health():
    """Health check endpoint — no auth required.

    Also says what is serving: `commit` is the git SHA the Deploy workflow
    passes in as GIT_SHA, `revision` the Cloud Run revision. The release
    checklist compares `commit` with the `backend-deployed` tag, so "the tag
    says X" and "production runs X" cannot drift apart unnoticed. Both are
    null locally. The repository is public, so neither tells anyone anything.
    """
    return {
        "status": "ok",
        "commit": os.environ.get("GIT_SHA") or None,
        "revision": os.environ.get("K_REVISION") or None,
    }


@app.get("/api/plans")
async def list_plans():
    """Plan tiers for the pricing page — no auth required.

    `billing_enabled` tells the client whether an upgrade button can do
    anything, so a self-hosted deployment shows the tiers without offering a
    checkout that would fail.
    """
    return {"plans": public_plans(), "billing_enabled": billing.is_configured()}


@app.get("/api/me/usage")
def my_usage(authorization: Optional[str] = Header(None)):
    """Current plan, quota consumption, and entitlements for the caller."""
    user = inject_user(authorization)
    profile = user["profile"]
    plan = plan_for(profile)
    quota = check_quota(profile)
    validations = check_validation_quota(profile, FREE_VALIDATIONS_PER_MONTH)

    return {
        "plan": plan["name"],
        "plan_label": plan["label"],
        "used": quota["used"],
        "limit": quota["limit"],
        "remaining": quota["remaining"],
        "period": current_period(),
        "validation": plan["validation"],
        # The free plan's monthly validations; limit and remaining are None
        # on Pro, and limit is 0 while the free allowance is switched off.
        "validations_used": validations["used"],
        "validations_limit": validations["limit"],
        "validations_remaining": validations["remaining"],
        "max_portfolio_size": plan["max_portfolio_size"],
        "billing_enabled": billing.is_configured(),
    }


@app.get("/api/me/export")
def export_my_data(authorization: Optional[str] = Header(None)):
    """Everything stored about the caller, as a JSON download (DPDP: access)."""
    user = inject_user(authorization)
    with step("export_read"):
        body = export_account(get_db(), user["uid"], user["email"])
    stamp = body["exported_at"][:10]
    log.info("account exported", extra={"uid": user["uid"], "runs": len(body["runs"])})
    return JSONResponse(
        jsonable_encoder(body),
        headers={"Content-Disposition": f'attachment; filename="finertia-export-{stamp}.json"'},
    )


@app.delete("/api/me")
def delete_my_account(body: DeleteAccountRequest, authorization: Optional[str] = Header(None)):
    """Delete the caller's account and every document that belongs to it
    (DPDP: erasure). See account.py for what is removed and in what order."""
    user = inject_user(authorization)
    profile = user["profile"]

    if (body.confirm or "").strip().lower() != (user["email"] or "").strip().lower():
        raise HTTPException(status_code=400, detail="Type your account's email address to confirm.")
    # An admin deleting themselves could leave nobody able to open the admin
    # panel; the role has to be removed by another admin first.
    if user["role"] == "admin":
        raise HTTPException(status_code=409, detail="Admin accounts cannot delete themselves. Ask another admin to remove the role first.")
    # Deleting the account would not stop Stripe charging the card.
    if profile.get("planSource") == "stripe" and plan_for(profile)["name"] != "free":
        raise HTTPException(status_code=409, detail="Cancel your subscription before deleting the account.")

    with step("delete"):
        counts = delete_account(get_db(), user["uid"], delete_auth_user)
    log.info("account deleted", extra={"uid": user["uid"], **counts})
    return {"deleted": True, **counts}


@app.post("/api/billing/checkout")
def create_checkout(authorization: Optional[str] = Header(None)):
    """Start a Stripe Checkout session and return the URL to redirect to."""
    user = inject_user(authorization)

    if not billing.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Billing is not enabled on this deployment.",
        )

    origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://localhost:5174"
    try:
        url = billing.create_checkout_session(
            uid=user["uid"],
            email=user["email"],
            success_url=f"{origin}/profile?upgraded=1",
            cancel_url=f"{origin}/pricing",
        )
    except Exception as exc:
        log.exception("checkout session failed", extra={"uid": user["uid"]})
        raise HTTPException(status_code=502, detail="Could not start checkout.") from exc

    return {"url": url}


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    """Apply Stripe subscription events to the user's plan.

    Deliberately unauthenticated — Stripe cannot present a Firebase token — so
    the signature check *is* the authentication. Without it, anyone who learned
    this URL could POST a completed-checkout event and upgrade for free.
    """
    secret = billing.webhook_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="Webhooks are not configured.")

    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not billing.verify_signature(payload, signature, secret):
        log.warning(
            "rejected webhook with a bad signature",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Malformed payload") from exc

    uid, new_plan = billing.plan_from_event(event)
    if not uid:
        # Acknowledge anything we do not act on; a non-2xx makes Stripe retry
        # the same event indefinitely.
        return {"received": True, "applied": False}

    # Async only to read the raw body for the signature; the Firestore calls
    # block, so they go to a worker thread like every other route's.
    applied = await run_in_threadpool(_apply_plan, uid, new_plan, event.get("type"))
    return {"received": True, "applied": applied}


def _apply_plan(uid: str, new_plan: str, event_type: str | None) -> bool:
    db = get_db()
    ref = db.collection("users").document(uid)
    if not ref.get().exists:
        log.warning("webhook referenced an unknown user", extra={"uid": uid})
        return False

    ref.update({"plan": new_plan, "planSource": "stripe"})
    log.info(
        "plan updated from stripe",
        extra={"uid": uid, "plan": new_plan, "event": event_type},
    )
    return True


@app.get("/api/strategies")
async def list_strategies():
    """Available strategies and their parameter names — no auth required.

    Lets the frontend render the strategy picker without hardcoding a list that
    would drift out of sync with the backend registry.
    """
    return {
        "strategies": [
            {"id": name, "label": STRATEGIES[name]["label"]} for name in STRATEGY_NAMES
        ]
    }


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest, authorization: Optional[str] = Header(None)):
    """Run a backtest for the selected strategy and persist results to Firestore."""
    user = inject_user(authorization, limit=(backtest_limiter, "backtests", 1))
    uid = user["uid"]
    email = user["email"]
    _enforce_quota(user)

    start_time = time.time()

    # 1. Fetch data — a bad ticker or an empty range is the user's mistake, so
    # surface it as a 400 with the underlying reason rather than a 500.
    try:
        df = fetch_ohlcv(req.ticker, req.start, req.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    data_source = df.attrs.get("data_source", "yfinance")
    close = df["Close"]

    if len(close) < req.warmup_bars() + 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(close)} trading days returned for {req.ticker} in this range — "
                "not enough history for the chosen indicator and sizing windows."
            ),
        )

    # 2. Signals — direction only
    signals = build_positions(close, req.strategy, req.strategy_params())
    returns = compute_returns(close)

    # 3. Risk overlays. Order matters: stops decide whether the trade is still
    # open, sizing decides how large it is. Sizing first would scale a position
    # that the stop is about to close, and the stop's own P&L tracking would
    # then be measuring a moving target rather than the trade.
    signals = apply_stops(signals, returns, req.stop_loss, req.take_profit)
    signals = size_positions(
        signals,
        returns,
        sizing=req.sizing,
        target_vol=req.target_vol,
        vol_window=req.vol_window,
        max_leverage=req.max_leverage,
    )

    # 4. Engine
    engine_out = apply_positions(signals, returns, req.transaction_cost)
    benchmark = compute_benchmark(close)

    net_return = engine_out["net_return"].fillna(0)
    equity_curve = engine_out["equity_curve"].fillna(1)
    drawdown = engine_out["drawdown"].fillna(0)
    position = engine_out["position"]

    # 5. Metrics
    metrics = compute_metrics(net_return, equity_curve, drawdown, position)

    # 5b. Uncertainty around those metrics.
    #
    # Deliberately NOT a Pro feature, unlike validation. Validation is gated
    # because a grid sweep plus hundreds of permutations genuinely costs
    # hundreds of backtests; this is one resample of a series already in memory
    # and adds ~50ms. Gating it would mean the free tier — the tier most likely
    # to read a Sharpe of 1.2 as a fact about the strategy — is the only one
    # shown a naked point estimate, which is the exact failure the module exists
    # to prevent.
    #
    # The seed is derived from the run's own inputs so the interval is stable:
    # re-running the same backtest returns the same band rather than a slightly
    # different one each time, which would teach the user the number is arbitrary.
    confidence_intervals = bootstrap_metrics(
        net_return,
        seed=stable_seed(
            req.ticker.upper(),
            req.start,
            req.end,
            req.strategy,
            sorted(req.strategy_params().items()),
            sorted(req.risk_params().items()),
            req.transaction_cost,
        ),
    )

    # 6. Build response arrays
    dates = [d.strftime("%Y-%m-%d") for d in close.index]
    benchmark_vals = benchmark.fillna(1).tolist()
    equity_vals = equity_curve.tolist()
    drawdown_vals = drawdown.tolist()
    position_vals = position.tolist()
    net_return_vals = net_return.tolist()

    equity_curve_data = [
        {"date": d, "strategy": round(s, 6), "benchmark": round(b, 6)}
        for d, s, b in zip(dates, equity_vals, benchmark_vals)
    ]

    drawdown_data = [
        {"date": d, "value": round(v, 6)}
        for d, v in zip(dates, drawdown_vals)
    ]

    # Trade entry rows only (position changed), capped at 500 most recent
    trade_rows = []
    for i, (d, pos, ret, eq) in enumerate(zip(dates, position_vals, net_return_vals, equity_vals)):
        if i == 0:
            continue
        if position_vals[i] != position_vals[i - 1]:
            trade_rows.append({
                "date": d,
                "position": int(pos),
                "daily_return": round(ret, 6),
                "equity": round(eq, 6),
            })
    trades = trade_rows[-500:]

    # Time-sliced views — small payloads next to the equity curve.
    benchmark_daily = close.pct_change().fillna(0)
    monthly = monthly_returns(net_return)
    annual = annual_returns(net_return, benchmark_daily)
    rolling = rolling_sharpe(net_return, window=60)
    # Where the return was earned, in the market's own terms: the strategy's
    # Sharpe on the calm, middling and turbulent thirds of the period.
    regimes = regime_breakdown(net_return, position, benchmark_daily)
    # The page prints the strategy's Sharpe beside buy-and-hold's. This is the
    # p-value that belongs between them — Ledoit-Wolf on the paired series, so
    # the shared bars work for the reader instead of against them. Same
    # reasoning as the confidence intervals above for not gating it: 50-90ms on
    # a series already in memory, and the free tier is the tier most likely to
    # read "1.2 vs 0.6" as a settled fact.
    benchmark_test = sharpe_difference_test(
        net_return,
        benchmark_daily,
        seed=stable_seed(
            req.ticker.upper(), req.start, req.end, req.strategy, "sharpe-test"
        ),
    )

    # How far the cost assumption can be wrong before the edge is gone.
    #
    # This is the level question, and the level is the only part of the cost
    # model that moves the number on the page — see costs.py for the
    # measurement that ruled out shipping a vol-scaled model instead. Five
    # engine runs plus a bisection, ~5ms, so it is not gated either.
    cost_block = cost_sensitivity(position, returns, req.transaction_cost)

    signals_summary = {
        "long_days": int((position > 0).sum()),
        "short_days": int((position < 0).sum()),
        "flat_days": int((position == 0).sum()),
    }

    duration_ms = int((time.time() - start_time) * 1000)

    # 7. Persist to Firestore
    run_id = str(uuid.uuid4())
    db = get_db()
    run_doc = {
        "runId": run_id,
        "uid": uid,
        "email": email,
        "ticker": req.ticker.upper(),
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "params": {
            **req.strategy_params(),
            **req.risk_params(),
            "transaction_cost": req.transaction_cost,
        },
        "metrics": metrics,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "durationMs": duration_ms,
    }
    batch = db.batch()
    batch.set(db.collection("runs").document(run_id), run_doc)
    _record_run(db, uid, user["profile"], batch=batch)
    with step("run_write"):
        batch.commit()

    return {
        "runId": run_id,
        "metrics": metrics,
        "equity_curve": equity_curve_data,
        "drawdown": drawdown_data,
        "trades": trades,
        "monthly_returns": monthly,
        "annual_returns": annual,
        "rolling_sharpe": rolling,
        "regimes": regimes,
        "benchmark_test": benchmark_test,
        "cost_sensitivity": cost_block,
        "signals_summary": signals_summary,
        "confidence_intervals": confidence_intervals,
        # "yfinance" | "cache" | "cache-stale" | "memory". Stale means Yahoo
        # was down and this is the last good copy — the UI says so.
        "data_source": data_source,
        "duration_ms": duration_ms,
    }


@app.post("/api/validate")
def validate_strategy(req: ValidateRequest, authorization: Optional[str] = Header(None)):
    """Run the two overfitting checks a single backtest cannot answer.

    Walk-forward asks whether parameters survive on data they were not chosen on.
    The permutation test asks whether signal timing beats random timing at the
    same market exposure. Results are diagnostic and not persisted.
    """
    # Tighter than the backtest budget: a validation run rebuilds positions once
    # per grid combination and then again for every permutation trial, so one
    # call is worth hundreds of backtests in CPU terms.
    user = inject_user(authorization, limit=(validate_limiter, "validation runs", 1))
    _check_validation_allowed(user)
    _enforce_quota(user)

    slot = _take_validation_slot(user)
    try:
        result = _validate_single(req)
    except BaseException:
        _give_back_validation_slot(user, slot)
        raise
    return _with_allowance(result, slot)


def _validate_single(req) -> dict:
    """Walk-forward and the permutation test for one ticker; the work behind `/api/validate`."""
    start_time = time.time()

    try:
        df = fetch_ohlcv(req.ticker, req.start, req.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DataUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    data_source = df.attrs.get("data_source", "yfinance")
    close = df["Close"]

    params = req.strategy_params()
    # Score the user's own values for exactly the keys the grid sweeps, so the
    # comparison against the optimised set is like for like.
    swept_keys = param_grid(req.strategy)[0].keys()
    user_params = {k: params[k] for k in swept_keys if k in params}

    try:
        wf = walk_forward(
            close,
            transaction_cost=req.transaction_cost,
            strategy=req.strategy,
            base_params=params,
            user_params=user_params,
            split_ratio=req.split_ratio,
            seed=stable_seed(req.ticker.upper(), req.start, req.end, req.strategy, "snooping"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # The single split above is one draw. Walk it forward so the verdict is
    # reported per segment, with the market's own return beside each — the
    # only way to tell "no edge" from "no edge in the stretch the split
    # happened to score". Cheap: positions per grid cell are built once.
    try:
        rolling = rolling_walk_forward(
            close,
            transaction_cost=req.transaction_cost,
            strategy=req.strategy,
            base_params=params,
            n_folds=req.rolling_folds,
            seed=stable_seed(req.ticker.upper(), req.start, req.end, req.strategy, "rolling"),
        )
    except ValueError as exc:
        rolling = {"computable": False, "reason": str(exc)}

    positions = build_positions(close, req.strategy, params)
    returns = compute_returns(close)
    permutation = permutation_test(
        positions, returns, req.transaction_cost, n_trials=req.permutation_trials
    )

    return {
        "ticker": req.ticker,
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "bars": len(close),
        "walk_forward": wf,
        "rolling_walk_forward": rolling,
        "permutation": permutation,
        "data_source": data_source,
        "duration_ms": int((time.time() - start_time) * 1000),
    }




def _fetch_aligned(req: PortfolioRequest) -> tuple[pd.DataFrame, dict, str]:
    """Fetch every leg, align on shared days, reject a book too short to warm up.

    Every leg is fetched before anything is computed — one bad ticker should
    fail the request outright rather than silently yielding a smaller
    portfolio than the user asked for.
    """
    def fetch(symbol):
        try:
            return fetch_ohlcv(symbol, req.start, req.end)
        except (ValueError, DataUnavailableError) as exc:
            return exc

    # The legs' price reads are independent round trips, so they go out
    # together. Errors are reported in the order the user listed the tickers.
    frames = _in_parallel(*[lambda s=symbol: fetch(s) for symbol in req.tickers])
    closes = {}
    sources = set()
    for symbol, df in zip(req.tickers, frames):
        if isinstance(df, ValueError):
            raise HTTPException(status_code=400, detail=f"{symbol}: {df}") from df
        if isinstance(df, DataUnavailableError):
            raise HTTPException(status_code=503, detail=f"{symbol}: {df}") from df
        closes[symbol] = df["Close"]
        sources.add(df.attrs.get("data_source", "yfinance"))
    # One stale leg makes the whole portfolio stale — that is the flag that matters.
    data_source = "cache-stale" if "cache-stale" in sources else "mixed" if len(sources) > 1 else next(iter(sources))

    try:
        aligned = align_closes(closes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if len(aligned) < req.warmup_bars() + 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(aligned)} trading days are shared by all "
                f"{len(req.tickers)} tickers — not enough for the chosen "
                "indicator and weighting windows."
            ),
        )
    return aligned, closes, data_source


def _portfolio_weights(req: PortfolioRequest, aligned: pd.DataFrame) -> pd.DataFrame:
    """The weight path the request asked for, on the aligned index."""
    if req.weighting == "inverse_vol":
        # Weights follow the *assets'* volatility, not the strategy's, so a leg
        # that happens to sit flat does not get an unbounded weight.
        asset_returns = aligned.pct_change().fillna(0.0)
        try:
            return inverse_vol_weights(
                asset_returns, window=req.weight_window, max_weight=req.max_weight
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return equal_weights(list(aligned.columns), aligned.index)


@app.post("/api/portfolio/validate")
def validate_portfolio(req: PortfolioValidateRequest, authorization: Optional[str] = Header(None)):
    """The overfitting checks, asked of the whole book.

    One parameter set is optimised on the basket's in-sample Sharpe and scored
    on the rest; the permutation test re-times every leg independently with
    the weight path held fixed (see `portfolio_validation.py` for why that is
    the null). Same plan gate and rate budget as `/api/validate`, plus the
    plan's portfolio-size cap. Diagnostic; not persisted.
    """
    user = inject_user(authorization, limit=(validate_limiter, "validation runs", 1))
    _check_validation_allowed(user)
    allowed_size = max_portfolio_size(user["profile"])
    if len(req.tickers) > allowed_size:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Your plan allows portfolios of up to {allowed_size} holdings; "
                f"you selected {len(req.tickers)}. Upgrade to run larger baskets."
            ),
        )
    _enforce_quota(user)

    slot = _take_validation_slot(user)
    try:
        result = _validate_book(req)
    except BaseException:
        _give_back_validation_slot(user, slot)
        raise
    return _with_allowance(result, slot)


def _validate_book(req) -> dict:
    """The same checks for a basket; the work behind `/api/portfolio/validate`."""
    start_time = time.time()
    aligned, _, data_source = _fetch_aligned(req)
    weights = _portfolio_weights(req, aligned)

    params = req.strategy_params()
    swept_keys = param_grid(req.strategy)[0].keys()
    user_params = {k: params[k] for k in swept_keys if k in params}
    seed_key = ("|".join(req.tickers), req.start, req.end, req.strategy, req.weighting)

    try:
        wf = portfolio_walk_forward(
            aligned,
            weights,
            transaction_cost=req.transaction_cost,
            strategy=req.strategy,
            base_params=params,
            user_params=user_params,
            split_ratio=req.split_ratio,
            seed=stable_seed(*seed_key, "snooping"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    permutation = portfolio_permutation_test(
        leg_positions(aligned, req.strategy, params),
        aligned.pct_change(),
        weights,
        req.transaction_cost,
        n_trials=req.permutation_trials,
    )

    return {
        "tickers": req.tickers,
        "start": req.start,
        "end": req.end,
        "strategy": req.strategy,
        "weighting": req.weighting,
        "bars": len(aligned),
        "walk_forward": wf,
        "permutation": permutation,
        "data_source": data_source,
        "duration_ms": int((time.time() - start_time) * 1000),
    }



@app.post("/api/portfolio")
def run_portfolio(req: PortfolioRequest, authorization: Optional[str] = Header(None)):
    """Run one strategy across several tickers and combine the legs.

    Each leg is a complete backtest — its own signals, stops, sizing, and
    transaction costs — so the portfolio is an aggregation of honest single
    results rather than a separate model with its own assumptions.
    """
    # One request is N data fetches and N full backtests, so it costs a slot
    # per leg rather than a single one, taken all at once or not at all.
    user = inject_user(authorization, limit=(backtest_limiter, "portfolio legs", len(req.tickers)))
    uid = user["uid"]
    _enforce_quota(user)

    allowed_size = max_portfolio_size(user["profile"])
    if len(req.tickers) > allowed_size:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Your plan allows portfolios of up to {allowed_size} holdings; "
                f"you selected {len(req.tickers)}. Upgrade to run larger baskets."
            ),
        )

    start_time = time.time()

    aligned, closes, data_source = _fetch_aligned(req)

    # How much history the inner join actually cost, measured against the leg
    # with the longest record rather than against the requested start date.
    # Comparing to the request would flag every run whose start landed on a
    # weekend or a holiday, and a warning that fires constantly gets ignored.
    longest_ticker = max(closes, key=lambda t: len(closes[t]))
    dropped_bars = len(closes[longest_ticker]) - len(aligned)
    limiting_ticker = min(closes, key=lambda t: len(closes[t])) if dropped_bars else None

    # 3. Run each leg exactly as a single-ticker backtest would.
    leg_returns = {}
    leg_metrics = {}
    # Kept so the cost block can re-run the legs at other costs. The loop
    # below reuses one `positions` name per iteration, so without this the
    # only surviving position series is the last leg's.
    leg_positions = {}
    leg_asset_returns = {}
    for symbol in req.tickers:
        close = aligned[symbol]
        returns = compute_returns(close)

        positions = build_positions(close, req.strategy, req.strategy_params())
        positions = apply_stops(positions, returns, req.stop_loss, req.take_profit)
        positions = size_positions(
            positions,
            returns,
            sizing=req.sizing,
            target_vol=req.target_vol,
            vol_window=req.vol_window,
            max_leverage=req.max_leverage,
        )

        out = apply_positions(positions, returns, req.transaction_cost)
        leg_net = out["net_return"].fillna(0)
        leg_returns[symbol] = leg_net
        leg_positions[symbol] = out["position"]
        leg_asset_returns[symbol] = returns
        leg_metrics[symbol] = compute_metrics(
            leg_net,
            out["equity_curve"].fillna(1),
            out["drawdown"].fillna(0),
            out["position"],
        )

    legs_frame = pd.DataFrame(leg_returns)

    # 4. Weight and combine.
    weights = _portfolio_weights(req, aligned)
    portfolio = combine(legs_frame, weights)

    net_return = portfolio["net_return"]
    equity = portfolio["equity_curve"]
    drawdown = portfolio["drawdown"]

    # 5. Portfolio metrics. compute_metrics counts trades from position changes;
    # a portfolio has no single position series, so it is handed the weighted
    # exposure — turnover of the book as a whole.
    exposure = portfolio["weights"].sum(axis=1)
    metrics = compute_metrics(net_return, equity, drawdown, exposure)

    contributions = contribution_summary(portfolio["contributions"])

    # A portfolio is not persisted as a run document — its legs are not a single
    # backtest — but it consumed the same compute, so it counts against quota.
    _record_run(get_db(), uid, user["profile"])

    dates_out = [d.strftime("%Y-%m-%d") for d in legs_frame.index]

    # An equal-weight buy-and-hold of the same names — the honest benchmark for
    # a portfolio, rather than any single ticker.
    bench_daily = aligned.pct_change().fillna(0.0).mean(axis=1)
    bench_equity = (1 + bench_daily).cumprod()

    benchmark_test = sharpe_difference_test(
        net_return,
        bench_daily,
        seed=stable_seed(
            ",".join(req.tickers), req.start, req.end, req.strategy, "sharpe-test"
        ),
    )

    # Same question as a single-ticker run, on the book. Valid because the
    # book is affine in cost exactly as one leg is — nothing upstream of the
    # weighted sum reads the cost. costs.py carries the check.
    cost_block = portfolio_cost_sensitivity(
        leg_positions, leg_asset_returns, weights, req.transaction_cost
    )

    return {
        "tickers": req.tickers,
        "strategy": req.strategy,
        "weighting": req.weighting,
        "start": dates_out[0],
        "end": dates_out[-1],
        "aligned_bars": len(legs_frame),
        # The inner join can truncate the period; saying so beats leaving the
        # user to wonder why their 2015 start date became 2021. Zero means the
        # holdings shared their full history and there is nothing to report.
        "dropped_bars": int(dropped_bars),
        "limiting_ticker": limiting_ticker,
        "longest_ticker_bars": int(len(closes[longest_ticker])),
        "metrics": metrics,
        "diversification_ratio": diversification_ratio(legs_frame, weights, net_return),
        # Against an equal-weight hold of the same names, not any one ticker.
        "benchmark_test": benchmark_test,
        "cost_sensitivity": cost_block,
        "equity_curve": [
            {"date": d, "strategy": round(s, 6), "benchmark": round(b, 6)}
            for d, s, b in zip(dates_out, equity.tolist(), bench_equity.tolist())
        ],
        "drawdown": [
            {"date": d, "value": round(v, 6)} for d, v in zip(dates_out, drawdown.tolist())
        ],
        "legs": [
            {
                "ticker": symbol,
                "avg_weight": round(float(weights[symbol].mean()), 4),
                "contribution": round(contributions[symbol], 6),
                "metrics": leg_metrics[symbol],
            }
            for symbol in req.tickers
        ],
        "monthly_returns": monthly_returns(net_return),
        "annual_returns": annual_returns(net_return, bench_daily),
        "rolling_sharpe": rolling_sharpe(net_return, window=60),
        "data_source": data_source,
        "duration_ms": int((time.time() - start_time) * 1000),
    }


@app.post("/api/compare")
def compare_runs(req: CompareRequest, authorization: Optional[str] = Header(None)):
    """Recompute several stored runs so their equity curves can be overlaid.

    Equity curves are deliberately not persisted — they are a few thousand floats
    per run and derivable from the config, so Firestore stores the config and we
    rebuild the curve here. That keeps documents small and means a fix to the
    engine retroactively corrects every historical chart.
    """
    # Each id costs a data fetch plus a full recompute, so this shares the
    # backtest budget rather than getting a free pass.
    user = inject_user(authorization, limit=(backtest_limiter, "comparisons", 1))
    uid = user["uid"]

    start_time = time.time()
    db = get_db()

    # Every run in one round trip rather than one each.
    with step("run_read"):
        fetched = {
            doc.id: doc
            for doc in db.get_all([db.collection("runs").document(r) for r in req.run_ids])
        }

    series = []
    for run_id in req.run_ids:
        doc = fetched.get(run_id)
        if doc is None or not doc.exists:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        d = doc.to_dict()
        if d.get("uid") != uid and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Access denied")

        strategy = d.get("strategy", "momentum")
        stored = d.get("params", {}) or {}
        # The run document keeps signal parameters, risk overlays, and the cost
        # in one flat map. They have to be separated again here, or the overlays
        # would be handed to the signal builder and silently never applied —
        # which would draw a curve that does not match the run it came from.
        cost = stored.get("transaction_cost", 0.001)
        risk = {k: stored.get(k) for k in RISK_KEYS if k in stored}
        params = {
            k: v for k, v in stored.items()
            if k != "transaction_cost" and k not in RISK_KEYS
        }

        try:
            close = fetch_ohlcv(d["ticker"], d["start"], d["end"])["Close"]
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Could not reload data for {d.get('ticker')}: {exc}",
            ) from exc
        except DataUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        returns = compute_returns(close)
        positions = build_positions(close, strategy, params)
        # Runs created before the risk overlays existed have no such keys; the
        # defaults reproduce the original always-in, unstopped behaviour.
        positions = apply_stops(
            positions, returns, risk.get("stop_loss"), risk.get("take_profit")
        )
        positions = size_positions(
            positions,
            returns,
            sizing=risk.get("sizing", "fixed"),
            target_vol=risk.get("target_vol", 0.15),
            vol_window=risk.get("vol_window", 20),
            max_leverage=risk.get("max_leverage", 2.0),
        )
        out = apply_positions(positions, returns, cost)
        equity = out["equity_curve"].fillna(1)

        series.append({
            "runId": run_id,
            "ticker": d.get("ticker"),
            "strategy": strategy,
            "start": d.get("start"),
            "end": d.get("end"),
            "params": params,
            "metrics": d.get("metrics", {}),
            "points": [
                {"date": dt.strftime("%Y-%m-%d"), "value": round(v, 6)}
                for dt, v in zip(close.index, equity.tolist())
            ],
        })

    # Runs can cover different tickers and different date ranges, so the only
    # honest shared axis is the date. Where a run has no bar for a date its key
    # is simply absent and the chart leaves a gap rather than inventing a value.
    all_dates = sorted({p["date"] for s in series for p in s["points"]})
    by_run = {s["runId"]: {p["date"]: p["value"] for p in s["points"]} for s in series}
    merged = []
    for date in all_dates:
        row = {"date": date}
        for s in series:
            value = by_run[s["runId"]].get(date)
            if value is not None:
                row[s["runId"]] = value
        merged.append(row)

    overlapping = sum(
        1 for row in merged if len(row) == len(series) + 1
    )

    return {
        "series": [{k: v for k, v in s.items() if k != "points"} for s in series],
        "chart": merged,
        # Two runs over disjoint periods produce a chart where the lines never
        # meet; the UI needs to be able to say so rather than imply comparison.
        "overlapping_days": overlapping,
        "duration_ms": int((time.time() - start_time) * 1000),
    }


@app.get("/api/history")
def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """Return paginated backtest history for the authenticated user."""
    user = inject_user(authorization)
    uid = user["uid"]

    db = get_db()
    query = (
        db.collection("runs")
        .where("uid", "==", uid)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
    )
    with step("history_read"):
        all_docs = list(query.stream())
    total = len(all_docs)
    page = all_docs[offset: offset + limit]

    runs = []
    for doc in page:
        d = doc.to_dict()
        m = d.get("metrics", {})
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


@app.get("/api/history/{run_id}")
def get_run(run_id: str, authorization: Optional[str] = Header(None)):
    """Fetch a single run by ID — only the owner or an admin may access it."""
    user = inject_user(authorization)
    uid = user["uid"]

    db = get_db()
    with step("run_read"):
        doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")

    data = doc.to_dict()
    if data.get("uid") != uid and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return data


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@app.get("/api/admin/stats")
def admin_stats(authorization: Optional[str] = Header(None)):
    """Return platform-wide statistics — admin only."""
    inject_admin(authorization)
    with step("admin_query"):
        return platform_stats(get_db())


@app.get("/api/admin/users")
def admin_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Return paginated user list — admin only."""
    inject_admin(authorization)
    with step("admin_query"):
        return list_users(get_db(), limit, offset, search)


@app.patch("/api/admin/users/{target_uid}")
def admin_patch_user(
    target_uid: str,
    patch: UserPatch,
    authorization: Optional[str] = Header(None),
):
    """Update isActive, role or plan on a user document — admin only.

    A plan set here is stamped `planSource: "admin"` so a comped Pro account is
    never counted as a paying one; the Stripe webhook stamps "stripe".
    """
    inject_admin(authorization)

    db = get_db()
    ref = db.collection("users").document(target_uid)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {}
    if patch.isActive is not None:
        update_data["isActive"] = patch.isActive
    if patch.role is not None:
        if patch.role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="role must be 'user' or 'admin'")
        update_data["role"] = patch.role
    if patch.plan is not None:
        if patch.plan not in PLAN_NAMES:
            raise HTTPException(status_code=400, detail=f"plan must be one of {', '.join(PLAN_NAMES)}")
        update_data["plan"] = patch.plan
        update_data["planSource"] = "admin"

    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    ref.update(update_data)
    return ref.get().to_dict()


@app.get("/api/admin/runs")
def admin_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    uid: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Return paginated run list with optional filters — admin only."""
    inject_admin(authorization)
    with step("admin_query"):
        return list_runs(get_db(), limit, offset, uid, ticker)


class SentryTestError(RuntimeError):
    """Raised on purpose by /api/admin/sentry-test."""


@app.post("/api/admin/sentry-test")
def admin_sentry_test(authorization: Optional[str] = Header(None)):
    """Raise an error on purpose to prove reporting works end to end — admin only.

    Comes back as an ordinary 500 with a request id; the matching issue should
    appear in Sentry within a minute, tagged with the same id.
    """
    inject_admin(authorization)
    raise SentryTestError("Deliberate test error from /api/admin/sentry-test")
