"""Stripe checkout and webhook handling.

Everything here is optional. With no `STRIPE_SECRET_KEY` set, `is_configured()`
returns False and the app runs exactly as before — the pricing page still
renders, the upgrade button explains that billing is not enabled, and no import
of the Stripe SDK is attempted. That keeps local development, CI, and anyone
self-hosting from needing a Stripe account to run the project at all.

The webhook signature check is implemented here rather than taken from the SDK
so it stays testable without the dependency installed, and so the constant-time
comparison and the replay window are visible rather than assumed.
"""

import hashlib
import hmac
import os
import time

# Stripe sends this many seconds of tolerance by convention. Anything older is
# rejected so a captured request cannot be replayed indefinitely.
SIGNATURE_TOLERANCE_SECONDS = 300


def is_configured() -> bool:
    """Whether billing is switched on for this deployment."""
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def price_id() -> str | None:
    return os.environ.get("STRIPE_PRICE_ID")


def webhook_secret() -> str | None:
    return os.environ.get("STRIPE_WEBHOOK_SECRET")


def parse_signature_header(header: str) -> tuple[int | None, list[str]]:
    """Pull the timestamp and v1 signatures out of a Stripe-Signature header.

    The header looks like `t=1614556800,v1=abc...,v1=def...`. Multiple v1
    entries appear while a webhook secret is being rotated, and both must be
    accepted or the rotation drops events.
    """
    timestamp = None
    signatures = []
    for part in (header or "").split(","):
        key, _, value = part.strip().partition("=")
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                timestamp = None
        elif key == "v1":
            signatures.append(value)
    return timestamp, signatures


def verify_signature(
    payload: bytes,
    header: str,
    secret: str,
    now: float | None = None,
    tolerance: int = SIGNATURE_TOLERANCE_SECONDS,
) -> bool:
    """Check a Stripe webhook signature.

    Without this, anyone who learns the webhook URL could POST a
    `checkout.session.completed` and upgrade themselves for free — the endpoint
    is necessarily unauthenticated, so the signature *is* the authentication.
    """
    if not secret or not header or not payload:
        return False

    timestamp, signatures = parse_signature_header(header)
    if timestamp is None or not signatures:
        return False

    now = time.time() if now is None else now
    if abs(now - timestamp) > tolerance:
        return False

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    # compare_digest, not ==, so the comparison does not leak how many leading
    # characters matched.
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


def plan_from_event(event: dict) -> tuple[str | None, str | None]:
    """Map a Stripe event onto (uid, new_plan), or (None, None) to ignore it.

    Only the events that actually change entitlement are handled. Anything else
    is acknowledged and ignored — returning an error for unrecognised events
    makes Stripe retry them forever.
    """
    event_type = event.get("type")
    obj = (event.get("data") or {}).get("object") or {}

    # The uid is put into metadata when the checkout session is created; it is
    # the only link back from a Stripe customer to an application user.
    uid = (obj.get("metadata") or {}).get("uid")
    if not uid:
        return None, None

    if event_type == "checkout.session.completed":
        return uid, "pro"

    if event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        return uid, "free"

    if event_type == "customer.subscription.updated":
        # `status` covers cancellation at period end, failed payments, and
        # reactivation in one place.
        active = obj.get("status") in ("active", "trialing")
        return uid, "pro" if active else "free"

    return None, None


def create_checkout_session(uid: str, email: str, success_url: str, cancel_url: str) -> str:
    """Create a Stripe Checkout session and return its URL.

    Imported lazily so the SDK is only a dependency for deployments that
    actually enable billing.
    """
    if not is_configured():
        raise RuntimeError("Billing is not enabled on this deployment")
    if not price_id():
        raise RuntimeError("STRIPE_PRICE_ID is not set")

    try:
        import stripe  # noqa: PLC0415 — deliberate lazy import
    except ImportError as exc:
        raise RuntimeError(
            "STRIPE_SECRET_KEY is set but the stripe package is not installed. "
            "Run `pip install stripe`, or unset the key to run without billing."
        ) from exc

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id(), "quantity": 1}],
        customer_email=email,
        success_url=success_url,
        cancel_url=cancel_url,
        # Carried through to every subscription event for this customer, which
        # is what lets the webhook find the user again.
        metadata={"uid": uid},
        subscription_data={"metadata": {"uid": uid}},
    )
    return session.url
