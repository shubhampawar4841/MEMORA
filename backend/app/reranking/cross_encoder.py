from sentence_transformers import CrossEncoder

from app.config import (
    RERANK_SCORE_MARGIN,
    RERANKER_MODEL_NAME,
    SEARCH_RERANK_TOP_K,
)

print("Loading reranker...")

reranker = CrossEncoder(RERANKER_MODEL_NAME)

print("Reranker loaded.")


def rerank(
    query,
    documents,
    top_k=SEARCH_RERANK_TOP_K,
    score_margin=RERANK_SCORE_MARGIN,
):
    """
    Rerank candidate documents.

    Returns a list of (candidate_index, score) pairs so callers can
    recover metadata without keying on chunk text.
    """
    if not documents:
        return []

    pairs = [[query, document] for document in documents]
    scores = reranker.predict(pairs)

    ranked = sorted(
        enumerate(scores),
        key=lambda item: item[1],
        reverse=True,
    )

    best_score = float(ranked[0][1])
    filtered = [
        (index, float(score))
        for index, score in ranked
        if best_score - float(score) <= score_margin
    ]

    return filtered[:top_k]
