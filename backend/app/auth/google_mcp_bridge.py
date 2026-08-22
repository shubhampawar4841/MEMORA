"""
Google Workspace MCP credential bridge for LiveKit agents.

Architecture
------------

Google's official Workspace MCP servers (Gmail, Calendar) authenticate with
OAuth 2.0. MCP clients such as Antigravity configure ``clientId`` + ``clientSecret``
because *they* run the browser consent flow. At runtime those clients send the
resulting **user access token** on each MCP HTTP request:

    Authorization: Bearer <google_oauth_access_token>

LiveKit's ``MCPServerHTTP`` has no built-in OAuth client flow — it only accepts
static ``headers``. Therefore Memora uses a small backend bridge:

1. **Next.js** → user clicks "Sign in with Google"
2. **FastAPI** ``/auth/google`` → Google consent + code exchange (client secret
   stays server-side) → refresh/access tokens stored in ``data/google_oauth/``
3. **FastAPI** ``/auth/google/mcp/headers`` → returns a fresh Bearer header for
   the LiveKit worker (optional shared secret; never exposes refresh tokens)
4. **LiveKit agent** → ``MCPServerHTTP(url=..., headers=..., transport_type=
   "streamable_http")`` → Google's remote MCP endpoints

Supermemory/Firecrawl continue to use API-key Bearer headers unchanged.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

import httpx

from app.auth.google_access import get_google_mcp_diagnostics, resolve_google_mcp_auth
from app.auth.google_mcp import probe_google_workspace_mcp
from app.config import (
    GOOGLE_MCP_BRIDGE_SECRET,
    GOOGLE_MCP_BRIDGE_URL,
    GOOGLE_MCP_CREDENTIAL_MODE,
)

logger = logging.getLogger("nerva.auth.google_mcp_bridge")

_BRIDGE_HEADER = "X-Nerva-MCP-Bridge-Key"


def fetch_google_mcp_auth_headers(
    user_id: str | None = None,
) -> tuple[dict[str, str] | None, bool, str]:
    """
    Resolve Google MCP Authorization headers for the LiveKit worker.

    Returns ``(headers, refresh_performed, source)`` where ``source`` is
    ``"local"`` or ``"api"``.
    """
    mode = GOOGLE_MCP_CREDENTIAL_MODE
    if mode == "api":
        headers, refreshed = _fetch_via_api_bridge(user_id)
        if headers:
            return headers, refreshed, "api"
        logger.warning(
            "Google MCP API bridge failed — falling back to local token store"
        )

    headers, refreshed = resolve_google_mcp_auth(user_id)
    return headers, refreshed, "local"


def _fetch_via_api_bridge(
    user_id: str | None,
) -> tuple[dict[str, str] | None, bool]:
    if not GOOGLE_MCP_BRIDGE_URL:
        return None, False

    params: dict[str, str] = {}
    if user_id:
        params["user_id"] = user_id

    request_headers: dict[str, str] = {}
    if GOOGLE_MCP_BRIDGE_SECRET:
        request_headers[_BRIDGE_HEADER] = GOOGLE_MCP_BRIDGE_SECRET

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                GOOGLE_MCP_BRIDGE_URL,
                params=params or None,
                headers=request_headers,
            )
        if response.status_code >= 400:
            logger.warning(
                "Google MCP bridge HTTP %s from %s",
                response.status_code,
                GOOGLE_MCP_BRIDGE_URL,
            )
            return None, False

        payload = response.json()
        if not isinstance(payload, dict):
            return None, False

        raw_headers = payload.get("headers")
        if not isinstance(raw_headers, dict):
            return None, False

        authorization = raw_headers.get("Authorization")
        if not isinstance(authorization, str) or not authorization.startswith(
            "Bearer "
        ):
            return None, False

        refreshed = bool(payload.get("token_refresh_performed"))
        return {"Authorization": authorization}, refreshed
    except httpx.HTTPError as exc:
        logger.warning("Google MCP bridge request failed: %s", exc.__class__.__name__)
        return None, False


def get_google_mcp_runtime_status(
    user_id: str | None = None,
    *,
    probe: bool = True,
) -> dict[str, Any]:
    """
    Safe runtime status for logs and ``/auth/google/mcp/status``.

    Never includes access tokens, refresh tokens, or client secrets.
    """
    headers, refresh_performed, source = fetch_google_mcp_auth_headers(user_id)
    diagnostics = get_google_mcp_diagnostics(user_id)
    diagnostics["token_refresh_performed"] = refresh_performed
    diagnostics["credential_source"] = source
    diagnostics["gmail_mcp_enabled"] = False
    diagnostics["calendar_mcp_enabled"] = False
    diagnostics["gmail_mcp_discovery"] = None
    diagnostics["calendar_mcp_discovery"] = None

    if not headers:
        diagnostics["reason"] = diagnostics.get("reason") or "no_valid_token"
        return diagnostics

    if not probe:
        diagnostics["google_oauth_token_available"] = True
        return diagnostics

    probe_result = probe_google_workspace_mcp(headers)
    gmail = probe_result["gmail"]
    calendar = probe_result["calendar"]

    diagnostics["google_oauth_token_available"] = True
    diagnostics["gmail_mcp_enabled"] = gmail["connected"]
    diagnostics["calendar_mcp_enabled"] = calendar["connected"]
    diagnostics["gmail_mcp_discovery"] = {
        "connected": gmail["connected"],
        "tools_discovered": gmail["tools_discovered"],
        "tool_names_sample": gmail["tool_names_sample"],
        "error": gmail["error"],
    }
    diagnostics["calendar_mcp_discovery"] = {
        "connected": calendar["connected"],
        "tools_discovered": calendar["tools_discovered"],
        "tool_names_sample": calendar["tool_names_sample"],
        "error": calendar["error"],
    }
    return diagnostics


def log_google_mcp_runtime_status(user_id: str | None = None) -> dict[str, Any]:
    """Emit standard Google MCP startup logs and return the status dict."""
    status = get_google_mcp_runtime_status(user_id, probe=True)

    logger.info(
        "Google OAuth token available: %s",
        "yes" if status.get("google_oauth_token_available") else "no",
    )
    logger.info(
        "Token refresh performed: %s",
        "yes" if status.get("token_refresh_performed") else "no",
    )
    logger.info("Google MCP credential source: %s", status.get("credential_source"))
    logger.info(
        "Gmail MCP enabled: %s",
        "yes" if status.get("gmail_mcp_enabled") else "no",
    )
    logger.info(
        "Calendar MCP enabled: %s",
        "yes" if status.get("calendar_mcp_enabled") else "no",
    )

    gmail_discovery = status.get("gmail_mcp_discovery") or {}
    calendar_discovery = status.get("calendar_mcp_discovery") or {}
    if gmail_discovery:
        logger.info(
            "Gmail MCP discovery: connected=%s tools=%s sample=%s error=%s",
            gmail_discovery.get("connected"),
            gmail_discovery.get("tools_discovered"),
            gmail_discovery.get("tool_names_sample"),
            gmail_discovery.get("error"),
        )
    if calendar_discovery:
        logger.info(
            "Calendar MCP discovery: connected=%s tools=%s sample=%s error=%s",
            calendar_discovery.get("connected"),
            calendar_discovery.get("tools_discovered"),
            calendar_discovery.get("tool_names_sample"),
            calendar_discovery.get("error"),
        )

    if status.get("reason") == "missing_mcp_scopes":
        scope_summary = status.get("scope_summary") or {}
        logger.warning(
            "Google MCP scopes incomplete (gmail=%s calendar=%s) — re-sign in",
            scope_summary.get("gmail_mcp_scopes"),
            scope_summary.get("calendar_mcp_scopes"),
        )

    return status
