"""Telegram webhook for the Nerva Supermemory interface."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_WEBHOOK_SECRET,
)
from app.integrations import telegram_client
from app.services import nerva_telegram
from app.supermemory import client as sm

logger = logging.getLogger("nerva.telegram.api")

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

_WEBHOOK_URL = "https://memora-ashen-gamma.vercel.app/api/telegram/webhook"


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

    return {
        "webhook_url": _WEBHOOK_URL,
        "set_webhook_curl": (
            'curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" '
            f'-H "Content-Type: application/json" '
            f'-d \'{{"url": "{_WEBHOOK_URL}"}}\''
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
