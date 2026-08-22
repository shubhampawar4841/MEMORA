"""Resolve a valid Google access token for server-side MCP calls."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.auth.google_oauth import (
    GoogleOAuthError,
    has_calendar_mcp_scopes,
    has_gmail_mcp_scopes,
    has_workspace_mcp_scopes,
    refresh_access_token,
)
from app.auth.token_store import GoogleTokenRecord, get_google_tokens, save_google_tokens

logger = logging.getLogger("nerva.auth.google_access")

_TOKEN_REFRESH_BUFFER_SECONDS = 120


def _is_expired(record: GoogleTokenRecord) -> bool:
    if record.expires_at is None:
        return False
    now = int(datetime.now(UTC).timestamp())
    return record.expires_at <= now + _TOKEN_REFRESH_BUFFER_SECONDS


def _needs_refresh(record: GoogleTokenRecord) -> bool:
    """Refresh when expired, or when expiry is unknown but a refresh token exists."""
    if record.refresh_token and record.expires_at is None:
        return True
    return _is_expired(record)


def _normalize_access_token(access_token: str) -> str | None:
    token = access_token.strip()
    return token or None


def _scope_summary(record: GoogleTokenRecord) -> dict[str, bool]:
    return {
        "gmail_mcp_scopes": has_gmail_mcp_scopes(record.scopes),
        "calendar_mcp_scopes": has_calendar_mcp_scopes(record.scopes),
        "workspace_mcp_scopes": has_workspace_mcp_scopes(record.scopes),
    }


def get_google_mcp_diagnostics(user_id: str | None = None) -> dict[str, Any]:
    """
    Safe diagnostics for logging — never includes tokens or secrets.
    """
    record = get_google_tokens(user_id)
    if not record:
        return {
            "google_oauth_token_available": False,
            "token_refresh_performed": False,
            "email": None,
            "has_refresh_token": False,
            "scope_summary": {
                "gmail_mcp_scopes": False,
                "calendar_mcp_scopes": False,
                "workspace_mcp_scopes": False,
            },
            "reason": "no_stored_token",
        }

    scopes = _scope_summary(record)
    return {
        "google_oauth_token_available": scopes["workspace_mcp_scopes"],
        "token_refresh_performed": False,
        "email": record.email or None,
        "has_refresh_token": bool(record.refresh_token),
        "expires_at": record.expires_at,
        "scope_summary": scopes,
        "reason": None if scopes["workspace_mcp_scopes"] else "missing_mcp_scopes",
    }


def get_valid_google_access_token(
    user_id: str | None = None,
    *,
    _refresh_performed: list[bool] | None = None,
) -> str | None:
    """
    Return a usable Google OAuth access token for Workspace MCP.

    Google Workspace MCP servers authenticate with a standard OAuth 2.0 user
    access token in the Authorization Bearer header — not a separate MCP token.
    """
    record = get_google_tokens(user_id)
    if not record:
        logger.info("Google OAuth token available: no (no stored token)")
        return None

    scope_info = _scope_summary(record)
    if not scope_info["workspace_mcp_scopes"]:
        logger.warning(
            "Google OAuth token available: no — stored token for %s missing MCP "
            "scopes (gmail=%s calendar=%s). Re-authenticate via /auth/google",
            record.email or record.user_id,
            scope_info["gmail_mcp_scopes"],
            scope_info["calendar_mcp_scopes"],
        )
        return None

    if not _needs_refresh(record):
        logger.info(
            "Google OAuth token available: yes (email=%s, refresh=no)",
            record.email or record.user_id,
        )
        return _normalize_access_token(record.access_token)

    if not record.refresh_token:
        logger.warning(
            "Google OAuth token available: no — access token expired for %s "
            "and no refresh token is stored",
            record.email or record.user_id,
        )
        return None

    try:
        refreshed = refresh_access_token(record.refresh_token)
    except GoogleOAuthError as exc:
        logger.warning(
            "Google OAuth token available: no — refresh failed for %s: %s",
            record.email or record.user_id,
            exc,
        )
        return None

    if _refresh_performed is not None:
        _refresh_performed.append(True)

    scope_raw = refreshed.get("scope") or " ".join(record.scopes)
    scopes = [scope for scope in str(scope_raw).split() if scope]

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

    if not has_workspace_mcp_scopes(updated.scopes):
        logger.warning(
            "Google OAuth token available: no — refreshed token for %s missing "
            "Gmail/Calendar MCP scopes",
            updated.email or updated.user_id,
        )
        return None

    logger.info(
        "Google OAuth token available: yes (email=%s, refresh=yes)",
        updated.email or updated.user_id,
    )
    return _normalize_access_token(updated.access_token)


def google_mcp_auth_headers(user_id: str | None = None) -> dict[str, str] | None:
    """
    Bearer headers for Google Workspace MCP servers.

    Returns exactly {"Authorization": "Bearer <valid_access_token>"} when the
    authenticated backend user has a valid token with the required MCP scopes.
    """
    headers, _refresh = resolve_google_mcp_auth(user_id)
    return headers


def resolve_google_mcp_auth(
    user_id: str | None = None,
) -> tuple[dict[str, str] | None, bool]:
    """Return MCP auth headers and whether a token refresh was performed."""
    refresh_flags: list[bool] = []
    token = get_valid_google_access_token(user_id, _refresh_performed=refresh_flags)
    if not token:
        return None, bool(refresh_flags)
    return {"Authorization": f"Bearer {token}"}, bool(refresh_flags)
