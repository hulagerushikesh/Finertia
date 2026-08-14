"""Structured JSON logging.

Cloud Run collects stdout and parses each line as JSON when it looks like JSON.
The keys `severity` and `message` are the ones Cloud Logging understands, so
using them means log levels and the message body render correctly in the console
instead of arriving as one opaque text blob. Everything else on the record is
passed through so a log line can carry the request id, route, and timing.

Local dev gets the same JSON. One format everywhere beats a pretty local format
that hides what production will actually emit.
"""

import json
import logging
import os
import sys

# Attributes LogRecord always carries — anything outside this set was attached
# by the caller via `extra=` and belongs in the output.
_STANDARD_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "taskName", "thread", "threadName",
}

# Python level names -> the severity strings Cloud Logging recognises.
_SEVERITY = {
    "DEBUG": "DEBUG",
    "INFO": "INFO",
    "WARNING": "WARNING",
    "ERROR": "ERROR",
    "CRITICAL": "CRITICAL",
}


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "severity": _SEVERITY.get(record.levelname, record.levelname),
            "message": record.getMessage(),
            "logger": record.name,
        }

        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            # The traceback goes on the same line so it stays one log entry
            # rather than fragmenting into one entry per stack frame.
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_sentry() -> bool:
    """Enable Sentry error tracking if a DSN is configured.

    Optional, like billing: with no `SENTRY_DSN` this is a no-op and the SDK is
    never imported, so neither local development nor CI needs an account. The
    structured logs already carry a request id and a full traceback; Sentry adds
    grouping and alerting on top, which is a production concern rather than a
    correctness one.

    Returns whether it was switched on, so startup can say so out loud.
    """
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return False

    try:
        import sentry_sdk  # noqa: PLC0415 — deliberate lazy import
    except ImportError:
        logging.getLogger("finertia").warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; "
            "run `pip install sentry-sdk` or unset the variable"
        )
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        # A backtesting API handles no personal data beyond an email, and
        # sending request bodies would ship users' strategy parameters to a
        # third party. Neither belongs in an error tracker.
        send_default_pii=False,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
    )
    return True


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Install the JSON formatter on the root logger and return the app logger.

    Existing handlers are cleared first because uvicorn installs its own, and
    leaving them attached would print every line twice — once as JSON and once
    as uvicorn's plain text.
    """
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())

    # uvicorn.access duplicates our own request log with less detail.
    logging.getLogger("uvicorn.access").disabled = True
    for noisy in ("uvicorn", "uvicorn.error"):
        logging.getLogger(noisy).handlers.clear()
        logging.getLogger(noisy).propagate = True

    return logging.getLogger("finertia")
