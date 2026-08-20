from __future__ import annotations

import time

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


def _merge_candidates(
    vector_results,
    keyword_results,
):
    documents = []
    distances = []
    metadatas = []
    seen = set()

    def add_batch(
        batch_docs,
        batch_distances,
        batch_metas,
    ):
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

    v_docs = vector_results.get(
        "documents",
        [[]],
    )[0]

    v_dist = vector_results.get(
        "distances",
        [[]],
    )[0]

    v_meta = vector_results.get(
        "metadatas",
        [[]],
    )[0]

    add_batch(
        v_docs,
        v_dist,
        v_meta,
    )

    k_docs = keyword_results.get(
        "documents",
        [[]],
    )[0]

    k_dist = keyword_results.get(
        "distances",
        [[]],
    )[0]

    k_meta = keyword_results.get(
        "metadatas",
        [[]],
    )[0]

    add_batch(
        k_docs,
        k_dist,
        k_meta,
    )

    return (
        documents,
        distances,
        metadatas,
    )


def retrieve_ranked_chunks(
    query: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
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

    total_start = time.perf_counter()

    print("")
    print("========== RETRIEVAL TIMING ==========")

    # ========================================================
    # 1. QUERY EMBEDDING
    # ========================================================

    start = time.perf_counter()

    query_embedding = embed_query(query)

    embedding_time = (
        time.perf_counter() - start
    )

    print(
        f"Query embedding: "
        f"{embedding_time:.3f}s"
    )

    # ========================================================
    # 2. VECTOR SEARCH
    # ========================================================

    start = time.perf_counter()

    vector_results = search(
        query_embedding,
        top_k=vector_top_k,
        document_id=document_id,
        document_ids=document_ids,
        folder=folder,
    )

    vector_search_time = (
        time.perf_counter() - start
    )

    vector_count = len(
        vector_results.get(
            "documents",
            [[]],
        )[0]
    )

    print(
        f"Vector search: "
        f"{vector_search_time:.3f}s "
        f"({vector_count} results)"
    )

    # ========================================================
    # 3. DETERMINE HYBRID MODE
    # ========================================================

    hybrid = (
        USE_HYBRID_SEARCH
        if use_hybrid is None
        else use_hybrid
    )

    # ========================================================
    # 4. KEYWORD SEARCH
    # ========================================================

    keyword_search_time = 0.0

    if hybrid:

        start = time.perf_counter()

        keyword_results = keyword_search(
            query,
            top_k=KEYWORD_TOP_K,
            document_id=document_id,
            document_ids=document_ids,
            folder=folder,
        )

        keyword_search_time = (
            time.perf_counter() - start
        )

        keyword_count = len(
            keyword_results.get(
                "documents",
                [[]],
            )[0]
        )

        print(
            f"Keyword search: "
            f"{keyword_search_time:.3f}s "
            f"({keyword_count} results)"
        )

        # ====================================================
        # 5. MERGE
        # ====================================================

        start = time.perf_counter()

        (
            documents,
            distances,
            metadatas,
        ) = _merge_candidates(
            vector_results,
            keyword_results,
        )

        merge_time = (
            time.perf_counter() - start
        )

        print(
            f"Candidate merge: "
            f"{merge_time:.3f}s "
            f"({len(documents)} unique candidates)"
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

        merge_time = 0.0

        print(
            f"Hybrid search disabled; "
            f"using {len(documents)} vector candidates."
        )

    # ========================================================
    # 6. NO RESULTS
    # ========================================================

    if not documents:

        total_time = (
            time.perf_counter() - total_start
        )

        print(
            f"Total retrieval: "
            f"{total_time:.3f}s"
        )

        print(
            "===================================="
        )

        return []

    # ========================================================
    # 7. RERANKING
    # ========================================================

    start = time.perf_counter()

    ranked = rerank(
        query,
        documents,
        top_k=rerank_top_k,
        score_margin=score_margin,
        distances=distances,
    )

    rerank_time = (
        time.perf_counter() - start
    )

    print(
        f"BGE reranking: "
        f"{rerank_time:.3f}s "
        f"({len(documents)} -> {len(ranked)})"
    )

    # ========================================================
    # 8. BUILD OUTPUT
    # ========================================================

    start = time.perf_counter()

    output = []

    for index, rerank_score in ranked:

        output.append(
            {
                "text": documents[index],
                "distance": distances[index],
                "rerank_score": float(
                    rerank_score
                ),
                "metadata": metadatas[index],
            }
        )

    output_time = (
        time.perf_counter() - start
    )

    print(
        f"Output formatting: "
        f"{output_time:.3f}s"
    )

    # ========================================================
    # 9. TOTAL
    # ========================================================

    total_time = (
        time.perf_counter() - total_start
    )

    print(
        f"TOTAL RETRIEVAL: "
        f"{total_time:.3f}s"
    )

    print(
        "===================================="
    )

    return output


def build_ask_context(
    ranked_chunks,
):
    """
    Build source-aware context for the LLM.

    Accepts legacy local chunks or normalized provider hits.
    """
    from app.retrieval.context import build_context

    return build_context(ranked_chunks)


def retrieve_for_search(
    query: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
):
    from app.retrieval.factory import search_with_provider
    from app.retrieval.types import to_legacy_chunk

    ids = list(document_ids) if document_ids else []
    if not ids and document_id:
        ids = [document_id]

    hits = search_with_provider(
        query,
        folder=folder,
        document_ids=ids or None,
        top_k=SEARCH_RERANK_TOP_K,
    )
    return [to_legacy_chunk(hit) for hit in hits]


def retrieve_for_ask(
    query: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
):
    from app.retrieval.factory import search_with_provider
    from app.retrieval.types import to_legacy_chunk

    ids = list(document_ids) if document_ids else []
    if not ids and document_id:
        ids = [document_id]

    hits = search_with_provider(
        query,
        folder=folder,
        document_ids=ids or None,
        top_k=ASK_RERANK_TOP_K,
    )
    return [to_legacy_chunk(hit) for hit in hits]


def retrieve_vector_only(
    query: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    folder: str | None = None,
    top_k: int = VECTOR_TOP_K,
):
    """
    Used by evaluation to measure dense retrieval
    before reranking.
    """

    start = time.perf_counter()

    query_embedding = embed_query(query)

    embedding_time = (
        time.perf_counter() - start
    )

    start = time.perf_counter()

    results = search(
        query_embedding,
        top_k=top_k,
        document_id=document_id,
        document_ids=document_ids,
        folder=folder,
    )

    search_time = (
        time.perf_counter() - start
    )

    print(
        f"Vector-only embedding: "
        f"{embedding_time:.3f}s"
    )

    print(
        f"Vector-only search: "
        f"{search_time:.3f}s"
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