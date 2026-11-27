"""Health, plans and the strategy list: public, and none of them block."""

import os

from fastapi import APIRouter

import billing
from plans import public_plans
from strategies import STRATEGIES, STRATEGY_NAMES

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint — no auth required.

    Also says what is serving: `commit` is the git SHA the Deploy workflow
    passes in as GIT_SHA, `revision` the Cloud Run revision. The release
    checklist compares `commit` with the `backend-deployed` tag, so "the tag
    says X" and "production runs X" cannot drift apart unnoticed. Both are
    null locally. The repository is public, so neither tells anyone anything.
    """
    return {
        "status": "ok",
        "commit": os.environ.get("GIT_SHA") or None,
        "revision": os.environ.get("K_REVISION") or None,
        # "staging" on the staging service; production sets nothing.
        "environment": os.environ.get("FINERTIA_ENV") or "production",
    }


@router.get("/plans")
async def list_plans():
    """Plan tiers for the pricing page — no auth required.

    `billing_enabled` tells the client whether an upgrade button can do
    anything, so a self-hosted deployment shows the tiers without offering a
    checkout that would fail.
    """
    return {"plans": public_plans(), "billing_enabled": billing.is_configured()}


@router.get("/strategies")
async def list_strategies():
    """Available strategies and their parameter names — no auth required.

    Lets the frontend render the strategy picker without hardcoding a list that
    would drift out of sync with the backend registry.
    """
    return {
        "strategies": [
            {"id": name, "label": STRATEGIES[name]["label"]} for name in STRATEGY_NAMES
        ]
    }

