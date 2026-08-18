from sentence_transformers import CrossEncoder

from app.config import (
    RERANKER_MODEL_NAME,
    RERANK_SCORE_MARGIN,
    SEARCH_RERANK_TOP_K,
)

print("Loading reranker...")

reranker = CrossEncoder(
    RERANKER_MODEL_NAME
)

print("Reranker loaded.")


def rerank(
    query,
    documents,
    top_k=SEARCH_RERANK_TOP_K,
    score_margin=RERANK_SCORE_MARGIN
):

    if not documents:
        return []

    pairs = [
        [query, document]
        for document in documents
    ]

    scores = reranker.predict(
        pairs
    )

    ranked = sorted(
        zip(documents, scores),
        key=lambda x: x[1],
        reverse=True
    )

    # --------------------------------------------------------
    # Keep the strongest result.
    # --------------------------------------------------------

    best_score = float(ranked[0][1])

    filtered = [
        item
        for item in ranked
        if best_score - float(item[1]) <= score_margin
    ]

    # --------------------------------------------------------
    # Limit final number of chunks.
    # --------------------------------------------------------

    return filtered[:top_k]
