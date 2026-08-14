"""Structured logging tests.

The formatter is exercised directly on LogRecord objects rather than by
capturing stdout, so the assertions are about the JSON contract Cloud Logging
depends on, not about handler plumbing.
"""

import json
import logging

import pytest

from logging_config import JsonFormatter, configure_logging


def record(level=logging.INFO, msg="hello", args=(), **extra):
    """Build a LogRecord the way logging.Logger._log would."""
    rec = logging.LogRecord(
        name="finertia", level=level, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )
    for key, value in extra.items():
        setattr(rec, key, value)
    return rec


class TestJsonShape:
    def test_output_is_a_single_line(self):
        out = JsonFormatter().format(record())
        assert "\n" not in out

    def test_output_parses_as_json(self):
        parsed = json.loads(JsonFormatter().format(record()))
        assert parsed["message"] == "hello"

    def test_carries_the_logger_name(self):
        parsed = json.loads(JsonFormatter().format(record()))
        assert parsed["logger"] == "finertia"

    def test_interpolates_message_args(self):
        parsed = json.loads(JsonFormatter().format(record(msg="run %s took %dms", args=("abc", 42))))
        assert parsed["message"] == "run abc took 42ms"


class TestSeverity:
    @pytest.mark.parametrize(
        "level,expected",
        [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ],
    )
    def test_maps_level_to_the_severity_key_cloud_logging_reads(self, level, expected):
        parsed = json.loads(JsonFormatter().format(record(level=level)))
        assert parsed["severity"] == expected


class TestExtraFields:
    def test_extra_fields_are_promoted_to_top_level_keys(self):
        parsed = json.loads(
            JsonFormatter().format(record(request_id="abc123", duration_ms=17, path="/api/backtest"))
        )
        assert parsed["request_id"] == "abc123"
        assert parsed["duration_ms"] == 17
        assert parsed["path"] == "/api/backtest"

    def test_standard_record_attributes_are_not_dumped_into_the_payload(self):
        # Without the filter every line would carry pathname, thread ids, and
        # relativeCreated — noise that makes the logs harder to read, not easier.
        parsed = json.loads(JsonFormatter().format(record()))
        for noisy in ("pathname", "lineno", "threadName", "relativeCreated", "msecs"):
            assert noisy not in parsed

    def test_non_serialisable_values_do_not_break_the_line(self):
        class Opaque:
            def __repr__(self):
                return "<opaque>"

        parsed = json.loads(JsonFormatter().format(record(payload=Opaque())))
        assert parsed["payload"] == "<opaque>"


class TestExceptions:
    def test_traceback_is_attached_to_the_same_entry(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            rec = record(level=logging.ERROR, msg="failed")
            rec.exc_info = sys.exc_info()
            parsed = json.loads(JsonFormatter().format(rec))

        assert "ValueError: boom" in parsed["exception"]
        assert parsed["severity"] == "ERROR"

    def test_traceback_stays_on_one_line(self):
        try:
            raise RuntimeError("nested")
        except RuntimeError:
            import sys
            rec = record(level=logging.ERROR)
            rec.exc_info = sys.exc_info()
            out = JsonFormatter().format(rec)

        assert out.count("\n") == 0


class TestConfigure:
    def test_installs_exactly_one_handler(self):
        configure_logging()
        try:
            assert len(logging.getLogger().handlers) == 1
        finally:
            logging.getLogger().handlers.clear()

    def test_repeated_calls_do_not_stack_handlers(self):
        # Duplicated handlers would print every log line twice.
        configure_logging()
        configure_logging()
        try:
            assert len(logging.getLogger().handlers) == 1
        finally:
            logging.getLogger().handlers.clear()

    def test_honours_the_requested_level(self):
        configure_logging("WARNING")
        try:
            assert logging.getLogger().level == logging.WARNING
        finally:
            logging.getLogger().handlers.clear()
            logging.getLogger().setLevel(logging.NOTSET)

    def test_disables_the_duplicate_uvicorn_access_log(self):
        configure_logging()
        try:
            assert logging.getLogger("uvicorn.access").disabled is True
        finally:
            logging.getLogger().handlers.clear()

    def test_returns_the_app_logger(self):
        logger = configure_logging()
        try:
            assert logger.name == "finertia"
        finally:
            logging.getLogger().handlers.clear()
