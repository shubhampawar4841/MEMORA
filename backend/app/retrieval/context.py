"""Unified context builder for any retrieval provider."""

from __future__ import annotations

import time
from typing import Any

from app.retrieval.types import RetrievalHit, to_legacy_chunk


def build_context(
    hits: list[RetrievalHit] | list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Build LLM context + UI sources from normalized or legacy hits.
    """
    start = time.perf_counter()

    legacy: list[dict[str, Any]] = []
    for hit in hits:
        if isinstance(hit, dict) and "provider" in hit and "score" in hit:
            legacy.append(to_legacy_chunk(hit))  # type: ignore[arg-type]
        elif isinstance(hit, dict) and "metadata" in hit and "text" in hit:
            legacy.append(hit)
        else:
            legacy.append(to_legacy_chunk(hit))  # type: ignore[arg-type]

    context_parts: list[str] = []
    sources: list[dict[str, Any]] = []

    for chunk in legacy:
        metadata = chunk.get("metadata") or {}
        source = metadata.get("source", "Unknown document")
        page = metadata.get("page", "Unknown")
        chunk_index = metadata.get("chunk_index", "Unknown")
        folder = metadata.get("folder", "other")
        provider = metadata.get("provider", "local")

        context_parts.append(
            f"[Document: {source} | "
            f"Folder: {folder} | "
            f"Page: {page} | "
            f"Chunk: {chunk_index}]\n"
            f"{chunk.get('text') or ''}"
        )

        sources.append(
            {
                "source": source,
                "page": page,
                "chunk_index": chunk_index,
                "folder": folder,
                "provider": provider,
                "distance": float(chunk.get("distance", 0.0)),
                "rerank_score": float(chunk.get("rerank_score", 0.0)),
                "text": chunk.get("text"),
            }
        )

    context = "\n\n---\n\n".join(context_parts)
    elapsed = time.perf_counter() - start
    print(f"Context construction: {elapsed:.3f}s")
    return context, sources
