"""Select RAG backend from RAG_PROVIDER / LOCAL_RAG_ENABLED."""

from __future__ import annotations

from app.config import LOCAL_RAG_ENABLED, RAG_FALLBACK_TO_LOCAL, RAG_PROVIDER
from app.supermemory import client as sm


class RetrieverError(RuntimeError):
    pass


def get_retriever():
    # Local RAG disabled: always Supermemory (code paths kept, not used).
    if not LOCAL_RAG_ENABLED:
        if not sm.is_configured():
            raise RetrieverError(
                "LOCAL_RAG_ENABLED=false requires SUPERMEMORY_API_KEY."
            )
        from app.retrieval.supermemory import SupermemoryRetriever

        return SupermemoryRetriever()

    provider = RAG_PROVIDER

    if provider == "local":
        from app.retrieval.local import LocalRetriever

        return LocalRetriever()

    if provider == "both":
        from app.retrieval.both import BothRetriever

        return BothRetriever()

    if provider == "supermemory":
        if sm.is_configured():
            from app.retrieval.supermemory import SupermemoryRetriever

            return SupermemoryRetriever()
        if RAG_FALLBACK_TO_LOCAL:
            print(
                "RAG_PROVIDER=supermemory but SUPERMEMORY_API_KEY "
                "missing; falling back to local "
                "(RAG_FALLBACK_TO_LOCAL=true)."
            )
            from app.retrieval.local import LocalRetriever

            return LocalRetriever()
        raise RetrieverError(
            "RAG_PROVIDER=supermemory requires SUPERMEMORY_API_KEY "
            "(or set RAG_FALLBACK_TO_LOCAL=true)."
        )

    from app.retrieval.local import LocalRetriever

    return LocalRetriever()


def search_with_provider(
    query: str,
    *,
    folder: str | None = None,
    document_ids: list[str] | None = None,
    top_k: int,
):
    """
    Run retrieval for the configured provider.

    On supermemory-only failures, optionally fall back to local
    when LOCAL_RAG_ENABLED=true.
    """
    retriever = get_retriever()
    print(f"RAG provider: {retriever.name}")
    print(f"LOCAL_RAG_ENABLED={LOCAL_RAG_ENABLED}")

    try:
        return retriever.search(
            query,
            folder=folder,
            document_ids=document_ids,
            top_k=top_k,
        )
    except Exception as exc:
        if (
            LOCAL_RAG_ENABLED
            and getattr(retriever, "name", None) == "supermemory"
            and RAG_FALLBACK_TO_LOCAL
        ):
            print(
                f"Supermemory retrieval failed ({exc}); "
                "falling back to local "
                "(RAG_FALLBACK_TO_LOCAL=true)."
            )
            from app.retrieval.local import LocalRetriever

            return LocalRetriever().search(
                query,
                folder=folder,
                document_ids=document_ids,
                top_k=top_k,
            )
        raise
