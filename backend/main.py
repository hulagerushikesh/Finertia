"""FastAPI application: assembles the API from its domain modules.

The routes live in api/routes/ (one module per domain), shared runtime in
api/core.py (configuration, rate limits, quotas, auth) and the simulation steps
several routes share in api/simulation.py. This file only creates the app,
adds the middleware and mounts the routers.

Every router is mounted twice: under /api/v1, the versioned contract the
OpenAPI schema describes, and under /api, the original paths, kept for the
current front end and for links already shared. Both reach the same handler.
"""

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from api import core
from api.core import ALLOWED_ORIGIN_REGEX, ALLOWED_ORIGINS, backtest_limiter, client_ip, ip_limiter, log, validate_limiter
from api.routes import admin, backtests, compare, me, meta, payments, portfolios, runs, sharing, validations
import billing
from logging_config import configure_sentry
from monitoring import init_sentry, tag_request
import timing

# Before the app exists, so the SDK's FastAPI integration sees it created.
init_sentry(emulator=core.EMULATOR)

# Optional integrations, announced at startup so a misconfigured deployment is
# visible in the first log line rather than discovered when something breaks.
log.info(
    "starting",
    extra={
        "sentry": configure_sentry(),
        "billing": billing.is_configured(),
        "allowed_origins": ",".join(ALLOWED_ORIGINS),
    },
)

app = FastAPI(title="Finertia API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# A backtest is ~420 KB of JSON and ~70 KB gzipped; nothing between here
# and the browser compressed it. Below 1 KB compression is not worth the CPU.
# Level 6, not Starlette's default 9: measured 27 Nov on a 10-year backtest,
# 9 took 25 ms for 68 KB, 6 takes 6 ms for 74 KB. On one vCPU, 19 ms a
# request is worth more than 6 KB on the wire (scripts/load_test.py).
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

# Paths that only ever read tiny documents and are polled by the UI — holding
# them to the same budget as a backtest would break normal navigation.
_RATE_LIMIT_EXEMPT = {"/api/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc"}

_requests_seen = 0
_PRUNE_EVERY = 500


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
        verdict = ip_limiter.check(client_ip(request))
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


# Routes that touch Firestore, the price provider or the engine are plain
# `def`, not `async def`. Every one of those calls blocks, and in an
# `async def` it blocks the event loop: the instance then serves one request
# at a time, health checks included, while it waits on a database a quarter
# of a second away. FastAPI runs a plain `def` route in a worker thread, so
# one request's wait no longer holds up the rest. Only routes that never block
# stay `async` (tests/test_routes.py checks the list).
#
# Order matters only where two paths could match the same URL: sharing's
# /share/card.png is a literal path and no other router has /share/{x}.
ROUTERS = (meta, me, payments, backtests, sharing, validations, portfolios, compare, runs, admin)
for module in ROUTERS:
    app.include_router(module.router, prefix="/api/v1")
for module in ROUTERS:
    app.include_router(module.router, prefix="/api", include_in_schema=False)
