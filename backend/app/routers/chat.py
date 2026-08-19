import json

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


def _print_retrieval_debug(ranked):
    """
    Print the final chunks that survived retrieval + reranking.

    This is temporary diagnostic logging so we can determine
    whether relevant information is being removed before generation.
    """

    print("\n========== RETRIEVAL DEBUG ==========")

    if not ranked:
        print("No ranked chunks returned.")
        print("========== END RETRIEVAL DEBUG ==========\n")
        return

    for rank, chunk in enumerate(ranked, start=1):

        metadata = chunk.get("metadata") or {}

        print(f"\n--- Rank {rank} ---")

        print(
            f"Rerank score: "
            f"{float(chunk.get('rerank_score', 0.0)):.4f}"
        )

        print(
            f"Distance: "
            f"{float(chunk.get('distance', 0.0)):.4f}"
        )

        print(
            f"Source: "
            f"{metadata.get('source')}"
        )

        print(
            f"Page: "
            f"{metadata.get('page')}"
        )

        print(
            f"Chunk: "
            f"{metadata.get('chunk_index')}"
        )

        text = chunk.get("text") or ""

        print("Text:")
        print(text[:1000])

    print("\n========== END RETRIEVAL DEBUG ==========\n")


def _print_context_debug(context):
    """
    Print the exact context that will be sent to Groq.
    """

    print("\n========== CONTEXT DEBUG ==========")
    print(context)
    print("========== END CONTEXT DEBUG ==========\n")


def _run_ask(
    query: str,
    document_id: str | None = None,
):
    ranked = retrieve_for_ask(
        query,
        document_id,
    )

    # --------------------------------------------------------
    # TEMPORARY RETRIEVAL DEBUG
    # --------------------------------------------------------

    _print_retrieval_debug(ranked)

    # --------------------------------------------------------
    # No retrieval results
    # --------------------------------------------------------

    if not ranked:
        print(
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

    print(
        f"Best rerank score: "
        f"{max_score:.4f}"
    )

    print(
        f"Minimum required score: "
        f"{MIN_RERANK_SCORE:.4f}"
    )

    if max_score < MIN_RERANK_SCORE:

        print(
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

    print(
        f"Reranked to {len(ranked)} chunks."
    )

    context, sources = build_ask_context(
        ranked
    )

    print("Context prepared.")

    # --------------------------------------------------------
    # TEMPORARY CONTEXT DEBUG
    # --------------------------------------------------------

    _print_context_debug(context)

    # --------------------------------------------------------
    # Generate answer
    # --------------------------------------------------------

    print(
        "Sending context to Groq..."
    )

    answer = generate_answer(
        query,
        context,
    )

    print(
        "Answer generated."
    )

    return {
        "query": query,
        "document_id": document_id,
        "answer": answer,
        "sources": sources,
    }


@router.post(
    "/ask",
    response_model=AskResponse,
)
async def ask(
    query: str,
    document_id: str | None = None,
):
    print("\n========== ASK ==========")

    print(
        f"Question: {query}"
    )

    if document_id:

        print(
            f"Document ID: {document_id}"
        )

    else:

        print(
            "Searching across all documents."
        )

    result = _run_ask(
        query,
        document_id,
    )

    print(
        "========== ASK COMPLETE ==========\n"
    )

    return result


@router.post(
    "/ask/stream"
)
async def ask_stream(
    query: str,
    document_id: str | None = None,
):
    print(
        "\n========== ASK STREAM =========="
    )

    print(
        f"Question: {query}"
    )

    ranked = retrieve_for_ask(
        query,
        document_id,
    )

    # Temporary diagnostic output
    _print_retrieval_debug(ranked)

    async def event_generator():

        if not ranked:

            payload = {
                "type": "final",
                "answer": INSUFFICIENT,
                "sources": [],
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}\n\n"
            )

            return

        max_score = max(
            float(chunk["rerank_score"])
            for chunk in ranked
        )

        print(
            f"Best rerank score: "
            f"{max_score:.4f}"
        )

        if max_score < MIN_RERANK_SCORE:

            payload = {
                "type": "final",
                "answer": INSUFFICIENT,
                "sources": [],
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}\n\n"
            )

            return

        context, sources = build_ask_context(
            ranked
        )

        # Temporary context diagnostic
        _print_context_debug(context)

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
                f"{json.dumps({
                    'type': 'token',
                    'token': token,
                })}\n\n"
            )

        payload = {
            "type": "final",
            "answer": "".join(
                answer_parts
            ),
            "sources": sources,
        }

        yield (
            f"data: "
            f"{json.dumps(payload)}\n\n"
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


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