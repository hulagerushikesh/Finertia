"""FastAPI application — all routes, middleware, and backtest orchestration."""

import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from firebase_admin import firestore

from data import fetch_ohlcv
from engine import compute_returns, apply_positions, compute_benchmark
from metrics import compute_metrics
from analytics import monthly_returns, annual_returns, rolling_sharpe
import billing
from logging_config import configure_logging, configure_sentry
from plans import (
    check_quota,
    current_period,
    may_validate,
    max_portfolio_size,
    plan_for,
    public_plans,
)
from ratelimit import RateLimiter
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
    UserPatch,
    RISK_KEYS,
)
from strategies import build_positions, longest_window, param_grid, STRATEGY_NAMES, STRATEGIES
from validation import walk_forward, permutation_test
from firebase_admin_init import verify_token, get_user_profile, get_db

# ---------------------------------------------------------------------------
# Startup configuration checks — fail loudly rather than at first request
# ---------------------------------------------------------------------------

# Local dev convenience: in production (Cloud Run) the env vars are already set
# and no .env file exists, so this is a no-op there.
load_dotenv()

REQUIRED_ENV_VARS = ("FIREBASE_SERVICE_ACCOUNT_JSON",)

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


ip_limiter = RateLimiter(limit=_int_env("RATE_LIMIT_IP_PER_MIN", 120), window_seconds=60)
backtest_limiter = RateLimiter(limit=_int_env("RATE_LIMIT_BACKTEST_PER_MIN", 20), window_seconds=60)
validate_limiter = RateLimiter(limit=_int_env("RATE_LIMIT_VALIDATE_PER_MIN", 5), window_seconds=60)

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


def _record_run(db, uid: str, profile: dict) -> None:
    """Increment the usage counters for a completed run.

    The period stamp is rewritten every time so a counter left over from an
    earlier month is replaced rather than added to — `runs_used` already reads a
    stale period as zero, and this is what makes the stored value agree.
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

    db.collection("users").document(uid).update(updates)


def _enforce(limiter: RateLimiter, key: str, what: str) -> None:
    """Raise 429 with a Retry-After header if `key` is over budget."""
    verdict = limiter.check(key)
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
    started = time.perf_counter()
    path = request.url.path

    global _requests_seen
    _requests_seen += 1
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
            },
        )
        raise

    duration_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-Id"] = request_id
    log.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": duration_ms,
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


async def inject_user(authorization: Optional[str] = Header(None)) -> dict:
    """Verify the Bearer token and return {uid, email, role}.

    Blocked accounts (isActive == False) are rejected with 403 here, so every
    authenticated route is closed to them without needing its own check.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    user = verify_token(token)

    # A missing profile means the account was just created and the client has
    # not written users/{uid} yet — treat it as a normal active user.
    profile = get_user_profile(user["uid"]) or {}
    if profile.get("isActive") is False:
        raise HTTPException(
            status_code=403,
            detail="Your account has been suspended. Contact support if you believe this is an error.",
        )

    user["role"] = profile.get("role", "user")
    # Carried through so quota and entitlement checks do not each re-read the
    # same document. inject_user is the only place that reads it.
    user["profile"] = profile
    return user


async def inject_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Like inject_user but also asserts the caller has admin role."""
    user = await inject_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    """Health check endpoint — no auth required."""
    return {"status": "ok"}


@app.get("/api/plans")
async def list_plans():
    """Plan tiers for the pricing page — no auth required.

    `billing_enabled` tells the client whether an upgrade button can do
    anything, so a self-hosted deployment shows the tiers without offering a
    checkout that would fail.
    """
    return {"plans": public_plans(), "billing_enabled": billing.is_configured()}


@app.get("/api/me/usage")
async def my_usage(authorization: Optional[str] = Header(None)):
    """Current plan, quota consumption, and entitlements for the caller."""
    user = await inject_user(authorization)
    profile = user["profile"]
    plan = plan_for(profile)
    quota = check_quota(profile)

    return {
        "plan": plan["name"],
        "plan_label": plan["label"],
        "used": quota["used"],
        "limit": quota["limit"],
        "remaining": quota["remaining"],
        "period": current_period(),
        "validation": plan["validation"],
        "max_portfolio_size": plan["max_portfolio_size"],
        "billing_enabled": billing.is_configured(),
    }


@app.post("/api/billing/checkout")
async def create_checkout(authorization: Optional[str] = Header(None)):
    """Start a Stripe Checkout session and return the URL to redirect to."""
    user = await inject_user(authorization)

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

    db = get_db()
    ref = db.collection("users").document(uid)
    if not ref.get().exists:
        log.warning("webhook referenced an unknown user", extra={"uid": uid})
        return {"received": True, "applied": False}

    ref.update({"plan": new_plan})
    log.info(
        "plan updated from stripe",
        extra={"uid": uid, "plan": new_plan, "event": event.get("type")},
    )
    return {"received": True, "applied": True}


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
async def run_backtest(req: BacktestRequest, authorization: Optional[str] = Header(None)):
    """Run a backtest for the selected strategy and persist results to Firestore."""
    user = await inject_user(authorization)
    uid = user["uid"]
    email = user["email"]
    _enforce(backtest_limiter, uid, "backtests")
    _enforce_quota(user)

    start_time = time.time()

    # 1. Fetch data — a bad ticker or an empty range is the user's mistake, so
    # surface it as a 400 with the underlying reason rather than a 500.
    try:
        df = fetch_ohlcv(req.ticker, req.start, req.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    db.collection("runs").document(run_id).set(run_doc)
    _record_run(db, uid, user["profile"])

    return {
        "runId": run_id,
        "metrics": metrics,
        "equity_curve": equity_curve_data,
        "drawdown": drawdown_data,
        "trades": trades,
        "monthly_returns": monthly,
        "annual_returns": annual,
        "rolling_sharpe": rolling,
        "signals_summary": signals_summary,
        "duration_ms": duration_ms,
    }


@app.post("/api/validate")
async def validate_strategy(req: ValidateRequest, authorization: Optional[str] = Header(None)):
    """Run the two overfitting checks a single backtest cannot answer.

    Walk-forward asks whether parameters survive on data they were not chosen on.
    The permutation test asks whether signal timing beats random timing at the
    same market exposure. Results are diagnostic and not persisted.
    """
    user = await inject_user(authorization)
    # Tighter than the backtest budget: a validation run rebuilds positions once
    # per grid combination and then again for every permutation trial, so one
    # call is worth hundreds of backtests in CPU terms.
    _enforce(validate_limiter, user["uid"], "validation runs")
    if not may_validate(user["profile"]):
        raise HTTPException(
            status_code=402,
            detail=(
                "Walk-forward validation and the permutation test are Pro features. "
                "Each run sweeps a parameter grid and then reshuffles the signals "
                "hundreds of times, so they cost far more than a single backtest."
            ),
        )
    _enforce_quota(user)

    start_time = time.time()

    try:
        df = fetch_ohlcv(req.ticker, req.start, req.end)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
        "permutation": permutation,
        "duration_ms": int((time.time() - start_time) * 1000),
    }


@app.post("/api/portfolio")
async def run_portfolio(req: PortfolioRequest, authorization: Optional[str] = Header(None)):
    """Run one strategy across several tickers and combine the legs.

    Each leg is a complete backtest — its own signals, stops, sizing, and
    transaction costs — so the portfolio is an aggregation of honest single
    results rather than a separate model with its own assumptions.
    """
    user = await inject_user(authorization)
    uid = user["uid"]
    # One request is N data fetches and N full backtests, so it costs a slot
    # per leg rather than a single one.
    for _ in req.tickers:
        _enforce(backtest_limiter, uid, "portfolio legs")
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

    # 1. Fetch every leg before computing anything — one bad ticker should fail
    # the request outright rather than silently yielding a smaller portfolio
    # than the user asked for.
    closes = {}
    for symbol in req.tickers:
        try:
            closes[symbol] = fetch_ohlcv(symbol, req.start, req.end)["Close"]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"{symbol}: {exc}") from exc

    # 2. Align on shared trading days.
    try:
        aligned = align_closes(closes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # How much history the inner join actually cost, measured against the leg
    # with the longest record rather than against the requested start date.
    # Comparing to the request would flag every run whose start landed on a
    # weekend or a holiday, and a warning that fires constantly gets ignored.
    longest_ticker = max(closes, key=lambda t: len(closes[t]))
    dropped_bars = len(closes[longest_ticker]) - len(aligned)
    limiting_ticker = min(closes, key=lambda t: len(closes[t])) if dropped_bars else None

    if len(aligned) < req.warmup_bars() + 2:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only {len(aligned)} trading days are shared by all "
                f"{len(req.tickers)} tickers — not enough for the chosen "
                "indicator and weighting windows."
            ),
        )

    # 3. Run each leg exactly as a single-ticker backtest would.
    leg_returns = {}
    leg_metrics = {}
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
        leg_metrics[symbol] = compute_metrics(
            leg_net,
            out["equity_curve"].fillna(1),
            out["drawdown"].fillna(0),
            out["position"],
        )

    legs_frame = pd.DataFrame(leg_returns)

    # 4. Weight and combine.
    if req.weighting == "inverse_vol":
        # Weights follow the *assets'* volatility, not the strategy's, so a leg
        # that happens to sit flat does not get an unbounded weight.
        asset_returns = aligned.pct_change().fillna(0.0)
        try:
            weights = inverse_vol_weights(
                asset_returns, window=req.weight_window, max_weight=req.max_weight
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        weights = equal_weights(list(legs_frame.columns), legs_frame.index)

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
        "duration_ms": int((time.time() - start_time) * 1000),
    }


@app.post("/api/compare")
async def compare_runs(req: CompareRequest, authorization: Optional[str] = Header(None)):
    """Recompute several stored runs so their equity curves can be overlaid.

    Equity curves are deliberately not persisted — they are a few thousand floats
    per run and derivable from the config, so Firestore stores the config and we
    rebuild the curve here. That keeps documents small and means a fix to the
    engine retroactively corrects every historical chart.
    """
    user = await inject_user(authorization)
    uid = user["uid"]
    # Each id costs a data fetch plus a full recompute, so this shares the
    # backtest budget rather than getting a free pass.
    _enforce(backtest_limiter, uid, "comparisons")

    start_time = time.time()
    db = get_db()

    series = []
    for run_id in req.run_ids:
        doc = db.collection("runs").document(run_id).get()
        if not doc.exists:
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
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """Return paginated backtest history for the authenticated user."""
    user = await inject_user(authorization)
    uid = user["uid"]

    db = get_db()
    query = (
        db.collection("runs")
        .where("uid", "==", uid)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
    )
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
async def get_run(run_id: str, authorization: Optional[str] = Header(None)):
    """Fetch a single run by ID — only the owner or an admin may access it."""
    user = await inject_user(authorization)
    uid = user["uid"]

    db = get_db()
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
async def admin_stats(authorization: Optional[str] = Header(None)):
    """Return platform-wide statistics — admin only."""
    await inject_admin(authorization)

    db = get_db()
    users_docs = list(db.collection("users").stream())
    runs_docs = list(db.collection("runs").stream())

    total_users = len(users_docs)
    total_runs = len(runs_docs)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    runs_today = 0
    runs_this_week = 0
    ticker_counts: dict = {}
    sharpe_sum = 0.0
    return_sum = 0.0

    for doc in runs_docs:
        d = doc.to_dict()
        created = d.get("createdAt")
        if created:
            # Firestore timestamps are datetime-like objects
            if hasattr(created, "timestamp"):
                ts = datetime.fromtimestamp(created.timestamp(), tz=timezone.utc)
            else:
                ts = created
            if ts >= today_start:
                runs_today += 1
            if ts >= week_start:
                runs_this_week += 1

        ticker = d.get("ticker", "")
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        m = d.get("metrics", {})
        sharpe_sum += m.get("sharpe_ratio", 0) or 0
        return_sum += m.get("total_return", 0) or 0

    top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    avg_sharpe = round(sharpe_sum / total_runs, 4) if total_runs else 0.0
    avg_total_return = round(return_sum / total_runs, 4) if total_runs else 0.0

    return {
        "total_users": total_users,
        "total_runs": total_runs,
        "runs_today": runs_today,
        "runs_this_week": runs_this_week,
        "top_tickers": [{"ticker": t, "count": c} for t, c in top_tickers],
        "avg_sharpe": avg_sharpe,
        "avg_total_return": avg_total_return,
    }


@app.get("/api/admin/users")
async def admin_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Return paginated user list — admin only."""
    await inject_admin(authorization)

    db = get_db()
    all_docs = list(
        db.collection("users")
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .stream()
    )

    if search:
        all_docs = [d for d in all_docs if search.lower() in (d.to_dict().get("email", "").lower())]

    total = len(all_docs)
    page = all_docs[offset: offset + limit]
    users = [d.to_dict() for d in page]

    return {"users": users, "total": total}


@app.patch("/api/admin/users/{target_uid}")
async def admin_patch_user(
    target_uid: str,
    patch: UserPatch,
    authorization: Optional[str] = Header(None),
):
    """Update isActive or role on a user document — admin only."""
    await inject_admin(authorization)

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

    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    ref.update(update_data)
    return ref.get().to_dict()


@app.get("/api/admin/runs")
async def admin_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    uid: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Return paginated run list with optional filters — admin only."""
    await inject_admin(authorization)

    db = get_db()
    query = db.collection("runs").order_by("createdAt", direction=firestore.Query.DESCENDING)
    if uid:
        query = query.where("uid", "==", uid)
    if ticker:
        query = query.where("ticker", "==", ticker.upper())

    all_docs = list(query.stream())
    total = len(all_docs)
    page = all_docs[offset: offset + limit]
    runs = [d.to_dict() for d in page]

    return {"runs": runs, "total": total}
