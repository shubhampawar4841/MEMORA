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


def _run_ask(query: str, document_id: str | None = None):
    ranked = retrieve_for_ask(query, document_id)

    if not ranked:
        return {
            "query": query,
            "document_id": document_id,
            "answer": INSUFFICIENT,
            "sources": [],
        }

    max_score = max(float(chunk["rerank_score"]) for chunk in ranked)
    if max_score < MIN_RERANK_SCORE:
        print(f"Low confidence ({max_score:.4f}); skipping generation.")
        return {
            "query": query,
            "document_id": document_id,
            "answer": INSUFFICIENT,
            "sources": [],
        }

    print(f"Reranked to {len(ranked)} chunks.")
    context, sources = build_ask_context(ranked)
    print("Context prepared.")
    print("Sending context to Groq...")
    answer = generate_answer(query, context)
    print("Answer generated.")

    return {
        "query": query,
        "document_id": document_id,
        "answer": answer,
        "sources": sources,
    }


@router.post("/ask", response_model=AskResponse)
async def ask(query: str, document_id: str | None = None):
    print("\n========== ASK ==========")
    print(f"Question: {query}")

    if document_id:
        print(f"Document ID: {document_id}")
    else:
        print("Searching across all documents.")

    result = _run_ask(query, document_id)
    print("========== ASK COMPLETE ==========\n")
    return result


@router.post("/ask/stream")
async def ask_stream(query: str, document_id: str | None = None):
    print("\n========== ASK STREAM ==========")
    print(f"Question: {query}")

    ranked = retrieve_for_ask(query, document_id)

    async def event_generator():
        if not ranked:
            payload = {
                "type": "final",
                "answer": INSUFFICIENT,
                "sources": [],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        max_score = max(float(chunk["rerank_score"]) for chunk in ranked)
        if max_score < MIN_RERANK_SCORE:
            payload = {
                "type": "final",
                "answer": INSUFFICIENT,
                "sources": [],
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        context, sources = build_ask_context(ranked)
        answer_parts: list[str] = []

        for token in stream_answer(query, context):
            answer_parts.append(token)
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        payload = {
            "type": "final",
            "answer": "".join(answer_parts),
            "sources": sources,
        }
        yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/conversations", response_model=ConversationsResponse)
def list_conversations():
    return {"conversations": conversation_service.list_conversations()}


@router.post("/conversations", response_model=ConversationDetail)
def create_conversation(body: ConversationCreate):
    return conversation_service.create_conversation(
        title=body.title,
        document_id=body.document_id,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(conversation_id: str):
    detail = conversation_service.get_conversation(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def rename_conversation(conversation_id: str, body: ConversationRename):
    detail = conversation_service.rename_conversation(
        conversation_id,
        body.title,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    deleted = conversation_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "id": conversation_id}


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationDetail,
)
def append_conversation_messages(
    conversation_id: str,
    body: AppendMessagesRequest,
):
    convo = conversation_service.get_conversation(conversation_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_service.append_message(
        conversation_id,
        role="user",
        content=body.user_content,
    )
    conversation_service.append_message(
        conversation_id,
        role="assistant",
        content=body.assistant_content,
        sources=[s.model_dump() for s in body.sources],
    )

    detail = conversation_service.get_conversation(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.post(
    "/conversations/{conversation_id}/ask",
    response_model=AskResponse,
)
async def ask_in_conversation(conversation_id: str, query: str):
    convo = conversation_service.get_conversation(conversation_id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    document_id = convo.get("document_id")
    conversation_service.append_message(
        conversation_id,
        role="user",
        content=query,
    )

    result = _run_ask(query, document_id)
    conversation_service.append_message(
        conversation_id,
        role="assistant",
        content=result["answer"],
        sources=result["sources"],
    )

    return result
