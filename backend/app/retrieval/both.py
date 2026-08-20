"""Merge local + supermemory hits for RAG_PROVIDER=both."""

from __future__ import annotations

import time

from app.config import ASK_RERANK_TOP_K
from app.retrieval.local import LocalRetriever
from app.retrieval.supermemory import SupermemoryRetriever
from app.retrieval.types import RetrievalHit


def _merge_hits(
    local_hits: list[RetrievalHit],
    sm_hits: list[RetrievalHit],
    top_k: int,
) -> list[RetrievalHit]:
    combined: list[RetrievalHit] = []
    seen: set[tuple[str | None, str]] = set()

    for hit in sorted(
        [*local_hits, *sm_hits],
        key=lambda item: float(item.get("score", 0.0)),
        reverse=True,
    ):
        key = (
            hit.get("document_id"),
            (hit.get("text") or "")[:240],
        )
        if key in seen:
            continue
        seen.add(key)
        combined.append(hit)
        if len(combined) >= top_k:
            break
    return combined


class BothRetriever:
    name = "both"

    def __init__(self) -> None:
        self._local = LocalRetriever()
        self._supermemory = SupermemoryRetriever()

    def search(
        self,
        query: str,
        *,
        folder: str | None = None,
        document_ids: list[str] | None = None,
        top_k: int = ASK_RERANK_TOP_K,
    ) -> list[RetrievalHit]:
        start = time.perf_counter()

        local_hits = self._local.search(
            query,
            folder=folder,
            document_ids=document_ids,
            top_k=top_k,
        )

        sm_hits: list[RetrievalHit] = []
        try:
            sm_hits = self._supermemory.search(
                query,
                folder=folder,
                document_ids=document_ids,
                top_k=top_k,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Supermemory retrieval failed in BOTH mode: {exc}")

        merge_start = time.perf_counter()
        merged = _merge_hits(local_hits, sm_hits, top_k)
        merge_time = time.perf_counter() - merge_start
        total = time.perf_counter() - start

        print(f"Merge: {merge_time:.3f}s ({len(merged)} hits)")
        print(f"Total retrieval: {total:.3f}s")
        return merged
