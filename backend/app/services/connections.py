"""Supermemory OAuth connectors (Gmail, GitHub, …)."""

from __future__ import annotations

from typing import Any, Literal

from app.config import CONNECTIONS_REDIRECT_URL, NERVA_USER_ID
from app.supermemory import client as sm
from app.supermemory.containers import (
    container_tag_for_user,
    resolve_container_tag,
)

Provider = Literal["gmail", "github"]

PROVIDER_NOTES = {
    "gmail": (
        "Gmail requires Supermemory Scale or Enterprise. "
        "OAuth is handled by Supermemory — no Google API credentials in Nerva."
    ),
    "github": (
        "GitHub requires Supermemory Scale or Enterprise. "
        "OAuth is handled by Supermemory — no GitHub API credentials in Nerva. "
        "By default GitHub syncs docs/text (.md, .txt, …); source code "
        "(.js, .py, .go, …) is excluded unless configured otherwise."
    ),
}


def start_connection(
    provider: Provider,
    *,
    user_id: str | None = None,
    redirect_url: str | None = None,
    document_limit: int = 5000,
) -> dict[str, Any]:
    if not sm.is_configured():
        return {
            "ok": False,
            "error": "SUPERMEMORY_API_KEY is not configured.",
        }

    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    tag = container_tag_for_user(uid)
    redirect = (redirect_url or CONNECTIONS_REDIRECT_URL).strip()
    if not redirect:
        return {
            "ok": False,
            "error": "redirectUrl / CONNECTIONS_REDIRECT_URL is required.",
        }

    # Append provider hint for the SPA callback banner.
    sep = "&" if "?" in redirect else "?"
    if "provider=" not in redirect:
        redirect = f"{redirect}{sep}provider={provider}"

    try:
        raw = sm.create_connection(
            provider,
            redirect_url=redirect,
            container_tag=tag,
            document_limit=document_limit,
            metadata={
                "source": provider,
                "user_id": uid,
                "app": "nerva",
            },
        )
    except sm.SupermemoryError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "provider": provider,
            "user_id": uid,
            "container_tag": tag,
            "plan_note": PROVIDER_NOTES.get(provider),
        }

    auth_link = raw.get("authLink") or raw.get("auth_link")
    return {
        "ok": True,
        "provider": provider,
        "user_id": uid,
        "container_tag": tag,
        "auth_link": auth_link,
        "connection_id": raw.get("id"),
        "expires_in": raw.get("expiresIn") or raw.get("expires_in"),
        "redirects_to": raw.get("redirectsTo") or redirect,
        "plan_note": PROVIDER_NOTES.get(provider),
        "raw": raw,
    }


def list_user_connections(user_id: str | None = None) -> dict[str, Any]:
    if not sm.is_configured():
        return {
            "ok": False,
            "error": "SUPERMEMORY_API_KEY is not configured.",
            "connections": [],
            "container_tag": resolve_container_tag(user_id),
        }

    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    tag = container_tag_for_user(uid)
    try:
        connections = sm.list_connections(container_tag=tag)
    except sm.SupermemoryError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "connections": [],
            "user_id": uid,
            "container_tag": tag,
        }

    return {
        "ok": True,
        "user_id": uid,
        "container_tag": tag,
        "connections": connections,
        "plan_notes": PROVIDER_NOTES,
    }


def disconnect(
    connection_id: str,
    *,
    delete_documents: bool = False,
) -> dict[str, Any]:
    if not sm.is_configured():
        return {"ok": False, "error": "SUPERMEMORY_API_KEY is not configured."}
    try:
        result = sm.delete_connection(
            connection_id,
            delete_documents=delete_documents,
        )
        return {"ok": True, "result": result}
    except sm.SupermemoryError as exc:
        return {"ok": False, "error": str(exc)}
