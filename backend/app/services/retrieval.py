from app.config import (
    ASK_RERANK_TOP_K,
    KEYWORD_TOP_K,
    RERANK_SCORE_MARGIN,
    SEARCH_RERANK_TOP_K,
    USE_HYBRID_SEARCH,
    VECTOR_TOP_K,
)
from app.embeddings.qwen import embed_query
from app.reranking.cross_encoder import rerank
from app.vectorstore.chroma import keyword_search, search


def _merge_candidates(vector_results, keyword_results):
    documents = []
    distances = []
    metadatas = []
    seen = set()

    def add_batch(batch_docs, batch_distances, batch_metas):
        for i, text in enumerate(batch_docs):
            metadata = batch_metas[i] or {}

            key = (
                text,
                metadata.get("document_id"),
                metadata.get("chunk_index"),
            )

            if key in seen:
                continue

            seen.add(key)

            documents.append(text)

            distances.append(
                batch_distances[i]
                if i < len(batch_distances)
                else 1.0
            )

            metadatas.append(metadata)

    v_docs = vector_results.get("documents", [[]])[0]
    v_dist = vector_results.get("distances", [[]])[0]
    v_meta = vector_results.get("metadatas", [[]])[0]

    add_batch(
        v_docs,
        v_dist,
        v_meta,
    )

    k_docs = keyword_results.get("documents", [[]])[0]
    k_dist = keyword_results.get("distances", [[]])[0]
    k_meta = keyword_results.get("metadatas", [[]])[0]

    add_batch(
        k_docs,
        k_dist,
        k_meta,
    )

    return documents, distances, metadatas


def retrieve_ranked_chunks(
    query: str,
    document_id: str | None = None,
    vector_top_k: int = VECTOR_TOP_K,
    rerank_top_k: int = SEARCH_RERANK_TOP_K,
    score_margin: float = RERANK_SCORE_MARGIN,
    use_hybrid: bool | None = None,
):
    """
    Shared retrieval path:

    query
        ↓
    embedding
        ↓
    vector retrieval
        ↓
    optional keyword retrieval
        ↓
    candidate merge
        ↓
    reranking
        ↓
    final top-K
    """

    query_embedding = embed_query(query)

    print("Query embedding generated.")

    vector_results = search(
        query_embedding,
        top_k=vector_top_k,
        document_id=document_id,
    )

    hybrid = (
        USE_HYBRID_SEARCH
        if use_hybrid is None
        else use_hybrid
    )

    if hybrid:

        keyword_results = keyword_search(
            query,
            top_k=KEYWORD_TOP_K,
            document_id=document_id,
        )

        documents, distances, metadatas = _merge_candidates(
            vector_results,
            keyword_results,
        )

        print(
            f"Hybrid candidates: "
            f"vector={len(vector_results.get('documents', [[]])[0])} "
            f"keyword={len(keyword_results.get('documents', [[]])[0])} "
            f"merged={len(documents)}"
        )

    else:

        documents = vector_results.get(
            "documents",
            [[]],
        )[0]

        distances = vector_results.get(
            "distances",
            [[]],
        )[0]

        metadatas = vector_results.get(
            "metadatas",
            [[]],
        )[0]

        print(
            f"Vector search returned "
            f"{len(documents)} candidates."
        )

    if not documents:
        return []

    ranked = rerank(
        query,
        documents,
        top_k=rerank_top_k,
        score_margin=score_margin,
    )

    print(
        f"Reranked to {len(ranked)} results."
    )

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
    """
    Build source-aware context for the LLM.

    Metadata is included in the context so the model can correctly
    associate information with its originating document.
    """

    context_parts = []
    sources = []

    for chunk in ranked_chunks:

        metadata = chunk["metadata"]

        source = metadata.get(
            "source",
            "Unknown document",
        )

        page = metadata.get(
            "page",
            "Unknown",
        )

        chunk_index = metadata.get(
            "chunk_index",
            "Unknown",
        )

        context_parts.append(
            f"[Document: {source} | "
            f"Page: {page} | "
            f"Chunk: {chunk_index}]\n"
            f"{chunk['text']}"
        )

        sources.append({
            "source": source,
            "page": page,
            "chunk_index": chunk_index,
            "distance": float(
                chunk["distance"]
            ),
            "rerank_score": float(
                chunk["rerank_score"]
            ),
            "text": chunk["text"],
        })

    context = "\n\n---\n\n".join(
        context_parts
    )

    return context, sources


def retrieve_for_search(
    query: str,
    document_id: str | None = None,
):
    return retrieve_ranked_chunks(
        query=query,
        document_id=document_id,
        vector_top_k=VECTOR_TOP_K,
        rerank_top_k=SEARCH_RERANK_TOP_K,
        score_margin=RERANK_SCORE_MARGIN,
    )


def retrieve_for_ask(
    query: str,
    document_id: str | None = None,
):
    return retrieve_ranked_chunks(
        query=query,
        document_id=document_id,
        vector_top_k=VECTOR_TOP_K,
        rerank_top_k=ASK_RERANK_TOP_K,
        score_margin=RERANK_SCORE_MARGIN,
    )


def retrieve_vector_only(
    query: str,
    document_id: str | None = None,
    top_k: int = VECTOR_TOP_K,
):
    """
    Used by evaluation to measure dense retrieval
    before reranking.
    """

    query_embedding = embed_query(query)

    results = search(
        query_embedding,
        top_k=top_k,
        document_id=document_id,
    )

    documents = results.get(
        "documents",
        [[]],
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]],
    )[0]

    distances = results.get(
        "distances",
        [[]],
    )[0]

    return [
        {
            "text": documents[i],
            "metadata": metadatas[i],
            "distance": distances[i],
        }
        for i in range(len(documents))
    ]