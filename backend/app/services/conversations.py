import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import CHATS_PATH


def _chats_dir() -> Path:
    path = Path(CHATS_PATH)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(conversation_id: str) -> Path:
    return _chats_dir() / f"{conversation_id}.json"


def _read(conversation_id: str) -> dict | None:
    path = _path(conversation_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write(data: dict) -> dict:
    path = _path(data["id"])
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def list_conversations() -> list[dict]:
    conversations = []
    for path in sorted(_chats_dir().glob("*.json"), reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        conversations.append({
            "id": data["id"],
            "title": data.get("title") or "New conversation",
            "document_id": data.get("document_id"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "message_count": len(data.get("messages") or []),
        })
    conversations.sort(key=lambda c: c.get("updated_at") or "", reverse=True)
    return conversations


def create_conversation(
    title: str | None = None,
    document_id: str | None = None,
) -> dict:
    now = _now()
    data = {
        "id": str(uuid.uuid4()),
        "title": title or "New conversation",
        "document_id": document_id,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    return _write(data)


def get_conversation(conversation_id: str) -> dict | None:
    return _read(conversation_id)


def rename_conversation(conversation_id: str, title: str) -> dict | None:
    data = _read(conversation_id)
    if data is None:
        return None
    data["title"] = title.strip() or data["title"]
    data["updated_at"] = _now()
    return _write(data)


def delete_conversation(conversation_id: str) -> bool:
    path = _path(conversation_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def append_message(
    conversation_id: str,
    role: str,
    content: str,
    sources: list | None = None,
) -> dict | None:
    data = _read(conversation_id)
    if data is None:
        return None

    message = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "sources": sources or [],
        "created_at": _now(),
    }
    data.setdefault("messages", []).append(message)
    data["updated_at"] = _now()

    if (
        role == "user"
        and (data.get("title") in (None, "", "New conversation"))
    ):
        data["title"] = content.strip()[:60] or "New conversation"

    return _write(data)
