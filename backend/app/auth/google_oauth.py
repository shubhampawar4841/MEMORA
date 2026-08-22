"""Google OAuth 2.0 helpers for Gmail + Calendar authorization."""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

# Minimum scopes for read/search Gmail + Calendar.
GOOGLE_OAUTH_SCOPES: tuple[str, ...] = (
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)

_state_lock = threading.Lock()
_pending_states: dict[str, float] = {}
_STATE_TTL_SECONDS = 600


class GoogleOAuthError(RuntimeError):
    """Raised when Google OAuth configuration or exchange fails."""


def is_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI)


def _require_config() -> None:
    if not is_configured():
        raise GoogleOAuthError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI."
        )


def _prune_states(now: float) -> None:
    expired = [
        state
        for state, created_at in _pending_states.items()
        if now - created_at > _STATE_TTL_SECONDS
    ]
    for state in expired:
        _pending_states.pop(state, None)


def create_authorization_url() -> tuple[str, str]:
    _require_config()
    state = secrets.token_urlsafe(32)
    now = time.time()
    with _state_lock:
        _prune_states(now)
        _pending_states[state] = now

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_OAUTH_SCOPES),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}", state


def validate_state(state: str | None) -> bool:
    if not state:
        return False
    now = time.time()
    with _state_lock:
        _prune_states(now)
        created_at = _pending_states.pop(state, None)
    if created_at is None:
        return False
    return now - created_at <= _STATE_TTL_SECONDS


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    _require_config()
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(GOOGLE_TOKEN_URL, data=payload)

    if response.status_code >= 400:
        raise GoogleOAuthError(
            f"Token exchange failed ({response.status_code}): {response.text}"
        )

    data = response.json()
    if not isinstance(data, dict) or not data.get("access_token"):
        raise GoogleOAuthError("Token exchange returned no access_token.")

    return data


def fetch_google_userinfo(access_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code >= 400:
        raise GoogleOAuthError(
            f"Userinfo request failed ({response.status_code}): {response.text}"
        )

    data = response.json()
    if not isinstance(data, dict) or not data.get("sub"):
        raise GoogleOAuthError("Google userinfo response was invalid.")

    return data
