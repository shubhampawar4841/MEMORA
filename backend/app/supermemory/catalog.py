"""Supermemory-backed document catalog (when local RAG is disabled)."""

from __future__ import annotations

import logging
from typing import Any

from app.folders import normalize_folder
from app.supermemory import client as sm

logger = logging.getLogger("nerva.supermemory.catalog")


def _doc_from_sm(item: dict[str, Any]) -> dict[str, Any] | None:
    meta = item.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}

    document_id = (
        meta.get("document_id")
        or item.get("customId")
        or item.get("id")
    )
    if not document_id:
        return None

    source = (
        meta.get("title")
        or meta.get("source")
        or item.get("title")
        or item.get("customId")
        or str(document_id)
    )
    folder = normalize_folder(meta.get("folder"))

    return {
        "document_id": str(document_id),
        "source": source,
        "folder": folder,
        "pages": [],
        "chunks": int(item.get("chunkCount") or item.get("chunks") or 0),
        "supermemory_id": item.get("id"),
        "status": item.get("status"),
    }


def list_document_records() -> list[dict[str, Any]]:
    """List knowledge docs from Supermemory for the Nerva container."""
    if not sm.is_configured():
        return []

    docs: list[dict[str, Any]] = []
    page = 1
    while page <= 20:
        raw = sm.list_documents(limit=100, page=page)
        batch = raw.get("memories") or raw.get("documents") or []
        if not batch:
            break
        for item in batch:
            if not isinstance(item, dict):
                continue
            mapped = _doc_from_sm(item)
            if mapped:
                docs.append(mapped)
        pagination = raw.get("pagination") or {}
        total_pages = int(pagination.get("totalPages") or page)
        if page >= total_pages:
            break
        page += 1

    return docs


def get_document_record(document_id: str) -> dict[str, Any] | None:
    for doc in list_document_records():
        if doc["document_id"] == document_id:
            return doc
    return None
