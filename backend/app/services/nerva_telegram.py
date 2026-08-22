"""Nerva Telegram interface — Supermemory read, upload, and chat memory."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any

from app.config import GROQ_MODEL_NAME
from app.integrations import telegram_client
from app.services import telegram_session as session
from app.services.file_types import is_allowed_filename, mime_for_filename
from app.supermemory import client as sm
from app.supermemory import mcp_client as sm_mcp
from app.supermemory import sync as sm_sync

logger = logging.getLogger("nerva.telegram")

_REMEMBER_PREFIX = re.compile(
    r"^\s*remember(?:\s+this)?\s*[:\-]?\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)

_UPLOAD_INTENT = re.compile(
    r"(?:\b(?:upload|save|store|add)\b.*\b(?:supermemory|memory|this|file|pdf|passbook|document)\b"
    r"|\bupload\s+this\b"
    r"|\b(?:save|store)\s+this\b)",
    re.IGNORECASE,
)

_GREETINGS = frozenset({"/start", "start", "hi", "hey", "hello"})

_HELP_TRIGGERS = frozenset({"/help", "help", "what can you do"})

_FRIENDLY_FAILURE = (
    "Sorry, I couldn't retrieve that from your memory right now. "
    "Try again in a moment."
)

_NO_FILE_TO_UPLOAD = (
    "I don't see a file to upload. Send the document or photo first, "
    "then reply to that message with \"upload\", or say \"upload\" within "
    "15 minutes of sending the file."
)

_PENDING_FILE_HINT = (
    "Got your file ({filename}). Reply \"upload\" to save it to Supermemory, "
    "or add a caption like \"upload my father's passbook\" on the next file."
)


@dataclass(frozen=True)
class TelegramAttachment:
    file_id: str
    filename: str


@dataclass(frozen=True)
class TelegramInboundMessage:
    update_id: int | None
    message_id: int | None
    chat_id: str
    user_id: str | None
    user_name: str | None
    text: str
    attachment: TelegramAttachment | None
    reply_attachment: TelegramAttachment | None


def authorized_chat_id() -> str | None:
    from app.config import TELEGRAM_CHAT_ID

    chat_id = (TELEGRAM_CHAT_ID or "").strip()
    return chat_id or None


def is_authorized_chat(chat_id: int | str | None) -> bool:
    allowed = authorized_chat_id()
    if not allowed or chat_id is None:
        return False
    return str(chat_id).strip() == allowed


def _attachment_from_message(message: dict[str, Any]) -> TelegramAttachment | None:
    document = message.get("document")
    if isinstance(document, dict) and document.get("file_id"):
        filename = str(document.get("file_name") or "document.bin")
        return TelegramAttachment(
            file_id=str(document["file_id"]),
            filename=filename,
        )

    photos = message.get("photo")
    if isinstance(photos, list) and photos:
        largest = photos[-1]
        if isinstance(largest, dict) and largest.get("file_id"):
            message_id = message.get("message_id") or 0
            return TelegramAttachment(
                file_id=str(largest["file_id"]),
                filename=f"photo_{message_id}.jpg",
            )

    return None


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
    attachment = _attachment_from_message(message)

    reply_attachment = None
    reply_to = message.get("reply_to_message")
    if isinstance(reply_to, dict):
        reply_attachment = _attachment_from_message(reply_to)

    return TelegramInboundMessage(
        update_id=update.get("update_id"),
        message_id=message.get("message_id"),
        chat_id=str(chat_id),
        user_id=str(user_id) if user_id is not None else None,
        user_name=str(user_name) if user_name else None,
        text=text,
        attachment=attachment,
        reply_attachment=reply_attachment,
    )


def is_upload_intent(text: str) -> bool:
    return bool(_UPLOAD_INTENT.search((text or "").strip()))


def _upload_title(text: str, filename: str) -> str:
    cleaned = re.sub(
        r"^\s*(?:please\s+)?(?:upload|save|store|add)\s+(?:this\s+)?(?:to\s+supermemory\s*)?",
        "",
        text.strip(),
        flags=re.IGNORECASE,
    ).strip(" .,:;-")
    if cleaned and len(cleaned) > 2:
        return cleaned
    return filename


def _resolve_upload_target(
    message: TelegramInboundMessage,
) -> TelegramAttachment | None:
    if message.attachment:
        return message.attachment
    if message.reply_attachment:
        return message.reply_attachment
    pending = session.get_pending(message.chat_id)
    if pending:
        return TelegramAttachment(
            file_id=pending.file_id,
            filename=pending.filename,
        )
    return None


async def _upload_attachment(
    *,
    chat_id: str,
    attachment: TelegramAttachment,
    title: str | None = None,
) -> str:
    if not sm.is_configured():
        return "Supermemory is not configured on the server."

    filename = attachment.filename
    if not is_allowed_filename(filename):
        return (
            f"I can't upload `{filename}` yet. Supported types include PDF, "
            "images, txt, md, docx, and csv."
        )

    file_bytes = await telegram_client.download_file(attachment.file_id)
    if not file_bytes:
        return "I couldn't download that file from Telegram. Please try again."

    display = (title or filename).strip()
    result = sm_sync.sync_telegram_upload(
        file_bytes=file_bytes,
        filename=filename,
        title=display,
    )
    if not result.get("ok"):
        logger.warning("Telegram Supermemory upload failed: %s", result.get("error"))
        return _FRIENDLY_FAILURE

    session.clear_pending(chat_id)
    return (
        f"Uploaded \"{display}\" to Supermemory. "
        "Give it a minute to index, then you can ask questions about it."
    )


def _generate_answer(
    query: str,
    context: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    from app.llm import client

    if not sm_mcp.has_usable_context(context):
        return (
            "I couldn't find anything relevant in your Supermemory knowledge "
            "for that question."
        )

    prompt = f"""Answer using ONLY the Supermemory profile and retrieved context below.
The user is Shubham Pawar. First-person phrases refer to Shubham.
Do not invent facts. Do not claim you uploaded, shared, or attached files.
If the context is insufficient, say you couldn't find it.
Keep the answer concise and natural for Telegram.

Supermemory context:
----------------
{context}
----------------

Question:
{query}

Answer:"""

    messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are Nerva, Shubham Pawar's personal memory assistant on Telegram. "
                "You cannot upload files in chat — the user must send files as attachments."
            ),
        },
    ]
    if history:
        messages.extend(history[-12:])
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=GROQ_MODEL_NAME,
        messages=messages,
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


def answer_from_supermemory(
    query: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> str:
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
        return _generate_answer(query, context, history=history)
    except Exception:
        logger.exception("Telegram answer generation failed")
        return _FRIENDLY_FAILURE


async def build_reply(message: TelegramInboundMessage) -> str:
    text = message.text.strip()
    history = session.get_history(message.chat_id)

    # --- File / photo attached to this message ---
    if message.attachment:
        if is_upload_intent(text):
            title = _upload_title(text, message.attachment.filename)
            return await _upload_attachment(
                chat_id=message.chat_id,
                attachment=message.attachment,
                title=title,
            )

        session.set_pending(
            message.chat_id,
            session.PendingFile(
                file_id=message.attachment.file_id,
                filename=message.attachment.filename,
                message_id=message.message_id,
            ),
        )

        if text:
            logger.info("Telegram Supermemory retrieval started (caption)")
            return answer_from_supermemory(text, history=history)

        return _PENDING_FILE_HINT.format(filename=message.attachment.filename)

    # --- Text-only messages ---
    if not text:
        return "Send me a text message or a file and I'll help with Supermemory."

    lowered = text.lower()
    if lowered in _GREETINGS:
        return (
            "Hi Shubham — I'm Nerva on Telegram. Ask about your memories, "
            "send files to upload to Supermemory, or say \"Remember this: …\" "
            "to save a note."
        )

    if lowered in _HELP_TRIGGERS:
        return (
            "I can:\n"
            "• Search your Supermemory knowledge (e.g. \"Tell me about Shubham\")\n"
            "• Upload files — send a PDF/photo, then reply \"upload\" or use a caption\n"
            "• Save notes — \"Remember this: …\"\n"
            "Reply to a file message with \"upload\" for best results on Vercel."
        )

    remember_payload = _remember_text(text)
    if remember_payload:
        ok, reply = _store_memory_note(remember_payload)
        return reply

    if is_upload_intent(text):
        target = _resolve_upload_target(message)
        if not target:
            return _NO_FILE_TO_UPLOAD
        title = _upload_title(text, target.filename)
        return await _upload_attachment(
            chat_id=message.chat_id,
            attachment=target,
            title=title,
        )

    logger.info("Telegram Supermemory retrieval started")
    reply = answer_from_supermemory(text, history=history)
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

    user_text = inbound.text.strip()
    if not user_text and inbound.attachment:
        user_text = f"[file: {inbound.attachment.filename}]"

    try:
        reply = await build_reply(inbound)
    except Exception:
        logger.exception("Telegram processing failed")
        reply = _FRIENDLY_FAILURE

    if user_text:
        session.append_history(inbound.chat_id, "user", user_text)
    session.append_history(inbound.chat_id, "assistant", reply)

    ok, err = await telegram_client.send_message(
        chat_id=inbound.chat_id,
        text=reply,
    )
    if not ok:
        logger.warning("Telegram response failed: %s", err)
        return {"ok": False, "error": "telegram_send_failed"}

    logger.info("Telegram response success chat_id=%s", inbound.chat_id)
    return {"ok": True, "processed": True}
