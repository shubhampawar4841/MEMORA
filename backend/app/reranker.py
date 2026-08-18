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
    top_k=3
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
        key=lambda x: float(x[1]),
        reverse=True
    )

    return ranked[:top_k]