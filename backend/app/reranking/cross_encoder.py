"""Reranking: BGE cross-encoder, or distance fallback on Windows.

Loading SentenceTransformer (Qwen) and CrossEncoder (BGE) in the same
Windows process reliably segfaults (exit 3221225477 / 0xC0000005).
So on win32 we default to vector-distance ranking unless USE_CROSS_ENCODER=true.
"""

from __future__ import annotations

from app.config import (
    RERANK_SCORE_MARGIN,
    RERANKER_MODEL_NAME,
    SEARCH_RERANK_TOP_K,
    USE_CROSS_ENCODER,
)

_reranker = None
_warned_fallback = False


def get_reranker():
    global _reranker
    if not USE_CROSS_ENCODER:
        return None

    if _reranker is None:
        from sentence_transformers import CrossEncoder

        print(f"Loading reranker ({RERANKER_MODEL_NAME})...")
        _reranker = CrossEncoder(
            RERANKER_MODEL_NAME,
            device="cpu",
        )
        print("Reranker loaded.")

    return _reranker


def _rank_by_distance(
    distances: list[float],
    top_k: int,
    score_margin: float,
) -> list[tuple[int, float]]:
    """Higher score = closer match. Chroma distance is lower-is-better."""
    scored = [
        (index, -float(dist))
        for index, dist in enumerate(distances)
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    if not scored:
        return []

    best = scored[0][1]
    filtered = [
        (index, score)
        for index, score in scored
        if best - score <= score_margin
    ]
    return filtered[:top_k]


def rerank(
    query,
    documents,
    top_k=SEARCH_RERANK_TOP_K,
    score_margin=RERANK_SCORE_MARGIN,
    distances: list[float] | None = None,
):
    if not documents:
        return []

    global _warned_fallback

    if not USE_CROSS_ENCODER:
        if not _warned_fallback:
            print(
                "BGE cross-encoder disabled "
                "(USE_CROSS_ENCODER=false; default on Windows). "
                "Ranking by vector distance instead."
            )
            _warned_fallback = True
        if distances is None or len(distances) != len(documents):
            distances = list(range(len(documents)))
        return _rank_by_distance(distances, top_k, score_margin)

    pairs = [[query, document] for document in documents]
    scores = get_reranker().predict(pairs, show_progress_bar=False)

    ranked = sorted(
        enumerate(scores),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    best_score = float(ranked[0][1])
    filtered = [
        (index, float(score))
        for index, score in ranked
        if best_score - float(score) <= score_margin
    ]
    return filtered[:top_k]
