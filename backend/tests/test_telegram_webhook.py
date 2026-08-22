"""Tests for the Telegram webhook / Nerva Supermemory interface."""

from __future__ import annotations

import pytest

from app.services import nerva_telegram as tg
from app.services import telegram_session as session


@pytest.fixture(autouse=True)
def _clear_sessions():
    session.clear_session("927308616")
    yield
    session.clear_session("927308616")


def test_is_authorized_chat(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    assert tg.is_authorized_chat(927308616) is True
    assert tg.is_authorized_chat("927308616") is True
    assert tg.is_authorized_chat(12345) is False


def test_parse_telegram_update_text():
    update = {
        "update_id": 10,
        "message": {
            "message_id": 1,
            "from": {"id": 927308616, "first_name": "Shubham"},
            "chat": {"id": 927308616, "type": "private"},
            "text": "What was I working on yesterday?",
        },
    }
    parsed = tg.parse_telegram_update(update)
    assert parsed is not None
    assert parsed.chat_id == "927308616"
    assert parsed.text == "What was I working on yesterday?"
    assert parsed.attachment is None


def test_parse_telegram_update_document():
    update = {
        "update_id": 11,
        "message": {
            "message_id": 2,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "document": {"file_id": "doc123", "file_name": "notes.pdf"},
        },
    }
    parsed = tg.parse_telegram_update(update)
    assert parsed is not None
    assert parsed.attachment is not None
    assert parsed.attachment.filename == "notes.pdf"


def test_is_upload_intent():
    assert tg.is_upload_intent("upload this to supermemory") is True
    assert tg.is_upload_intent("upload my father's passbook") is True
    assert tg.is_upload_intent("Tell me about Shubham") is False


@pytest.mark.asyncio
async def test_process_unauthorized_update_is_ignored(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    update = {
        "update_id": 11,
        "message": {
            "message_id": 2,
            "from": {"id": 999, "first_name": "Other"},
            "chat": {"id": 999, "type": "private"},
            "text": "hello",
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert result.get("ignored") == "unauthorized"


@pytest.mark.asyncio
async def test_process_document_stores_pending(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    sent: list[str] = []

    async def fake_send(*, chat_id: str, text: str):
        sent.append(text)
        return True, None

    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )

    update = {
        "update_id": 12,
        "message": {
            "message_id": 3,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "document": {"file_id": "doc1", "file_name": "notes.pdf"},
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert sent
    assert "notes.pdf" in sent[0]
    assert session.get_pending("927308616") is not None


@pytest.mark.asyncio
async def test_upload_intent_without_file(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    sent: list[str] = []

    async def fake_send(*, chat_id: str, text: str):
        sent.append(text)
        return True, None

    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )

    update = {
        "update_id": 15,
        "message": {
            "message_id": 6,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "text": "upload this to supermemory",
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert "don't see a file" in sent[0].lower()


@pytest.mark.asyncio
async def test_upload_via_reply_to_document(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    sent: list[str] = []

    async def fake_send(*, chat_id: str, text: str):
        sent.append(text)
        return True, None

    async def fake_download(file_id: str):
        assert file_id == "doc1"
        return b"%PDF-1.4 test"

    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )
    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.download_file",
        fake_download,
    )
    monkeypatch.setattr("app.services.nerva_telegram.sm.is_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.nerva_telegram.sm_sync.sync_telegram_upload",
        lambda **kwargs: {"ok": True, "skipped": False, "error": None},
    )

    update = {
        "update_id": 16,
        "message": {
            "message_id": 7,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "text": "upload this to supermemory",
            "reply_to_message": {
                "message_id": 3,
                "document": {"file_id": "doc1", "file_name": "passbook.pdf"},
            },
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert "Uploaded" in sent[0]


@pytest.mark.asyncio
async def test_photo_with_caption_is_answered(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    sent: list[str] = []

    async def fake_send(*, chat_id: str, text: str):
        sent.append(text)
        return True, None

    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )
    monkeypatch.setattr(
        "app.services.nerva_telegram.answer_from_supermemory",
        lambda query, history=None: f"Answer about: {query}",
    )

    update = {
        "update_id": 14,
        "message": {
            "message_id": 5,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "photo": [{"file_id": "abc", "width": 100, "height": 100}],
            "caption": "Tell me about Shubham",
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert sent == ["Answer about: Tell me about Shubham"]


@pytest.mark.asyncio
async def test_remember_stores_memory(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    stored: list[str] = []

    def fake_add_document(**kwargs):
        stored.append(kwargs["content"])
        return {"ok": True}

    async def fake_send(*, chat_id: str, text: str):
        return True, None

    monkeypatch.setattr("app.services.nerva_telegram.sm.is_configured", lambda: True)
    monkeypatch.setattr("app.services.nerva_telegram.sm.add_document", fake_add_document)
    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )

    update = {
        "update_id": 13,
        "message": {
            "message_id": 4,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "text": "Remember this: Memora Telegram webhook is live.",
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert stored == ["Memora Telegram webhook is live."]


def test_answer_from_supermemory_uses_mcp_context(monkeypatch):
    monkeypatch.setattr("app.services.nerva_telegram.sm_mcp.is_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.nerva_telegram.sm_mcp.search_memory",
        lambda query, include_profile=True: (
            "## Profile\n- Shubham Pawar is a Software Developer Intern at Junoon LLC."
        ),
    )
    monkeypatch.setattr(
        "app.services.nerva_telegram._generate_answer",
        lambda query, context, history=None: (
            "Shubham works at Junoon LLC as a developer intern."
        ),
    )

    reply = tg.answer_from_supermemory("Tell me about shubham")
    assert "Junoon" in reply


@pytest.mark.asyncio
async def test_photo_caption_upload_intent(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    sent: list[str] = []
    upload_titles: list[str | None] = []

    async def fake_send(*, chat_id: str, text: str):
        sent.append(text)
        return True, None

    async def fake_download(file_id: str):
        return b"\xff\xd8\xff fake jpeg"

    def fake_sync(**kwargs):
        upload_titles.append(kwargs.get("title"))
        return {"ok": True, "skipped": False, "error": None}

    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )
    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.download_file",
        fake_download,
    )
    monkeypatch.setattr("app.services.nerva_telegram.sm.is_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.nerva_telegram.sm_sync.sync_telegram_upload",
        fake_sync,
    )

    update = {
        "update_id": 17,
        "message": {
            "message_id": 8,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "photo": [{"file_id": "pic1", "width": 100, "height": 100}],
            "caption": "upload my father's passbook",
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert sent and "Uploaded" in sent[0]
    assert upload_titles == ["my father's passbook"]


@pytest.mark.asyncio
async def test_pending_file_then_upload_text(monkeypatch):
    monkeypatch.setattr("app.config.TELEGRAM_CHAT_ID", "927308616")
    monkeypatch.setattr("app.config.TELEGRAM_BOT_TOKEN", "test-token")

    sent: list[str] = []

    async def fake_send(*, chat_id: str, text: str):
        sent.append(text)
        return True, None

    async def fake_download(file_id: str):
        assert file_id == "doc-pending"
        return b"%PDF-1.4 pending"

    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.send_message",
        fake_send,
    )
    monkeypatch.setattr(
        "app.services.nerva_telegram.telegram_client.download_file",
        fake_download,
    )
    monkeypatch.setattr("app.services.nerva_telegram.sm.is_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.nerva_telegram.sm_sync.sync_telegram_upload",
        lambda **kwargs: {"ok": True, "skipped": False, "error": None},
    )

    file_update = {
        "update_id": 18,
        "message": {
            "message_id": 9,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "document": {"file_id": "doc-pending", "file_name": "passbook.pdf"},
        },
    }
    await tg.process_telegram_update(file_update)
    assert session.get_pending("927308616") is not None

    upload_update = {
        "update_id": 19,
        "message": {
            "message_id": 10,
            "from": {"id": 927308616},
            "chat": {"id": 927308616},
            "text": "upload my father's passbook",
        },
    }
    result = await tg.process_telegram_update(upload_update)
    assert result["ok"] is True
    assert sent[-1] and "Uploaded" in sent[-1]
    assert session.get_pending("927308616") is None


def test_generate_answer_receives_history(monkeypatch):
    captured: dict[str, object] = {}

    def fake_generate(query, context, history=None):
        captured["history"] = history
        return "follow-up answer"

    monkeypatch.setattr("app.services.nerva_telegram.sm_mcp.is_configured", lambda: True)
    monkeypatch.setattr(
        "app.services.nerva_telegram.sm_mcp.search_memory",
        lambda query, include_profile=True: "## Profile\n- Shubham works at Junoon.",
    )
    monkeypatch.setattr(
        "app.services.nerva_telegram._generate_answer",
        fake_generate,
    )

    history = [
        {"role": "user", "content": "Tell me about Shubham"},
        {"role": "assistant", "content": "Shubham is an intern at Junoon."},
    ]
    reply = tg.answer_from_supermemory("What about his job?", history=history)
    assert reply == "follow-up answer"
    assert captured["history"] == history
