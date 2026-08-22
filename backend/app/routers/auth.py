"""Google OAuth routes."""

from __future__ import annotations

from typing import Any

from urllib.parse import urlencode

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from app.auth.google_access import resolve_google_mcp_auth
from app.auth.google_mcp_bridge import get_google_mcp_runtime_status
from app.auth.google_oauth import (
    GoogleOAuthError,
    GOOGLE_OAUTH_SCOPES,
    exchange_code_for_tokens,
    create_authorization_url,
    fetch_google_userinfo,
    has_workspace_mcp_scopes,
    is_configured,
    validate_state,
)
from app.auth.token_store import (
    get_google_connection_status,
    save_google_tokens,
)
from app.config import FRONTEND_URL, GOOGLE_MCP_BRIDGE_SECRET, NERVA_USER_ID

router = APIRouter(prefix="/auth", tags=["auth"])

_BRIDGE_HEADER = "X-Nerva-MCP-Bridge-Key"


def _require_mcp_bridge_access(
    request: Request,
    bridge_key: str | None,
) -> None:
    """Guard the MCP header bridge — never expose tokens without authorization."""
    if GOOGLE_MCP_BRIDGE_SECRET:
        if bridge_key != GOOGLE_MCP_BRIDGE_SECRET:
            raise HTTPException(status_code=401, detail="Invalid MCP bridge key.")
        return

    client_host = request.client.host if request.client else ""
    if client_host in {"127.0.0.1", "::1", "localhost"}:
        return

    raise HTTPException(
        status_code=503,
        detail=(
            "Google MCP bridge is not configured. Set GOOGLE_MCP_BRIDGE_SECRET "
            "or call from localhost."
        ),
    )


def _frontend_redirect(*, success: bool, **params: str) -> RedirectResponse:
    if success:
        query = urlencode(params)
        return RedirectResponse(url=f"{FRONTEND_URL}/?{query}", status_code=302)
    message = params.get("message", "Google sign-in failed.")
    query = urlencode({"google": "error", "message": message})
    return RedirectResponse(url=f"{FRONTEND_URL}/?{query}", status_code=302)


@router.get("/google")
def google_login():
    """Redirect browser to Google's OAuth consent screen."""
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI."
            ),
        )

    try:
        authorization_url, _state = create_authorization_url()
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RedirectResponse(url=authorization_url, status_code=302)


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
):
    """Handle Google's redirect, exchange code, store tokens server-side."""
    if error:
        message = error_description or error
        return _frontend_redirect(success=False, message=message)

    if not code:
        return _frontend_redirect(success=False, message="Missing authorization code.")

    if not validate_state(state):
        return _frontend_redirect(
            success=False,
            message="Invalid or expired OAuth state. Please try again.",
        )

    try:
        token_payload = exchange_code_for_tokens(code)
        access_token = str(token_payload["access_token"])
        userinfo = fetch_google_userinfo(access_token)
    except GoogleOAuthError as exc:
        return _frontend_redirect(success=False, message=str(exc))

    scope_raw = token_payload.get("scope") or ""
    scopes = [s for s in str(scope_raw).split() if s]

    if not scopes:
        scopes = list(GOOGLE_OAUTH_SCOPES)

    if not has_workspace_mcp_scopes(scopes):
        return _frontend_redirect(
            success=False,
            message=(
                "Google sign-in did not grant the Gmail and Calendar MCP scopes. "
                "Try again and approve all requested permissions."
            ),
        )

    save_google_tokens(
        user_id=NERVA_USER_ID,
        google_sub=str(userinfo["sub"]),
        email=str(userinfo.get("email") or ""),
        name=userinfo.get("name"),
        access_token=access_token,
        refresh_token=token_payload.get("refresh_token"),
        token_type=str(token_payload.get("token_type") or "Bearer"),
        expires_in=token_payload.get("expires_in"),
        scopes=scopes,
    )

    email = str(userinfo.get("email") or "")
    return _frontend_redirect(success=True, google="connected", email=email)


@router.get("/google/status")
def google_status():
    """Public connection status — never exposes tokens."""
    return get_google_connection_status()


@router.get("/google/mcp/status")
def google_mcp_status(user_id: str | None = Query(default=None)) -> dict[str, Any]:
    """Public MCP readiness diagnostics — never exposes tokens or secrets."""
    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    return get_google_mcp_runtime_status(uid, probe=True)


@router.get("/google/mcp/headers")
def google_mcp_headers(
    request: Request,
    user_id: str | None = Query(default=None),
    x_nerva_mcp_bridge_key: str | None = Header(default=None, alias=_BRIDGE_HEADER),
) -> dict[str, Any]:
    """
    Internal credential bridge for the LiveKit worker.

    Returns ``{"headers": {"Authorization": "Bearer ..."}, "token_refresh_performed": bool}``.
    Never returns refresh tokens or client secrets.
    """
    _require_mcp_bridge_access(request, x_nerva_mcp_bridge_key)
    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    headers, refresh_performed = resolve_google_mcp_auth(uid)
    if not headers:
        raise HTTPException(
            status_code=404,
            detail="No valid Google OAuth token for MCP. Sign in via /auth/google.",
        )
    return {
        "headers": headers,
        "token_refresh_performed": refresh_performed,
        "user_id": uid,
    }
