"""Local RAG tool (in-process) for the agent tool gateway."""

from __future__ import annotations

from typing import Any

from app.agent.tools.base import AgentTool, fail, ok
from app.config import MIN_RERANK_SCORE
from app.folders import normalize_folder
from app.services.retrieval import build_ask_context, retrieve_for_ask


def _execute_rag_search(arguments: dict[str, Any]) -> dict[str, Any]:
    query = (arguments.get("query") or "").strip()
    if not query:
        return fail("rag_search", "query is required")

    document_id = arguments.get("document_id")
    if document_id is not None:
        document_id = str(document_id).strip() or None

    folder = arguments.get("folder")
    if folder is not None:
        folder = normalize_folder(str(folder))

    raw_ids = arguments.get("document_ids") or []
    document_ids = None
    if isinstance(raw_ids, list) and raw_ids:
        document_ids = [str(i).strip() for i in raw_ids if str(i).strip()]

    try:
        ranked = retrieve_for_ask(
            query,
            document_id=document_id,
            document_ids=document_ids,
            folder=folder,
        )
    except Exception as exc:  # noqa: BLE001
        return fail("rag_search", f"Retrieval failed: {exc}")

    if not ranked:
        return ok(
            "rag_search",
            {
                "chunks": [],
                "context": "",
                "sources": [],
                "count": 0,
            },
            source="local_rag",
        )

    max_score = max(float(c["rerank_score"]) for c in ranked)
    if max_score < MIN_RERANK_SCORE:
        return ok(
            "rag_search",
            {
                "chunks": [],
                "context": "",
                "sources": [],
                "count": 0,
                "max_score": max_score,
                "note": "Retrieval scores below confidence threshold",
            },
            source="local_rag",
        )

    context, sources = build_ask_context(ranked)
    compact_chunks = [
        {
            "text": (c.get("text") or "")[:800],
            "rerank_score": c.get("rerank_score"),
            "document_id": (c.get("metadata") or {}).get("document_id"),
            "page": (c.get("metadata") or {}).get("page"),
            "folder": (c.get("metadata") or {}).get("folder"),
        }
        for c in ranked
    ]
    return ok(
        "rag_search",
        {
            "chunks": compact_chunks,
            "context": context,
            "sources": sources,
            "count": len(ranked),
            "max_score": max_score,
        },
        source="local_rag",
    )


rag_search_tool = AgentTool(
    name="rag_search",
    description=(
        "Search the local knowledge base (uploaded PDFs / ingested pages) "
        "using embeddings + reranking. Use for questions about the user's "
        "documents. Optional document_id, document_ids, or folder scopes "
        "retrieval (folders: personal, work, study, other)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query for the knowledge base",
            },
            "document_id": {
                "type": "string",
                "description": "Optional document id to scope retrieval",
            },
            "document_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of document ids to search",
            },
            "folder": {
                "type": "string",
                "description": "Optional folder: personal, work, study, other",
            },
        },
        "required": ["query"],
    },
    execute=_execute_rag_search,
    status_message="Searching your knowledge base…",
    read_only=True,
)
