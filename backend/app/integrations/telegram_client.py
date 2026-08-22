"""Async Telegram Bot API client (server-side only)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("nerva.telegram.client")

_TELEGRAM_API_BASE = "https://api.telegram.org"
_TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def telegram_configured() -> bool:
    from app.config import TELEGRAM_BOT_TOKEN

    return bool((TELEGRAM_BOT_TOKEN or "").strip())


def _bot_token() -> str | None:
    from app.config import TELEGRAM_BOT_TOKEN

    token = (TELEGRAM_BOT_TOKEN or "").strip()
    return token or None


async def send_message(
    *,
    chat_id: str,
    text: str,
    timeout: float = 30.0,
) -> tuple[bool, str | None]:
    """Send a Telegram message. Returns (ok, error_description)."""
    token = _bot_token()
    if not token:
        return False, "Telegram bot token is not configured"

    body = (text or "").strip()
    if not body:
        return False, "Message text is empty"

    if len(body) > _TELEGRAM_MAX_MESSAGE_LENGTH:
        body = body[: _TELEGRAM_MAX_MESSAGE_LENGTH - 3].rstrip() + "..."

    url = f"{_TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": body}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError:
        logger.warning("Telegram sendMessage request failed")
        return False, "Could not reach Telegram"

    try:
        data: dict[str, Any] = response.json()
    except ValueError:
        logger.warning(
            "Telegram sendMessage returned non-JSON (status=%s)",
            response.status_code,
        )
        return False, "Unexpected Telegram response"

    if response.status_code >= 400 or not data.get("ok"):
        description = str(data.get("description") or f"HTTP {response.status_code}")
        logger.warning("Telegram sendMessage failed: %s", description)
        return False, description

    logger.info("Telegram message sent to chat_id=%s", chat_id)
    return True, None
