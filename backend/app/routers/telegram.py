"""Telegram webhook for the Nerva Supermemory interface."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_WEBHOOK_SECRET,
    TELEGRAM_WEBHOOK_URL,
)
from app.integrations import telegram_client
from app.services import nerva_telegram
from app.supermemory import client as sm
from app.supermemory import mcp_client as sm_mcp

logger = logging.getLogger("nerva.telegram.api")

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

def _webhook_url() -> str:
    url = (TELEGRAM_WEBHOOK_URL or "").strip()
    if url:
        return url
    return "https://YOUR_VERCEL_DOMAIN/api/telegram/webhook"


def _validate_webhook_secret(
    header_value: str | None,
) -> None:
    expected = (TELEGRAM_WEBHOOK_SECRET or "").strip()
    if not expected:
        return
    if header_value != expected:
        logger.warning("Telegram webhook rejected (invalid secret token)")
        raise HTTPException(status_code=403, detail="Invalid webhook secret")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, Any]:
    _validate_webhook_secret(x_telegram_bot_api_secret_token)

    try:
        update = await request.json()
    except Exception:
        logger.warning("Telegram webhook rejected (invalid JSON)")
        raise HTTPException(status_code=400, detail="Invalid JSON body") from None

    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    return await nerva_telegram.process_telegram_update(update)


@router.get("/status")
def telegram_status() -> dict[str, Any]:
    """Operational status without exposing secrets."""
    return {
        "telegram_bot_configured": telegram_client.telegram_configured(),
        "telegram_chat_id_configured": bool((TELEGRAM_CHAT_ID or "").strip()),
        "supermemory_configured": sm.is_configured(),
        "retrieval_backend": "supermemory_mcp",
        "mcp_configured": sm_mcp.is_configured(),
        "webhook_path": "/api/telegram/webhook",
        "authorized_chat_only": True,
    }


@router.get("/setup")
def telegram_setup() -> dict[str, Any]:
    """
    Webhook setup helpers. Replace YOUR_BOT_TOKEN with the real token locally;
    never commit the token to source control.
    """
    secret_note = ""
    if (TELEGRAM_WEBHOOK_SECRET or "").strip():
        secret_note = (
            ' Include header secret_token when calling setWebhook and send '
            'X-Telegram-Bot-Api-Secret-Token on each webhook request.'
        )

    webhook_url = _webhook_url()
    payload: dict[str, str] = {"url": webhook_url}
    if (TELEGRAM_WEBHOOK_SECRET or "").strip():
        payload["secret_token"] = TELEGRAM_WEBHOOK_SECRET.strip()
    webhook_body = json.dumps(payload)

    return {
        "webhook_url": webhook_url,
        "set_webhook_curl": (
            'curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" '
            f'-H "Content-Type: application/json" '
            f"-d '{webhook_body}'"
        ),
        "verify_webhook_curl": (
            'curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"'
        ),
        "remove_webhook_curl": (
            'curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/deleteWebhook" '
            '-H "Content-Type: application/json" '
            '-d \'{"drop_pending_updates": true}\''
        ),
        "pending_updates_curl": (
            'curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates"'
        ),
        "notes": (
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in Vercel env vars. "
            "Only the configured TELEGRAM_CHAT_ID may use the bot."
            + secret_note
        ),
        "example_test_message": "What was I working on yesterday?",
    }
