"""Firebase Admin SDK initialisation, token verification, and role lookup."""

import json
import os

import firebase_admin
from firebase_admin import auth, credentials, firestore
from fastapi import HTTPException

_app = None


def _get_app() -> firebase_admin.App:
    """Lazily initialise Firebase Admin from env-var service account JSON."""
    global _app
    if _app is not None:
        return _app

    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON env var is not set")

    sa_dict = json.loads(sa_json)
    cred = credentials.Certificate(sa_dict)
    _app = firebase_admin.initialize_app(cred)
    return _app


def get_db():
    """A Firestore client, guaranteeing the SDK is initialised first.

    Calling `firestore.client()` directly works only if something already ran
    `_get_app()` — which for authenticated routes happens inside verify_token.
    An unauthenticated route that touches Firestore (the Stripe webhook) has no
    such step and fails with "The default Firebase app does not exist". Routing
    every caller through here makes that impossible rather than remembered.
    """
    _get_app()
    return firestore.client()


def verify_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return its decoded payload."""
    _get_app()
    try:
        decoded = auth.verify_id_token(id_token)
        return {"uid": decoded["uid"], "email": decoded.get("email", "")}
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def get_user_profile(uid: str) -> dict | None:
    """Read the full users/{uid} document, or None if it does not exist yet.

    Returns None during the brief window between account creation and the
    client writing the profile doc — callers must treat that as a new,
    unblocked user rather than denying access.
    """
    _get_app()
    db = firestore.client()
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def get_user_role(uid: str) -> str:
    """Read users/{uid}.role from Firestore and return it (defaults to 'user')."""
    profile = get_user_profile(uid)
    return (profile or {}).get("role", "user")
