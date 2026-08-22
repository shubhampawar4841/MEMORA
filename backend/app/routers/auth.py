"""Google OAuth routes."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth.google_oauth import (
    GoogleOAuthError,
    exchange_code_for_tokens,
    create_authorization_url,
    fetch_google_userinfo,
    is_configured,
    validate_state,
)
from app.auth.token_store import (
    get_google_connection_status,
    save_google_tokens,
)
from app.config import FRONTEND_URL, NERVA_USER_ID

router = APIRouter(prefix="/auth", tags=["auth"])


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
