from app.config import (
    ASK_RERANK_TOP_K,
    RERANK_SCORE_MARGIN,
    SEARCH_RERANK_TOP_K,
    VECTOR_TOP_K,
)
from app.embeddings.qwen import embed_query
from app.reranking.cross_encoder import rerank
from app.vectorstore.chroma import search


def retrieve_ranked_chunks(
    query: str,
    document_id: str | None = None,
    vector_top_k: int = VECTOR_TOP_K,
    rerank_top_k: int = SEARCH_RERANK_TOP_K,
    score_margin: float = RERANK_SCORE_MARGIN,
):
    """
    Shared retrieval path for /search and /ask:

    query → embedding → Chroma top-N → rerank → top-K hits
    """
    query_embedding = embed_query(query)
    print("Query embedding generated.")

    results = search(
        query_embedding,
        top_k=vector_top_k,
        document_id=document_id,
    )

    documents = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    print(f"Vector search returned {len(documents)} candidates.")

    if not documents:
        return []

    ranked = rerank(
        query,
        documents,
        top_k=rerank_top_k,
        score_margin=score_margin,
    )

    print(f"Reranked to {len(ranked)} results.")

    output = []
    for index, rerank_score in ranked:
        output.append({
            "text": documents[index],
            "distance": distances[index],
            "rerank_score": float(rerank_score),
            "metadata": metadatas[index],
        })

    return output


def build_ask_context(ranked_chunks):
    """Build Groq context string and /ask sources payload."""
    context_parts = []
    sources = []

    for chunk in ranked_chunks:
        metadata = chunk["metadata"]
        context_parts.append(chunk["text"])
        sources.append({
            "source": metadata.get("source"),
            "page": metadata.get("page"),
            "chunk_index": metadata.get("chunk_index"),
            "distance": float(chunk["distance"]),
            "rerank_score": float(chunk["rerank_score"]),
        })

    context = "\n\n---\n\n".join(context_parts)
    return context, sources


def retrieve_for_search(query: str, document_id: str | None = None):
    return retrieve_ranked_chunks(
        query=query,
        document_id=document_id,
        vector_top_k=VECTOR_TOP_K,
        rerank_top_k=SEARCH_RERANK_TOP_K,
        score_margin=RERANK_SCORE_MARGIN,
    )


def retrieve_for_ask(query: str, document_id: str | None = None):
    return retrieve_ranked_chunks(
        query=query,
        document_id=document_id,
        vector_top_k=VECTOR_TOP_K,
        rerank_top_k=ASK_RERANK_TOP_K,
        score_margin=RERANK_SCORE_MARGIN,
    )
