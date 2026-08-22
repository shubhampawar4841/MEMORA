"""Resolve a valid Google access token for server-side MCP calls."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.auth.google_oauth import GoogleOAuthError, refresh_access_token
from app.auth.token_store import GoogleTokenRecord, get_google_tokens, save_google_tokens

_TOKEN_REFRESH_BUFFER_SECONDS = 120


def _is_expired(record: GoogleTokenRecord) -> bool:
    if record.expires_at is None:
        return False
    now = int(datetime.now(UTC).timestamp())
    return record.expires_at <= now + _TOKEN_REFRESH_BUFFER_SECONDS


def get_valid_google_access_token(user_id: str | None = None) -> str | None:
    """
    Return a usable Google access token for Workspace MCP.

    Refreshes and persists a new access token when the stored one is expired.
    """
    record = get_google_tokens(user_id)
    if not record:
        return None

    if not _is_expired(record):
        return record.access_token

    if not record.refresh_token:
        return None

    try:
        refreshed = refresh_access_token(record.refresh_token)
    except GoogleOAuthError:
        return None

    scope_raw = refreshed.get("scope") or " ".join(record.scopes)
    scopes = [s for s in str(scope_raw).split() if s]

    updated = save_google_tokens(
        user_id=record.user_id,
        google_sub=record.google_sub,
        email=record.email,
        name=record.name,
        access_token=str(refreshed["access_token"]),
        refresh_token=refreshed.get("refresh_token") or record.refresh_token,
        token_type=str(refreshed.get("token_type") or record.token_type),
        expires_in=refreshed.get("expires_in"),
        scopes=scopes or record.scopes,
    )
    return updated.access_token


def google_mcp_auth_headers(user_id: str | None = None) -> dict[str, str] | None:
    """Bearer headers for Google Workspace MCP servers."""
    access_token = get_valid_google_access_token(user_id)
    if not access_token:
        return None
    return {"Authorization": f"Bearer {access_token}"}
