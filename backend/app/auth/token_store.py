"""Dev-safe Google OAuth token storage (file-backed, swappable for DB later)."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import BACKEND_ROOT, NERVA_USER_ID

_STORE_DIR = BACKEND_ROOT / "data" / "google_oauth"
_STORE_PATH = _STORE_DIR / "tokens.json"
_lock = threading.Lock()


@dataclass
class GoogleTokenRecord:
    user_id: str
    google_sub: str
    email: str
    name: str | None
    access_token: str
    refresh_token: str | None
    token_type: str
    expires_at: int | None
    scopes: list[str]
    updated_at: str

    def public_view(self) -> dict[str, Any]:
        return {
            "connected": True,
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "scopes": self.scopes,
            "has_refresh_token": bool(self.refresh_token),
            "expires_at": self.expires_at,
            "updated_at": self.updated_at,
        }


def _ensure_store() -> None:
    _STORE_DIR.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text(json.dumps({"users": {}}, indent=2), encoding="utf-8")


def _load() -> dict[str, Any]:
    _ensure_store()
    raw = _STORE_PATH.read_text(encoding="utf-8")
    data = json.loads(raw) if raw.strip() else {"users": {}}
    if not isinstance(data.get("users"), dict):
        data["users"] = {}
    return data


def _save(data: dict[str, Any]) -> None:
    _ensure_store()
    _STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_google_tokens(
    *,
    user_id: str | None,
    google_sub: str,
    email: str,
    name: str | None,
    access_token: str,
    refresh_token: str | None,
    token_type: str,
    expires_in: int | None,
    scopes: list[str],
) -> GoogleTokenRecord:
    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    expires_at: int | None = None
    if expires_in is not None:
        expires_at = int(datetime.now(UTC).timestamp()) + int(expires_in)

    record = GoogleTokenRecord(
        user_id=uid,
        google_sub=google_sub,
        email=email,
        name=name,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=token_type or "Bearer",
        expires_at=expires_at,
        scopes=scopes,
        updated_at=datetime.now(UTC).isoformat(),
    )

    with _lock:
        data = _load()
        users = data["users"]
        existing = users.get(uid) if isinstance(users.get(uid), dict) else None
        if not record.refresh_token and isinstance(existing, dict):
            record.refresh_token = existing.get("refresh_token")

        users[uid] = asdict(record)
        data["users"] = users
        _save(data)

    return record


def get_google_tokens(user_id: str | None = None) -> GoogleTokenRecord | None:
    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    with _lock:
        data = _load()
        raw = data.get("users", {}).get(uid)
    if not isinstance(raw, dict):
        return None
    return GoogleTokenRecord(**raw)


def get_google_connection_status(user_id: str | None = None) -> dict[str, Any]:
    record = get_google_tokens(user_id)
    if not record:
        return {
            "connected": False,
            "user_id": (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID,
        }
    return record.public_view()
