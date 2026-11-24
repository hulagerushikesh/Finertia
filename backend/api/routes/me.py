"""The signed-in user's own account: usage, export, deletion."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

import billing
from api import core
from api.core import (
    inject_user,
    log,
)
from plans import (
    check_quota,
    check_validation_quota,
    plan_for,
)
from schemas import DeleteAccountRequest
from timing import step

router = APIRouter()


@router.get("/me/usage")
def my_usage(authorization: Optional[str] = Header(None)):
    """Current plan, quota consumption, and entitlements for the caller."""
    user = inject_user(authorization)
    profile = user["profile"]
    plan = plan_for(profile)
    quota = check_quota(profile)
    validations = check_validation_quota(profile, core.FREE_VALIDATIONS_PER_MONTH)

    return {
        "plan": plan["name"],
        "plan_label": plan["label"],
        "used": quota["used"],
        "limit": quota["limit"],
        "remaining": quota["remaining"],
        "period": core.current_period(),
        "validation": plan["validation"],
        # The free plan's monthly validations; limit and remaining are None
        # on Pro, and limit is 0 while the free allowance is switched off.
        "validations_used": validations["used"],
        "validations_limit": validations["limit"],
        "validations_remaining": validations["remaining"],
        "max_portfolio_size": plan["max_portfolio_size"],
        "billing_enabled": billing.is_configured(),
    }


@router.get("/me/export")
def export_my_data(authorization: Optional[str] = Header(None)):
    """Everything stored about the caller, as a JSON download (DPDP: access)."""
    user = inject_user(authorization)
    with step("export_read"):
        body = core.export_account(core.get_db(), user["uid"], user["email"])
    stamp = body["exported_at"][:10]
    log.info("account exported", extra={"uid": user["uid"], "runs": len(body["runs"])})
    return JSONResponse(
        jsonable_encoder(body),
        headers={"Content-Disposition": f'attachment; filename="finertia-export-{stamp}.json"'},
    )


@router.delete("/me")
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
        counts = core.delete_account(core.get_db(), user["uid"], core.delete_auth_user)
    log.info("account deleted", extra={"uid": user["uid"], **counts})
    return {"deleted": True, **counts}

