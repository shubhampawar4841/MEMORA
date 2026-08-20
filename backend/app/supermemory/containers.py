"""User-scoped Supermemory container tags."""

from __future__ import annotations

import re

from app.config import NERVA_USER_ID, SUPERMEMORY_CONTAINER_TAG

_TAG_RE = re.compile(r"[^a-zA-Z0-9_:-]+")


def slug_user_id(user_id: str | None) -> str:
    raw = (user_id or NERVA_USER_ID or "default").strip() or "default"
    slug = _TAG_RE.sub("_", raw).strip("_")[:80]
    return slug or "default"


def container_tag_for_user(user_id: str | None = None) -> str:
    """
    Isolate each user's memory: Gmail + GitHub + uploads share one tag.

    Example: user_id=\"shubham\" → \"user_shubham\"
    """
    return f"user_{slug_user_id(user_id)}"


def resolve_container_tag(user_id: str | None = None) -> str:
    """
    Prefer an explicit user id → user_<id>.

    When user_id is omitted, use SUPERMEMORY_CONTAINER_TAG (workspace default).
    """
    if user_id and str(user_id).strip():
        return container_tag_for_user(user_id)
    return SUPERMEMORY_CONTAINER_TAG
