"""Per-request step timings (timing.py)."""

import time

import timing
from timing import step


def test_step_is_free_outside_a_request():
    # No collector open: nothing is recorded and nothing raises.
    timing._current.set(None)
    with step("profile"):
        pass
    assert timing._current.get() is None


def test_repeated_steps_add_up_and_count():
    steps = timing.begin()
    with step("prices_read"):
        time.sleep(0.002)
    with step("prices_read"):
        time.sleep(0.002)
    with step("auth"):
        pass
    ms, n = steps["prices_read"]
    assert n == 2 and ms >= 4
    assert steps["auth"][1] == 1


def test_a_step_that_raises_is_still_recorded():
    steps = timing.begin()
    try:
        with step("run_write"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert steps["run_write"][1] == 1


def test_log_fields_list_counts_only_for_repeats():
    fields = timing.as_log_fields({"auth": [1.234, 1], "prices_read": [10.0, 3]})
    assert fields["timings_ms"] == {"auth": 1.2, "prices_read": 10.0}
    assert fields["timing_counts"] == {"prices_read": 3}
    assert "timing_counts" not in timing.as_log_fields({"auth": [1.0, 1]})


def test_server_timing_header_has_steps_other_and_total():
    header = timing.server_timing({"profile": [250.0, 1], "prices_read": [100.0, 2]}, 400.0)
    assert header == (
        'profile;dur=250.0, prices_read;dur=100.0;desc="x2", other;dur=50.0, total;dur=400.0'
    )


def test_other_never_goes_negative():
    assert "other;dur=0.0" in timing.server_timing({"auth": [10.0, 1]}, 9.0)
