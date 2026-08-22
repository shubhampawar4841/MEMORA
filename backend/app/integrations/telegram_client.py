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


def _api_url(method: str) -> str | None:
    token = _bot_token()
    if not token:
        return None
    return f"{_TELEGRAM_API_BASE}/bot{token}/{method}"


async def send_message(
    *,
    chat_id: str,
    text: str,
    timeout: float = 30.0,
) -> tuple[bool, str | None]:
    """Send a Telegram message. Returns (ok, error_description)."""
    url = _api_url("sendMessage")
    if not url:
        return False, "Telegram bot token is not configured"

    body = (text or "").strip()
    if not body:
        return False, "Message text is empty"

    if len(body) > _TELEGRAM_MAX_MESSAGE_LENGTH:
        body = body[: _TELEGRAM_MAX_MESSAGE_LENGTH - 3].rstrip() + "..."

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


async def get_file_path(file_id: str, *, timeout: float = 30.0) -> str | None:
    """Resolve Telegram file_id to a download path via getFile."""
    url = _api_url("getFile")
    if not url or not (file_id or "").strip():
        return None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json={"file_id": file_id})
    except httpx.HTTPError:
        logger.warning("Telegram getFile request failed")
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if not data.get("ok"):
        logger.warning("Telegram getFile failed: %s", data.get("description"))
        return None

    result = data.get("result") or {}
    path = result.get("file_path")
    return str(path) if path else None


async def download_file(file_id: str, *, timeout: float = 120.0) -> bytes | None:
    """Download file bytes for a Telegram file_id."""
    token = _bot_token()
    path = await get_file_path(file_id, timeout=timeout)
    if not token or not path:
        return None

    download_url = f"{_TELEGRAM_API_BASE}/file/bot{token}/{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(download_url)
    except httpx.HTTPError:
        logger.warning("Telegram file download failed")
        return None

    if response.status_code >= 400:
        logger.warning("Telegram file download HTTP %s", response.status_code)
        return None

    return response.content
