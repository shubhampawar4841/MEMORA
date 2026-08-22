"""In-memory Telegram chat session — pending files + conversation history."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

Role = Literal["user", "assistant"]

_PENDING_TTL_SECONDS = 15 * 60
_MAX_HISTORY_TURNS = 6

_sessions: dict[str, dict[str, Any]] = {}


@dataclass(frozen=True)
class PendingFile:
    file_id: str
    filename: str
    message_id: int | None = None
    received_at: float = 0.0


def _now() -> float:
    return time.time()


def _chat(chat_id: str) -> dict[str, Any]:
    key = str(chat_id).strip()
    if key not in _sessions:
        _sessions[key] = {"pending": None, "history": []}
    return _sessions[key]


def set_pending(chat_id: str, pending: PendingFile) -> None:
    bucket = _chat(chat_id)
    bucket["pending"] = PendingFile(
        file_id=pending.file_id,
        filename=pending.filename,
        message_id=pending.message_id,
        received_at=_now(),
    )


def get_pending(chat_id: str) -> PendingFile | None:
    bucket = _chat(chat_id)
    pending = bucket.get("pending")
    if not isinstance(pending, PendingFile):
        return None
    if _now() - pending.received_at > _PENDING_TTL_SECONDS:
        bucket["pending"] = None
        return None
    return pending


def clear_pending(chat_id: str) -> None:
    _chat(chat_id)["pending"] = None


def append_history(chat_id: str, role: Role, content: str) -> None:
    text = (content or "").strip()
    if not text:
        return
    bucket = _chat(chat_id)
    history: list[dict[str, str]] = bucket["history"]
    history.append({"role": role, "content": text})
    if len(history) > _MAX_HISTORY_TURNS * 2:
        bucket["history"] = history[-(_MAX_HISTORY_TURNS * 2) :]


def get_history(chat_id: str) -> list[dict[str, str]]:
    bucket = _chat(chat_id)
    history = bucket.get("history") or []
    return [h for h in history if isinstance(h, dict)]


def clear_session(chat_id: str) -> None:
    _sessions.pop(str(chat_id).strip(), None)
