from __future__ import annotations

import json
import sys

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import MIN_RERANK_SCORE
from app.schemas.chat import (
    AskResponse,
    AppendMessagesRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationRename,
    ConversationsResponse,
)
from app.services import conversations as conversation_service
from app.services.generation import generate_answer, stream_answer
from app.services.retrieval import (
    build_ask_context,
    retrieve_for_ask,
)


router = APIRouter(tags=["chat"])


INSUFFICIENT = (
    "I don't have enough information in the provided documents."
)


# ============================================================
# SAFE UTF-8 LOGGING
# ============================================================

def _safe_print(value: object = "") -> None:
    """
    Safely print text on Windows.

    Some PDFs contain Unicode characters that Windows cp1252
    cannot encode. A normal print() can therefore crash the
    entire request.

    This function guarantees that diagnostic logging will never
    crash the application because of an encoding issue.
    """

    text = str(value)

    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"

        try:
            safe_text = text.encode(
                encoding,
                errors="replace",
            ).decode(
                encoding,
                errors="replace",
            )
            print(safe_text)
        except Exception:
            # Last-resort fallback.
            print(
                text.encode(
                    "ascii",
                    errors="replace",
                ).decode(
                    "ascii",
                    errors="replace",
                )
            )


def _print_retrieval_debug(ranked):
    """
    Print the final chunks that survived retrieval + reranking.

    This is temporary diagnostic logging so we can determine
    whether relevant information is being removed before
    generation.

    IMPORTANT:
    Never use raw print() for retrieved PDF text.
    PDF text may contain characters that Windows cp1252
    cannot encode.
    """

    _safe_print("\n========== RETRIEVAL DEBUG ==========")

    if not ranked:
        _safe_print("No ranked chunks returned.")
        _safe_print("========== END RETRIEVAL DEBUG ==========\n")
        return

    for rank, chunk in enumerate(ranked, start=1):

        metadata = chunk.get("metadata") or {}

        _safe_print(f"\n--- Rank {rank} ---")

        try:
            rerank_score = float(
                chunk.get("rerank_score", 0.0)
            )
        except (TypeError, ValueError):
            rerank_score = 0.0

        _safe_print(
            f"Rerank score: {rerank_score:.4f}"
        )

        try:
            distance = float(
                chunk.get("distance", 0.0)
            )
        except (TypeError, ValueError):
            distance = 0.0

        _safe_print(
            f"Distance: {distance:.4f}"
        )

        _safe_print(
            f"Source: {metadata.get('source')}"
        )

        _safe_print(
            f"Page: {metadata.get('page')}"
        )

        _safe_print(
            f"Chunk: {metadata.get('chunk_index')}"
        )

        text = chunk.get("text") or ""

        _safe_print("Text:")
        _safe_print(str(text)[:1000])

    _safe_print(
        "\n========== END RETRIEVAL DEBUG ==========\n"
    )


def _print_context_debug(context):
    """
    Print the exact context that will be sent to Groq.

    Uses safe UTF-8 logging so arbitrary PDF characters
    cannot crash the request.
    """

    _safe_print("\n========== CONTEXT DEBUG ==========")
    _safe_print(context)
    _safe_print("========== END CONTEXT DEBUG ==========\n")


# ============================================================
# NORMAL ASK
# ============================================================

def _run_ask(
    query: str,
    document_id: str | None = None,
    *,
    document_ids: list[str] | None = None,
    folder: str | None = None,
):
    import time

    from app.config import RAG_PROVIDER

    total_start = time.perf_counter()
    _safe_print(f"RAG_PROVIDER={RAG_PROVIDER}")

    retrieve_start = time.perf_counter()
    ranked = retrieve_for_ask(
        query,
        document_id=document_id,
        document_ids=document_ids,
        folder=folder,
    )
    retrieve_ms = (time.perf_counter() - retrieve_start) * 1000
    _safe_print(f"Retrieval wall time: {retrieve_ms:.0f} ms")

    # --------------------------------------------------------
    # TEMPORARY RETRIEVAL DEBUG
    # --------------------------------------------------------

    _print_retrieval_debug(ranked)

    # --------------------------------------------------------
    # No retrieval results
    # --------------------------------------------------------

    if not ranked:
        _safe_print(
            "No ranked chunks found. "
            "Skipping generation."
        )

        return {
            "query": query,
            "document_id": document_id,
            "answer": INSUFFICIENT,
            "sources": [],
        }

    # --------------------------------------------------------
    # Confidence check
    # --------------------------------------------------------

    max_score = max(
        float(chunk["rerank_score"])
        for chunk in ranked
    )

    _safe_print(
        f"Best rerank score: {max_score:.4f}"
    )

    _safe_print(
        f"Minimum required score: "
        f"{MIN_RERANK_SCORE:.4f}"
    )

    if max_score < MIN_RERANK_SCORE:

        _safe_print(
            f"Low confidence ({max_score:.4f}); "
            "skipping generation."
        )

        return {
            "query": query,
            "document_id": document_id,
            "answer": INSUFFICIENT,
            "sources": [],
        }

    # --------------------------------------------------------
    # Build context
    # --------------------------------------------------------

    _safe_print(
        f"Reranked to {len(ranked)} chunks."
    )

    context, sources = build_ask_context(
        ranked
    )

    _safe_print("Context prepared.")

    # --------------------------------------------------------
    # TEMPORARY CONTEXT DEBUG
    # --------------------------------------------------------

    _print_context_debug(context)

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    _safe_print(
        "Sending context to Groq..."
    )

    groq_start = time.perf_counter()
    answer = generate_answer(
        query,
        context,
    )
    groq_ms = (time.perf_counter() - groq_start) * 1000
    total_ms = (time.perf_counter() - total_start) * 1000

    _safe_print(f"Groq: {groq_ms:.0f} ms")
    _safe_print(f"Total ask: {total_ms:.0f} ms")
    _safe_print(
        "Answer generated."
    )

    return {
        "query": query,
        "document_id": document_id,
        "answer": answer,
        "sources": sources,
    }


# ============================================================
# ASK ENDPOINT
# ============================================================

@router.post(
    "/ask",
    response_model=AskResponse,
)
async def ask(
    query: str,
    document_id: str | None = None,
):
    _safe_print("\n========== ASK ==========")

    _safe_print(
        f"Question: {query}"
    )

    if document_id:

        _safe_print(
            f"Document ID: {document_id}"
        )

    else:

        _safe_print(
            "Searching across all documents."
        )

    result = _run_ask(
        query,
        document_id,
    )

    _safe_print(
        "========== ASK COMPLETE ==========\n"
    )

    return result


# ============================================================
# STREAMING ASK
# ============================================================

@router.post(
    "/ask/stream"
)
async def ask_stream(
    query: str,
    document_id: str | None = None,
):
    _safe_print(
        "\n========== ASK STREAM =========="
    )

    _safe_print(
        f"Question: {query}"
    )

    ranked = retrieve_for_ask(
        query,
        document_id,
    )

    # Temporary diagnostic output
    _print_retrieval_debug(ranked)

    async def event_generator():

        try:

            # ------------------------------------------------
            # No retrieval results
            # ------------------------------------------------

            if not ranked:

                payload = {
                    "type": "final",
                    "answer": INSUFFICIENT,
                    "sources": [],
                }

                yield (
                    f"data: "
                    f"{json.dumps(payload, ensure_ascii=False)}\n\n"
                )

                return

            # ------------------------------------------------
            # Confidence check
            # ------------------------------------------------

            max_score = max(
                float(chunk["rerank_score"])
                for chunk in ranked
            )

            _safe_print(
                f"Best rerank score: "
                f"{max_score:.4f}"
            )

            _safe_print(
                f"Minimum required score: "
                f"{MIN_RERANK_SCORE:.4f}"
            )

            if max_score < MIN_RERANK_SCORE:

                payload = {
                    "type": "final",
                    "answer": INSUFFICIENT,
                    "sources": [],
                }

                yield (
                    f"data: "
                    f"{json.dumps(payload, ensure_ascii=False)}\n\n"
                )

                return

            # ------------------------------------------------
            # Build context
            # ------------------------------------------------

            context, sources = build_ask_context(
                ranked
            )

            _safe_print("Context prepared.")

            # Temporary context diagnostic
            _print_context_debug(context)

            # ------------------------------------------------
            # Generate streaming answer
            # ------------------------------------------------

            answer_parts: list[str] = []

            for token in stream_answer(
                query,
                context,
            ):

                answer_parts.append(
                    token
                )

                yield (
                    f"data: "
                    f"{json.dumps(
                        {
                            'type': 'token',
                            'token': token,
                        },
                        ensure_ascii=False,
                    )}\n\n"
                )

            # ------------------------------------------------
            # Final SSE payload
            # ------------------------------------------------

            payload = {
                "type": "final",
                "answer": "".join(
                    answer_parts
                ),
                "sources": sources,
            }

            yield (
                f"data: "
                f"{json.dumps(
                    payload,
                    ensure_ascii=False,
                )}\n\n"
            )

        except Exception as exc:
            # Never allow a generator exception to disappear
            # without sending an SSE error event.

            _safe_print(
                f"Agent/chat stream failed: {exc}"
            )

            payload = {
                "type": "error",
                "error": str(exc),
            }

            yield (
                f"data: "
                f"{json.dumps(
                    payload,
                    ensure_ascii=False,
                )}\n\n"
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# ============================================================
# CONVERSATIONS
# ============================================================

@router.get(
    "/conversations",
    response_model=ConversationsResponse,
)
def list_conversations():

    return {
        "conversations":
            conversation_service.list_conversations()
    }


@router.post(
    "/conversations",
    response_model=ConversationDetail,
)
def create_conversation(
    body: ConversationCreate,
):

    return conversation_service.create_conversation(
        title=body.title,
        document_id=body.document_id,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(
    conversation_id: str,
):

    detail = (
        conversation_service
        .get_conversation(
            conversation_id
        )
    )

    if detail is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return detail


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def rename_conversation(
    conversation_id: str,
    body: ConversationRename,
):

    detail = (
        conversation_service
        .rename_conversation(
            conversation_id,
            body.title,
        )
    )

    if detail is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return detail


@router.delete(
    "/conversations/{conversation_id}"
)
def delete_conversation(
    conversation_id: str,
):

    deleted = (
        conversation_service
        .delete_conversation(
            conversation_id
        )
    )

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {
        "deleted": True,
        "id": conversation_id,
    }


# ============================================================
# CONVERSATION MESSAGES
# ============================================================

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationDetail,
)
def append_conversation_messages(
    conversation_id: str,
    body: AppendMessagesRequest,
):

    convo = (
        conversation_service
        .get_conversation(
            conversation_id
        )
    )

    if convo is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    conversation_service.append_message(
        conversation_id,
        role="user",
        content=body.user_content,
    )

    conversation_service.append_message(
        conversation_id,
        role="assistant",
        content=body.assistant_content,
        sources=[
            s.model_dump()
            for s in body.sources
        ],
    )

    detail = (
        conversation_service
        .get_conversation(
            conversation_id
        )
    )

    if detail is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return detail


# ============================================================
# ASK INSIDE CONVERSATION
# ============================================================

@router.post(
    "/conversations/{conversation_id}/ask",
    response_model=AskResponse,
)
async def ask_in_conversation(
    conversation_id: str,
    query: str,
):

    convo = (
        conversation_service
        .get_conversation(
            conversation_id
        )
    )

    if convo is None:

        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    document_id = convo.get(
        "document_id"
    )

    conversation_service.append_message(
        conversation_id,
        role="user",
        content=query,
    )

    result = _run_ask(
        query,
        document_id,
    )

    conversation_service.append_message(
        conversation_id,
        role="assistant",
        content=result["answer"],
        sources=result["sources"],
    )

    return result