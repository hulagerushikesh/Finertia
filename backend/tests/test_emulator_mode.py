"""Emulator mode is for local end-to-end tests only — never on Cloud Run."""

import pytest

import firebase_admin_init as fai

EMU = {"FIREBASE_AUTH_EMULATOR_HOST": "127.0.0.1:9099", "FIRESTORE_EMULATOR_HOST": "127.0.0.1:8080"}


def _env(monkeypatch, **values):
    for k in (*EMU, "K_SERVICE"):
        monkeypatch.delenv(k, raising=False)
    for k, v in values.items():
        monkeypatch.setenv(k, v)


def test_off_by_default(monkeypatch):
    _env(monkeypatch)
    assert fai.emulator_mode() is False


def test_needs_both_emulators(monkeypatch):
    _env(monkeypatch, FIREBASE_AUTH_EMULATOR_HOST="127.0.0.1:9099")
    assert fai.emulator_mode() is False


def test_on_with_both(monkeypatch):
    _env(monkeypatch, **EMU)
    assert fai.emulator_mode() is True


def test_refused_on_cloud_run(monkeypatch):
    _env(monkeypatch, **EMU, K_SERVICE="finertia-api")
    with pytest.raises(RuntimeError, match="Cloud Run"):
        fai.emulator_mode()
