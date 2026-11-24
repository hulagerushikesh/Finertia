"""Admin-only routes."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from admin_queries import list_runs, list_users
from api import core
from api.core import (
    inject_admin,
)
from plans import PLAN_NAMES
from schemas import UserPatch
from timing import step

router = APIRouter()


@router.get("/admin/stats")
def admin_stats(authorization: Optional[str] = Header(None)):
    """Return platform-wide statistics — admin only."""
    inject_admin(authorization)
    with step("admin_query"):
        return core.platform_stats(core.get_db())


@router.get("/admin/users")
def admin_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Return paginated user list — admin only."""
    inject_admin(authorization)
    with step("admin_query"):
        return list_users(core.get_db(), limit, offset, search)


@router.patch("/admin/users/{target_uid}")
def admin_patch_user(
    target_uid: str,
    patch: UserPatch,
    authorization: Optional[str] = Header(None),
):
    """Update isActive, role or plan on a user document — admin only.

    A plan set here is stamped `planSource: "admin"` so a comped Pro account is
    never counted as a paying one; the Stripe webhook stamps "stripe".
    """
    inject_admin(authorization)

    db = core.get_db()
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
    if patch.plan is not None:
        if patch.plan not in PLAN_NAMES:
            raise HTTPException(status_code=400, detail=f"plan must be one of {', '.join(PLAN_NAMES)}")
        update_data["plan"] = patch.plan
        update_data["planSource"] = "admin"

    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    ref.update(update_data)
    return ref.get().to_dict()


@router.get("/admin/runs")
def admin_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    uid: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Return paginated run list with optional filters — admin only."""
    inject_admin(authorization)
    with step("admin_query"):
        return list_runs(core.get_db(), limit, offset, uid, ticker)


class SentryTestError(RuntimeError):
    """Raised on purpose by /api/admin/sentry-test."""


@router.post("/admin/sentry-test")
def admin_sentry_test(authorization: Optional[str] = Header(None)):
    """Raise an error on purpose to prove reporting works end to end — admin only.

    Comes back as an ordinary 500 with a request id; the matching issue should
    appear in Sentry within a minute, tagged with the same id.
    """
    inject_admin(authorization)
    raise SentryTestError("Deliberate test error from /api/admin/sentry-test")
