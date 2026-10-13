"""Error reporting to Sentry, with the data that leaves the server kept small.

Off unless SENTRY_DSN is set, and always off against the Firebase emulators, so
tests, dev machines and the E2E suite never report.

What a report carries: the exception, its stack trace (code lines only — not
local variables, which could hold a token or a user's settings), the route,
the request id (to find the matching log line), the Cloud Run revision as the
release, and the user's Firebase uid. What it does not:

- no personal data — `send_default_pii=False`, so no IP address, cookies or
  user email; the uid is the only user field and it is opaque;
- no request body (a backtest's settings are the user's work, not ours to
  ship to a third party), and no query string (admin search puts an email
  address there);
- no Authorization header, even though the SDK's own scrubber would also
  remove it — the token is the one thing that must never leave;
- no performance tracing or profiling: errors only.
"""

import logging
import os

log = logging.getLogger("finertia")

# Request headers that may travel with an error. Everything else is dropped,
# rather than trying to list what to remove.
_KEEP_HEADERS = {"content-type", "user-agent", "x-request-id", "origin"}


def scrub(event: dict, hint: dict | None = None) -> dict:
    """before_send: trim the request down to what helps debug it."""
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers") or {}
        request["headers"] = {k: v for k, v in headers.items() if k.lower() in _KEEP_HEADERS}
        for key in ("data", "query_string", "cookies", "env"):
            request.pop(key, None)
        url = request.get("url")
        if isinstance(url, str):
            request["url"] = url.split("?", 1)[0]
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if user.get("id") else {}
    return event


def init_sentry(emulator: bool = False, transport=None) -> bool:
    """Start the SDK if configured. Returns whether it is on.

    `transport` is for tests: it receives what would have been sent.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn or emulator:
        return False

    import sentry_sdk  # noqa: PLC0415 — only imported when it will be used

    on_cloud_run = bool(os.environ.get("K_SERVICE"))
    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=False,
        traces_sample_rate=0.0,
        max_request_body_size="never",
        include_local_variables=False,
        environment=os.environ.get("SENTRY_ENVIRONMENT") or ("production" if on_cloud_run else "development"),
        # K_REVISION is set by Cloud Run (finertia-api-00020-abc), so an error
        # names the deploy it came from without any build step.
        release=os.environ.get("K_REVISION") or None,
        before_send=scrub,
        **({"transport": transport} if transport else {}),
    )
    log.info("sentry on", extra={"environment": "production" if on_cloud_run else "development"})
    return True


def tag_request(request_id: str) -> None:
    """Attach the request id so a Sentry issue and a log line can be matched."""
    try:
        import sentry_sdk  # noqa: PLC0415

        sentry_sdk.set_tag("request_id", request_id)
    except ImportError:
        pass


def set_user(uid: str) -> None:
    """Identify the caller by uid only — never email or IP."""
    try:
        import sentry_sdk  # noqa: PLC0415

        sentry_sdk.set_user({"id": uid})
    except ImportError:
        pass
