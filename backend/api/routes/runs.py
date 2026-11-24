"""A user's run history."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from api import core
from api.core import (
    in_parallel,
    inject_user,
)
from history import history_page
from timing import step

router = APIRouter()


@router.get("/history")
def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """Return paginated backtest history for the authenticated user."""
    user = inject_user(authorization)
    uid = user["uid"]

    with step("history_read"):
        return history_page(core.get_db(), uid, limit, offset, run=in_parallel)


@router.get("/history/{run_id}")
def get_run(run_id: str, authorization: Optional[str] = Header(None)):
    """Fetch a single run by ID — only the owner or an admin may access it."""
    user = inject_user(authorization)
    uid = user["uid"]

    db = core.get_db()
    with step("run_read"):
        doc = db.collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Run not found")

    data = doc.to_dict()
    if data.get("uid") != uid and user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return data

