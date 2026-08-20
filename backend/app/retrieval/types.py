"""Normalized retrieval result types."""

from __future__ import annotations

from typing import Any, TypedDict


class RetrievalHit(TypedDict, total=False):
    text: str
    document_id: str | None
    source: str | None
    folder: str | None
    page: Any
    chunk_index: Any
    score: float
    provider: str
    distance: float
    rerank_score: float
    metadata: dict[str, Any]


def hit_from_local(chunk: dict[str, Any]) -> RetrievalHit:
    metadata = chunk.get("metadata") or {}
    score = float(chunk.get("rerank_score", 0.0))
    return {
        "text": chunk.get("text") or "",
        "document_id": metadata.get("document_id"),
        "source": metadata.get("source"),
        "folder": metadata.get("folder") or "other",
        "page": metadata.get("page"),
        "chunk_index": metadata.get("chunk_index"),
        "score": score,
        "provider": "local",
        "distance": float(chunk.get("distance", 0.0)),
        "rerank_score": score,
        "metadata": metadata,
    }


def to_legacy_chunk(hit: RetrievalHit) -> dict[str, Any]:
    """Shape expected by existing chat/debug helpers."""
    metadata = dict(hit.get("metadata") or {})
    if hit.get("document_id") is not None:
        metadata.setdefault("document_id", hit.get("document_id"))
    if hit.get("source") is not None:
        metadata.setdefault("source", hit.get("source"))
    if hit.get("folder") is not None:
        metadata.setdefault("folder", hit.get("folder"))
    if hit.get("page") is not None:
        metadata.setdefault("page", hit.get("page"))
    if hit.get("chunk_index") is not None:
        metadata.setdefault("chunk_index", hit.get("chunk_index"))
    metadata.setdefault("provider", hit.get("provider", "local"))

    score = float(hit.get("score", hit.get("rerank_score", 0.0)))
    distance = float(hit.get("distance", max(0.0, 1.0 - score)))

    return {
        "text": hit.get("text") or "",
        "distance": distance,
        "rerank_score": score,
        "metadata": metadata,
    }
