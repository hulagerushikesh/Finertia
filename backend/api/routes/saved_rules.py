"""Saved rules: a user's own rules, kept by name to re-run or re-scan later.

`rules/{id}` holds `{uid, name, rule, createdAt, updatedAt}`. A rule is
checked with the same validator the backtest uses (rules.validate) before it
is stored, so a saved rule always runs. At most MAX_SAVED per user — a rule
library is a handful of ideas, not a database. Listing filters on uid only
and sorts in Python, so no composite index is needed.

Part of the user's data: exported and deleted with the account (account.py).
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import BaseModel, Field, field_validator

from api import core
from api.core import inject_user
from rules import RuleError, validate as validate_rule

router = APIRouter()

COLLECTION = "rules"
MAX_SAVED = 20


def _clean_name(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("Give the rule a name.")
    return v


def _checked_rule(v: dict) -> dict:
    try:
        return validate_rule(v)
    except RuleError as exc:
        raise ValueError(str(exc)) from exc


class SavedRuleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    rule: dict

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean_name(v)

    @field_validator("rule")
    @classmethod
    def _rule(cls, v: dict) -> dict:
        return _checked_rule(v)


class SavedRulePatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=60)
    rule: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return None if v is None else _clean_name(v)

    @field_validator("rule")
    @classmethod
    def _rule(cls, v):
        return None if v is None else _checked_rule(v)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _mine(db, uid: str) -> list[dict]:
    q = db.collection(COLLECTION).where(filter=FieldFilter("uid", "==", uid))
    out = [{"id": s.id, **(s.to_dict() or {})} for s in q.stream()]
    out.sort(key=lambda r: r.get("updatedAt") or "", reverse=True)
    return [{k: r[k] for k in ("id", "name", "rule", "createdAt", "updatedAt") if k in r} for r in out]


def _owned(db, uid: str, rule_id: str):
    ref = db.collection(COLLECTION).document(rule_id)
    snap = ref.get()
    # Someone else's rule reads as missing, not forbidden: an id says nothing.
    if not snap.exists or (snap.to_dict() or {}).get("uid") != uid:
        raise HTTPException(status_code=404, detail="Saved rule not found")
    return ref, snap.to_dict()


@router.get("/rules")
def list_rules(authorization: Optional[str] = Header(None)):
    user = inject_user(authorization)
    return {"rules": _mine(core.get_db(), user["uid"]), "max": MAX_SAVED}


@router.post("/rules", status_code=201)
def save_rule(body: SavedRuleIn, authorization: Optional[str] = Header(None)):
    user = inject_user(authorization)
    db = core.get_db()
    existing = _mine(db, user["uid"])
    if any(r["name"].lower() == body.name.lower() for r in existing):
        raise HTTPException(status_code=409, detail=f"You already have a rule called “{body.name}”.")
    if len(existing) >= MAX_SAVED:
        raise HTTPException(
            status_code=400,
            detail=f"You can keep up to {MAX_SAVED} rules. Delete one to save another.",
        )
    rule_id = uuid.uuid4().hex
    now = _now()
    doc = {"uid": user["uid"], "name": body.name, "rule": body.rule, "createdAt": now, "updatedAt": now}
    db.collection(COLLECTION).document(rule_id).set(doc)
    return {"id": rule_id, **{k: doc[k] for k in ("name", "rule", "createdAt", "updatedAt")}}


@router.patch("/rules/{rule_id}")
def update_rule(rule_id: str, body: SavedRulePatch, authorization: Optional[str] = Header(None)):
    user = inject_user(authorization)
    db = core.get_db()
    ref, current = _owned(db, user["uid"], rule_id)
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    if "name" in changes and changes["name"].lower() != current["name"].lower():
        if any(r["name"].lower() == changes["name"].lower() for r in _mine(db, user["uid"])):
            raise HTTPException(status_code=409, detail=f"You already have a rule called “{changes['name']}”.")
    changes["updatedAt"] = _now()
    ref.set(changes, merge=True)
    merged = {**current, **changes}
    return {"id": rule_id, **{k: merged[k] for k in ("name", "rule", "createdAt", "updatedAt")}}


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, authorization: Optional[str] = Header(None)):
    user = inject_user(authorization)
    db = core.get_db()
    ref, _ = _owned(db, user["uid"], rule_id)
    ref.delete()
