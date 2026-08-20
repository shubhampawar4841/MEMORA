"""Supermemory SuperRAG retriever."""

from __future__ import annotations

import time
from typing import Any

from app.config import ASK_RERANK_TOP_K
from app.folders import normalize_folder
from app.retrieval.types import RetrievalHit
from app.supermemory import client as sm


def _build_filters(
    *,
    folder: str | None,
    document_ids: list[str] | None,
) -> dict[str, Any] | None:
    conditions: list[dict[str, Any]] = []

    if folder:
        conditions.append(
            {
                "key": "folder",
                "value": normalize_folder(folder),
                "filterType": "metadata",
            }
        )

    if document_ids:
        id_filters = [
            {
                "key": "document_id",
                "value": str(doc_id),
                "filterType": "metadata",
            }
            for doc_id in document_ids
            if doc_id
        ]
        if len(id_filters) == 1:
            conditions.append(id_filters[0])
        elif id_filters:
            conditions.append({"OR": id_filters})

    if not conditions:
        return None
    if len(conditions) == 1:
        only = conditions[0]
        if "OR" in only or "AND" in only:
            return only
        return {"AND": conditions}
    return {"AND": conditions}


def _normalize_result(item: dict[str, Any]) -> RetrievalHit | None:
    text = item.get("chunk") or item.get("memory") or ""
    if not text:
        # Some document-mode payloads nest content differently.
        doc = item.get("document") or {}
        text = doc.get("content") or doc.get("summary") or ""
    if not isinstance(text, str) or not text.strip():
        return None

    metadata = item.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    document = item.get("document") or {}
    if isinstance(document, dict):
        doc_meta = document.get("metadata") or {}
        if isinstance(doc_meta, dict):
            metadata = {**doc_meta, **metadata}

    score = float(item.get("similarity") or item.get("score") or 0.0)
    document_id = (
        metadata.get("document_id")
        or document.get("customId")
        or document.get("id")
        or item.get("documentId")
    )
    source = (
        metadata.get("title")
        or metadata.get("source")
        or document.get("title")
        or document.get("customId")
    )
    folder = normalize_folder(metadata.get("folder"))

    return {
        "text": text.strip(),
        "document_id": str(document_id) if document_id else None,
        "source": source,
        "folder": folder,
        "page": metadata.get("page"),
        "chunk_index": metadata.get("chunk_index"),
        "score": score,
        "provider": "supermemory",
        "distance": max(0.0, 1.0 - score),
        "rerank_score": score,
        "metadata": {
            **metadata,
            "document_id": document_id,
            "source": source,
            "folder": folder,
            "provider": "supermemory",
        },
    }


class SupermemoryRetriever:
    name = "supermemory"

    def search(
        self,
        query: str,
        *,
        folder: str | None = None,
        document_ids: list[str] | None = None,
        top_k: int = ASK_RERANK_TOP_K,
    ) -> list[RetrievalHit]:
        if not sm.is_configured():
            raise sm.SupermemoryError(
                "SUPERMEMORY_API_KEY is not configured"
            )

        start = time.perf_counter()
        filters = _build_filters(
            folder=folder,
            document_ids=document_ids,
        )

        raw = sm.search(
            query=query,
            limit=top_k,
            filters=filters,
            search_mode="documents",
            rerank=True,
        )

        results = raw.get("results") or []
        hits: list[RetrievalHit] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            hit = _normalize_result(item)
            if hit:
                hits.append(hit)

        elapsed = time.perf_counter() - start
        print(
            f"Supermemory retrieval: {elapsed:.3f}s "
            f"({len(hits)} hits)"
        )
        return hits[:top_k]
