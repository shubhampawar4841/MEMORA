from sentence_transformers import CrossEncoder


MODEL_NAME = "BAAI/bge-reranker-v2-m3"

print("Loading reranker...")

reranker = CrossEncoder(
    MODEL_NAME
)

print("Reranker loaded.")


def rerank(
    query,
    documents,
    top_k=5,
    score_margin=0.25
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