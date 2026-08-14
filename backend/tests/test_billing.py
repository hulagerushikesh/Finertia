"""Stripe webhook verification and event mapping.

The signature check is the authentication for an endpoint that is necessarily
unauthenticated, so it gets the most attention here.
"""

import hashlib
import hmac
import os

import pytest

from billing import (
    is_configured,
    parse_signature_header,
    verify_signature,
    plan_from_event,
    create_checkout_session,
)

SECRET = "whsec_test_secret"
PAYLOAD = b'{"type":"checkout.session.completed"}'
NOW = 1_700_000_000


def sign(payload=PAYLOAD, secret=SECRET, timestamp=NOW):
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("STRIPE_SECRET_KEY", "STRIPE_PRICE_ID", "STRIPE_WEBHOOK_SECRET"):
        monkeypatch.delenv(key, raising=False)


class TestConfiguration:
    def test_billing_is_off_without_a_key(self):
        assert is_configured() is False

    def test_billing_is_on_with_a_key(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
        assert is_configured() is True

    def test_checkout_refuses_when_billing_is_off(self):
        with pytest.raises(RuntimeError, match="not enabled"):
            create_checkout_session("u1", "a@b.c", "https://s", "https://c")

    def test_checkout_refuses_without_a_price(self, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")
        with pytest.raises(RuntimeError, match="STRIPE_PRICE_ID"):
            create_checkout_session("u1", "a@b.c", "https://s", "https://c")


class TestSignatureHeader:
    def test_parses_timestamp_and_signature(self):
        ts, sigs = parse_signature_header("t=123,v1=abc")
        assert ts == 123 and sigs == ["abc"]

    def test_keeps_every_v1_entry(self):
        # Multiple signatures appear during secret rotation; dropping one would
        # silently lose events for the duration of the rotation.
        _, sigs = parse_signature_header("t=1,v1=aaa,v1=bbb")
        assert sigs == ["aaa", "bbb"]

    def test_ignores_unknown_schemes(self):
        ts, sigs = parse_signature_header("t=1,v0=legacy,v1=aaa")
        assert ts == 1 and sigs == ["aaa"]

    def test_tolerates_spaces(self):
        ts, sigs = parse_signature_header(" t=5 , v1=zzz ")
        assert ts == 5 and sigs == ["zzz"]

    @pytest.mark.parametrize("header", ["", "garbage", "t=notanumber,v1=a"])
    def test_malformed_headers_yield_no_timestamp(self, header):
        ts, _ = parse_signature_header(header)
        assert ts is None


class TestVerifySignature:
    def test_accepts_a_correct_signature(self):
        assert verify_signature(PAYLOAD, sign(), SECRET, now=NOW) is True

    def test_accepts_when_one_of_several_signatures_matches(self):
        header = sign() + ",v1=" + "0" * 64
        assert verify_signature(PAYLOAD, header, SECRET, now=NOW) is True

    def test_rejects_the_wrong_secret(self):
        assert verify_signature(PAYLOAD, sign(), "whsec_other", now=NOW) is False

    def test_rejects_a_tampered_payload(self):
        # The exact attack this exists to stop: a forged upgrade event.
        header = sign()
        forged = b'{"type":"checkout.session.completed","amount":0}'
        assert verify_signature(forged, header, SECRET, now=NOW) is False

    def test_rejects_a_stale_timestamp(self):
        assert verify_signature(PAYLOAD, sign(timestamp=NOW - 3600), SECRET, now=NOW) is False

    def test_rejects_a_timestamp_from_the_future(self):
        assert verify_signature(PAYLOAD, sign(timestamp=NOW + 3600), SECRET, now=NOW) is False

    def test_accepts_inside_the_tolerance_window(self):
        assert verify_signature(PAYLOAD, sign(timestamp=NOW - 60), SECRET, now=NOW) is True

    def test_replay_is_refused_once_the_window_passes(self):
        header = sign(timestamp=NOW)
        assert verify_signature(PAYLOAD, header, SECRET, now=NOW) is True
        assert verify_signature(PAYLOAD, header, SECRET, now=NOW + 3600) is False

    @pytest.mark.parametrize("secret,header,payload", [
        ("", sign(), PAYLOAD),
        (SECRET, "", PAYLOAD),
        (SECRET, sign(), b""),
    ])
    def test_missing_inputs_are_refused(self, secret, header, payload):
        assert verify_signature(payload, header, secret) is False

    def test_a_signature_with_no_v1_entry_is_refused(self):
        assert verify_signature(PAYLOAD, f"t={NOW}", SECRET, now=NOW) is False


class TestEventMapping:
    def event(self, type_, uid="user-1", **obj):
        return {"type": type_, "data": {"object": {"metadata": {"uid": uid} if uid else {}, **obj}}}

    def test_completed_checkout_grants_pro(self):
        assert plan_from_event(self.event("checkout.session.completed")) == ("user-1", "pro")

    def test_deleted_subscription_returns_to_free(self):
        assert plan_from_event(self.event("customer.subscription.deleted")) == ("user-1", "free")

    def test_paused_subscription_returns_to_free(self):
        assert plan_from_event(self.event("customer.subscription.paused")) == ("user-1", "free")

    @pytest.mark.parametrize("status", ["active", "trialing"])
    def test_an_active_update_keeps_pro(self, status):
        assert plan_from_event(
            self.event("customer.subscription.updated", status=status)
        ) == ("user-1", "pro")

    @pytest.mark.parametrize("status", ["past_due", "canceled", "unpaid", "incomplete_expired"])
    def test_a_lapsed_update_drops_to_free(self, status):
        assert plan_from_event(
            self.event("customer.subscription.updated", status=status)
        ) == ("user-1", "free")

    def test_an_event_without_a_uid_is_ignored(self):
        # Nothing links it back to an account, so acting on it is impossible.
        assert plan_from_event(self.event("checkout.session.completed", uid=None)) == (None, None)

    def test_unrelated_events_are_ignored(self):
        # Erroring on these would make Stripe retry them indefinitely.
        assert plan_from_event(self.event("invoice.created")) == (None, None)

    def test_a_malformed_event_does_not_raise(self):
        assert plan_from_event({}) == (None, None)
        assert plan_from_event({"type": "checkout.session.completed"}) == (None, None)
