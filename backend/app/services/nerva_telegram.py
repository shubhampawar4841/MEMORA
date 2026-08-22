"""Nerva Telegram interface — Supermemory read + optional memory writes."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from app.config import GROQ_MODEL_NAME
from app.integrations import telegram_client
from app.supermemory import client as sm
from app.supermemory import mcp_client as sm_mcp

logger = logging.getLogger("nerva.telegram")

_REMEMBER_PREFIX = re.compile(
    r"^\s*remember(?:\s+this)?\s*[:\-]?\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)

_FRIENDLY_FAILURE = (
    "Sorry, I couldn't retrieve that from your memory right now. "
    "Try again in a moment."
)

_DOCUMENT_NOT_IMPLEMENTED = (
    "I can't read files or images from Telegram yet. "
    "Send a text question like \"Tell me about Shubham\", "
    "or add a caption to your photo or file."
)


@dataclass(frozen=True)
class TelegramInboundMessage:
    update_id: int | None
    chat_id: str
    user_id: str | None
    user_name: str | None
    text: str
    has_document: bool
    has_photo: bool


def authorized_chat_id() -> str | None:
    from app.config import TELEGRAM_CHAT_ID

    chat_id = (TELEGRAM_CHAT_ID or "").strip()
    return chat_id or None


def is_authorized_chat(chat_id: int | str | None) -> bool:
    allowed = authorized_chat_id()
    if not allowed or chat_id is None:
        return False
    return str(chat_id).strip() == allowed


def parse_telegram_update(update: dict[str, Any]) -> TelegramInboundMessage | None:
    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
    )
    if not isinstance(message, dict):
        return None

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None

    sender = message.get("from") or {}
    user_id = sender.get("id")
    user_name = sender.get("first_name") or sender.get("username")

    text = (message.get("text") or message.get("caption") or "").strip()
    has_document = bool(message.get("document"))
    has_photo = bool(message.get("photo"))

    return TelegramInboundMessage(
        update_id=update.get("update_id"),
        chat_id=str(chat_id),
        user_id=str(user_id) if user_id is not None else None,
        user_name=str(user_name) if user_name else None,
        text=text,
        has_document=has_document,
        has_photo=has_photo,
    )


def _generate_answer(query: str, context: str) -> str:
    from app.llm import client

    if not sm_mcp.has_usable_context(context):
        return (
            "I couldn't find anything relevant in your Supermemory knowledge "
            "for that question."
        )

    prompt = f"""You are Nerva, Shubham Pawar's personal assistant on Telegram.

The user is Shubham. First-person phrases like "my project", "my work", and
"what was I doing" refer to Shubham.

Answer using ONLY the Supermemory profile and retrieved context below
(same sources as the Nerva voice assistant).
Do not invent facts. If the context is insufficient, say you couldn't find it.
Keep the answer concise and natural for Telegram (about one to four short paragraphs).
Avoid markdown headers, bullet lists, and code blocks unless truly necessary.

Supermemory context:
----------------
{context}
----------------

Question:
{query}

Answer:"""

    response = client.chat.completions.create(
        model=GROQ_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Nerva, Shubham Pawar's personal memory assistant."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=700,
    )
    content = response.choices[0].message.content or ""
    return content.strip() or _FRIENDLY_FAILURE


def _remember_text(text: str) -> str | None:
    match = _REMEMBER_PREFIX.match(text.strip())
    if not match:
        return None
    payload = match.group(1).strip()
    return payload or None


def _store_memory_note(content: str) -> tuple[bool, str]:
    if not sm.is_configured():
        return False, "Supermemory is not configured on the server."

    doc_id = f"telegram_{uuid.uuid4().hex[:12]}"
    try:
        sm.add_document(
            content=content,
            custom_id=doc_id,
            metadata={
                "title": "Telegram note",
                "folder": "personal",
                "source_type": "telegram",
            },
            task_type="memory",
        )
    except sm.SupermemoryError:
        logger.warning("Telegram memory write failed")
        return False, _FRIENDLY_FAILURE

    logger.info("Telegram memory note stored custom_id=%s", doc_id)
    return True, "Got it — I'll remember that."


def answer_from_supermemory(query: str) -> str:
    if not sm_mcp.is_configured():
        logger.warning("Telegram Supermemory MCP not configured")
        return _FRIENDLY_FAILURE

    try:
        context = sm_mcp.search_memory(query, include_profile=True)
    except sm_mcp.SupermemoryMcpError:
        logger.warning("Telegram Supermemory MCP search failed", exc_info=True)
        return _FRIENDLY_FAILURE

    usable = sm_mcp.has_usable_context(context)
    logger.info(
        "Telegram MCP context chars=%s usable=%s query=%r",
        len(context),
        usable,
        query[:80],
    )

    if not usable:
        return (
            "I couldn't find anything relevant in your Supermemory knowledge "
            "for that question."
        )

    try:
        return _generate_answer(query, context)
    except Exception:
        logger.exception("Telegram answer generation failed")
        return _FRIENDLY_FAILURE


def _is_unsupported_attachment(message: TelegramInboundMessage) -> bool:
    return message.has_document or message.has_photo


async def build_reply(message: TelegramInboundMessage) -> str:
    text = message.text.strip()

    if _is_unsupported_attachment(message) and not text:
        return _DOCUMENT_NOT_IMPLEMENTED

    if not text:
        return "Send me a text message and I'll search your Supermemory knowledge."

    if text.lower() in {"/start", "start"}:
        return (
            "Hi Shubham — I'm Nerva on Telegram. Ask about your work, projects, "
            "or memories and I'll search your Supermemory knowledge."
        )

    remember_payload = _remember_text(text)
    if remember_payload:
        ok, reply = _store_memory_note(remember_payload)
        return reply if ok else reply

    logger.info("Telegram Supermemory retrieval started")
    reply = answer_from_supermemory(text)
    logger.info("Telegram Supermemory retrieval finished")
    return reply


async def process_telegram_update(update: dict[str, Any]) -> dict[str, Any]:
    """Process one Telegram update and send a reply when authorized."""
    inbound = parse_telegram_update(update)
    if inbound is None:
        logger.info("Telegram update ignored (no message payload)")
        return {"ok": True, "ignored": "no_message"}

    logger.info(
        "Telegram update received update_id=%s chat_id=%s",
        inbound.update_id,
        inbound.chat_id,
    )

    if not is_authorized_chat(inbound.chat_id):
        logger.warning(
            "Telegram unauthorized chat_id=%s user_id=%s",
            inbound.chat_id,
            inbound.user_id,
        )
        return {"ok": True, "ignored": "unauthorized"}

    if not telegram_client.telegram_configured():
        logger.warning("Telegram bot token missing")
        return {"ok": False, "error": "telegram_not_configured"}

    logger.info("Telegram processing started chat_id=%s", inbound.chat_id)

    try:
        reply = await build_reply(inbound)
    except Exception:
        logger.exception("Telegram processing failed")
        reply = _FRIENDLY_FAILURE

    ok, err = await telegram_client.send_message(
        chat_id=inbound.chat_id,
        text=reply,
    )
    if not ok:
        logger.warning("Telegram response failed: %s", err)
        return {"ok": False, "error": "telegram_send_failed"}

    logger.info("Telegram response success chat_id=%s", inbound.chat_id)
    return {"ok": True, "processed": True}
