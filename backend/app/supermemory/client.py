"""Supermemory HTTP client (server-side only)."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import (
    SUPERMEMORY_API_KEY,
    SUPERMEMORY_BASE_URL,
    SUPERMEMORY_CONTAINER_TAG,
)

logger = logging.getLogger("nerva.supermemory")


class SupermemoryError(RuntimeError):
    """Raised when a Supermemory API call fails."""


def is_configured() -> bool:
    return bool(SUPERMEMORY_API_KEY)


def _headers() -> dict[str, str]:
    if not SUPERMEMORY_API_KEY:
        raise SupermemoryError("SUPERMEMORY_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {SUPERMEMORY_API_KEY}",
    }


def _url(path: str) -> str:
    return f"{SUPERMEMORY_BASE_URL}{path}"


def add_document(
    *,
    content: str,
    custom_id: str,
    metadata: dict[str, Any] | None = None,
    container_tag: str | None = None,
    task_type: str = "superrag",
    timeout: float = 120.0,
) -> dict[str, Any]:
    """POST /v3/documents — text ingest with SuperRAG task type."""
    payload: dict[str, Any] = {
        "content": content,
        "customId": custom_id,
        "containerTag": container_tag or SUPERMEMORY_CONTAINER_TAG,
        "taskType": task_type,
    }
    if metadata:
        payload["metadata"] = metadata

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url("/v3/documents"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"add_document failed ({response.status_code}): {response.text}"
        )
    return response.json()


def upload_file(
    *,
    file_bytes: bytes,
    filename: str,
    custom_id: str,
    metadata: dict[str, Any] | None = None,
    container_tag: str | None = None,
    use_container_tag: bool = True,
    task_type: str = "superrag",
    content_type: str | None = None,
    timeout: float = 180.0,
) -> dict[str, Any]:
    """POST /v3/documents/file — document/file ingest."""
    form: dict[str, Any] = {
        "customId": custom_id,
        "taskType": task_type,
    }
    if use_container_tag:
        form["containerTag"] = container_tag or SUPERMEMORY_CONTAINER_TAG
    if metadata:
        form["metadata"] = json.dumps(metadata)

    mime = content_type or "application/octet-stream"
    files = {
        "file": (filename or "document.bin", file_bytes, mime),
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url("/v3/documents/file"),
            headers=_headers(),
            data=form,
            files=files,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"upload_file failed ({response.status_code}): {response.text}"
        )
    return response.json()


def search(
    *,
    query: str,
    limit: int = 10,
    container_tag: str | None = None,
    filters: dict[str, Any] | None = None,
    search_mode: str = "documents",
    rerank: bool = True,
    threshold: float | None = None,
    include: dict[str, bool] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST /v4/search — modes: documents | memories | hybrid."""
    mode = (search_mode or "documents").strip().lower()
    if mode not in {"documents", "memories", "hybrid"}:
        mode = "documents"

    include_payload = {
        "documents": True,
        "summaries": False,
        "relatedMemories": False,
        "forgottenMemories": False,
    }
    if include:
        include_payload.update(include)

    payload: dict[str, Any] = {
        "q": query,
        "limit": limit,
        "containerTag": container_tag or SUPERMEMORY_CONTAINER_TAG,
        "searchMode": mode,
        "rerank": rerank,
        "include": include_payload,
    }
    if filters:
        payload["filters"] = filters
    if threshold is not None:
        payload["threshold"] = threshold

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url("/v4/search"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"search failed ({response.status_code}): {response.text}"
        )
    return response.json()


def get_profile(
    *,
    container_tag: str | None = None,
    q: str | None = None,
    threshold: float | None = None,
    filters: dict[str, Any] | None = None,
    include: list[str] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST /v4/profile — static + dynamic facts for a container."""
    payload: dict[str, Any] = {
        "containerTag": container_tag or SUPERMEMORY_CONTAINER_TAG,
    }
    if q:
        payload["q"] = q
    if threshold is not None:
        payload["threshold"] = threshold
    if filters:
        payload["filters"] = filters
    if include:
        payload["include"] = include

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url("/v4/profile"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"get_profile failed ({response.status_code}): {response.text}"
        )
    return response.json()


def update_document(
    document_id_or_custom_id: str,
    *,
    metadata: dict[str, Any] | None = None,
    content: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """PATCH /v3/documents/{id} — id may be customId."""
    payload: dict[str, Any] = {}
    if metadata is not None:
        payload["metadata"] = metadata
    if content is not None:
        payload["content"] = content

    with httpx.Client(timeout=timeout) as client:
        response = client.patch(
            _url(f"/v3/documents/{document_id_or_custom_id}"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"update_document failed ({response.status_code}): {response.text}"
        )
    if response.status_code == 204 or not response.content:
        return {"ok": True}
    return response.json()


def delete_document(
    document_id_or_custom_id: str,
    *,
    timeout: float = 60.0,
) -> bool:
    """DELETE /v3/documents/{id} — id may be customId."""
    with httpx.Client(timeout=timeout) as client:
        response = client.delete(
            _url(f"/v3/documents/{document_id_or_custom_id}"),
            headers=_headers(),
        )

    if response.status_code == 404:
        logger.warning(
            "Supermemory document not found for delete: %s",
            document_id_or_custom_id,
        )
        return False
    if response.status_code >= 400:
        raise SupermemoryError(
            f"delete_document failed ({response.status_code}): {response.text}"
        )
    return True


def list_documents(
    *,
    container_tag: str | None = None,
    limit: int = 50,
    page: int = 1,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST /v3/documents/list."""
    payload: dict[str, Any] = {
        "limit": limit,
        "page": page,
        "containerTags": [container_tag or SUPERMEMORY_CONTAINER_TAG],
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url("/v3/documents/list"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code >= 400:
        raise SupermemoryError(
            f"list_documents failed ({response.status_code}): {response.text}"
        )
    return response.json()


# ------------------------------------------------------------
# Connectors (OAuth) — Gmail, GitHub, etc.
# ------------------------------------------------------------

_ALLOWED_PROVIDERS = frozenset({
    "gmail",
    "github",
    "notion",
    "google-drive",
    "onedrive",
    "granola",
    "web-crawler",
    "s3",
})


def create_connection(
    provider: str,
    *,
    redirect_url: str,
    container_tag: str | None = None,
    document_limit: int | None = 5000,
    metadata: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """
    POST /v3/connections/{provider}

    Returns authLink for OAuth providers (gmail, github, …).
    Supermemory owns the OAuth app — we do not store Gmail/GitHub keys.
    """
    provider = (provider or "").strip().lower()
    if provider not in _ALLOWED_PROVIDERS:
        raise SupermemoryError(f"Unsupported connector provider: {provider}")

    tag = container_tag or SUPERMEMORY_CONTAINER_TAG
    payload: dict[str, Any] = {
        "redirectUrl": redirect_url,
        "containerTag": tag,
    }
    if document_limit is not None:
        payload["documentLimit"] = int(document_limit)
    if metadata:
        payload["metadata"] = metadata

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url(f"/v3/connections/{provider}"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"create_connection({provider}) failed "
            f"({response.status_code}): {response.text}"
        )
    return response.json()


def list_connections(
    *,
    container_tag: str | None = None,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """POST /v3/connections/list"""
    tag = container_tag or SUPERMEMORY_CONTAINER_TAG
    payload = {"containerTags": [tag]}

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            _url("/v3/connections/list"),
            headers={**_headers(), "Content-Type": "application/json"},
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"list_connections failed ({response.status_code}): {response.text}"
        )

    data = response.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return (
            data.get("connections")
            or data.get("results")
            or data.get("data")
            or []
        )
    return []


def delete_connection(
    connection_id: str,
    *,
    delete_documents: bool = False,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """DELETE /v3/connections/{id}"""
    params = {"deleteDocuments": "true" if delete_documents else "false"}
    with httpx.Client(timeout=timeout) as client:
        response = client.delete(
            _url(f"/v3/connections/{connection_id}"),
            headers=_headers(),
            params=params,
        )

    if response.status_code >= 400:
        raise SupermemoryError(
            f"delete_connection failed ({response.status_code}): {response.text}"
        )
    if response.status_code == 204 or not response.content:
        return {"id": connection_id, "deleted": True}
    return response.json()
