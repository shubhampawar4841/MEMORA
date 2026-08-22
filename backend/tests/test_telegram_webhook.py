"""Tests for the Telegram webhook / Nerva Supermemory interface."""

from __future__ import annotations

import pytest

from app.services import nerva_telegram as tg


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
async def test_process_document_reply(monkeypatch):
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
            "document": {"file_name": "notes.pdf"},
        },
    }

    result = await tg.process_telegram_update(update)
    assert result["ok"] is True
    assert sent
    assert "isn't available yet" in sent[0]


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
