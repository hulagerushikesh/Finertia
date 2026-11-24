"""Checkout and the payment provider's webhook."""

import json
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from starlette.concurrency import run_in_threadpool

import billing
from api import core
from api.core import (
    ALLOWED_ORIGINS,
    inject_user,
    log,
)

router = APIRouter()


@router.post("/billing/checkout")
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


@router.post("/billing/webhook")
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
    db = core.get_db()
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

