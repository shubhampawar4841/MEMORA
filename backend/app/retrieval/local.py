"""Local Chroma + Qwen + BGE retriever (existing pipeline wrapper)."""

from __future__ import annotations

import time

from app.config import ASK_RERANK_TOP_K, RERANK_SCORE_MARGIN, VECTOR_TOP_K
from app.retrieval.types import RetrievalHit, hit_from_local


class LocalRetriever:
    name = "local"

    def search(
        self,
        query: str,
        *,
        folder: str | None = None,
        document_ids: list[str] | None = None,
        top_k: int = ASK_RERANK_TOP_K,
    ) -> list[RetrievalHit]:
        # Lazy import avoids circular import with services.retrieval.
        from app.services.retrieval import retrieve_ranked_chunks

        start = time.perf_counter()

        document_id = None
        ids = document_ids
        if document_ids and len(document_ids) == 1:
            document_id = document_ids[0]
            ids = None

        ranked = retrieve_ranked_chunks(
            query=query,
            document_id=document_id,
            document_ids=ids,
            folder=folder,
            vector_top_k=max(VECTOR_TOP_K, top_k),
            rerank_top_k=top_k,
            score_margin=RERANK_SCORE_MARGIN,
        )

        elapsed = time.perf_counter() - start
        print(f"Local retrieval: {elapsed:.3f}s ({len(ranked)} hits)")

        return [hit_from_local(chunk) for chunk in ranked]
