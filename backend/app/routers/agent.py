from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.orchestrator import iter_agent_events, run_agent
from app.agent.planner import plan_route
from app.config import MIN_RERANK_SCORE
from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    WebIngestRequest,
    WebIngestResponse,
)
from app.services import conversations as conversation_service
from app.services.retrieval import build_ask_context, retrieve_for_ask
from app.services.web_ingest import ingest_web_content
from app.routers.chat import _run_ask

logger = logging.getLogger("nerva.agent.api")

router = APIRouter(prefix="/api/agent", tags=["agent"])

_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def _history_from_conversation(conversation_id: str | None) -> list[dict[str, str]]:
    if not conversation_id:
        return []
    detail = conversation_service.get_conversation(conversation_id)
    if not detail:
        return []
    return [
        {"role": m["role"], "content": m["content"]}
        for m in detail.get("messages") or []
        if m.get("role") in {"user", "assistant"} and m.get("content")
    ]


def _rag_bundle(query: str, document_id: str | None):
    ranked = retrieve_for_ask(query, document_id)
    if not ranked:
        return None, [], None
    max_score = max(float(c["rerank_score"]) for c in ranked)
    if max_score < MIN_RERANK_SCORE:
        return None, [], max_score
    context, sources = build_ask_context(ranked)
    return context, sources, max_score


def _first_url(text: str) -> str | None:
    match = _URL_RE.search(text or "")
    return match.group(0).rstrip(".,);]") if match else None


def _handle_ingest(message: str, document_id: str | None) -> AgentChatResponse:
    url = _first_url(message)
    if not url:
        return AgentChatResponse(
            success=False,
            message=(
                "Please include the website URL you want added to your "
                "knowledge base."
            ),
            route="ingest_web",
        )

    lower = message.lower()
    mode = "scrape"
    if "crawl" in lower:
        mode = "crawl"
    elif "map" in lower or "all pages" in lower or "documentation" in lower:
        mode = "map_scrape"

    result = ingest_web_content(
        url=url,
        mode=mode,
        document_id=document_id,
    )
    if result.get("error"):
        return AgentChatResponse(
            success=False,
            message=result["error"],
            route="ingest_web",
        )

    return AgentChatResponse(
        success=True,
        message=(
            f"Added {result['pages']} page(s) from {result['url']} to your "
            f"knowledge base ({result['chunks']} chunks). "
            f"Document ID: {result['document_id']}"
        ),
        route="ingest_web",
        document_id=result["document_id"],
        steps=[{"tool": "web_ingest", "status": "completed"}],
    )


def _run_routed(body: AgentChatRequest) -> AgentChatResponse:
    history = body.history or _history_from_conversation(body.conversation_id)
    plan = plan_route(
        body.message,
        document_id=body.document_id,
        force_web=body.force_web,
    )
    route = plan["route"]
    logger.info("Agent route=%s reason=%s", route, plan.get("reason"))

    if route == "ingest_web":
        return _handle_ingest(body.message, body.document_id)

    if route == "rag":
        result = _run_ask(body.message, body.document_id)
        return AgentChatResponse(
            success=True,
            message=result["answer"],
            route="rag",
            document_id=result.get("document_id"),
            sources=result.get("sources") or [],
            steps=[{"tool": "rag_retrieve", "status": "completed"}],
        )

    rag_context = None
    sources: list = []
    if route == "hybrid":
        rag_context, sources, _ = _rag_bundle(body.message, body.document_id)

    agent_result = run_agent(
        body.message,
        history=history,
        rag_context=rag_context,
    )

    return AgentChatResponse(
        success=bool(agent_result.get("success", True)),
        message=agent_result.get("message") or "",
        route=route,
        steps=agent_result.get("steps") or [],
        requires_confirmation=bool(
            agent_result.get("requires_confirmation")
        ),
        pending_tool=agent_result.get("pending_tool"),
        pending_arguments=agent_result.get("pending_arguments"),
        conversation_id=body.conversation_id,
        document_id=body.document_id,
        sources=sources,
    )


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(body: AgentChatRequest):
    return _run_routed(body)


@router.post("/chat/stream")
async def agent_chat_stream(body: AgentChatRequest):
    history = body.history or _history_from_conversation(body.conversation_id)
    plan = plan_route(
        body.message,
        document_id=body.document_id,
        force_web=body.force_web,
    )
    route = plan["route"]

    def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'route', 'route': route})}\n\n"

            if route == "ingest_web":
                yield (
                    "data: "
                    f"{json.dumps({'type': 'status', 'message': 'Adding website to knowledge base…'})}\n\n"
                )
                result = _handle_ingest(body.message, body.document_id)
                payload = {
                    "type": "final",
                    "success": result.success,
                    "message": result.message,
                    "route": result.route,
                    "steps": [s.model_dump() for s in result.steps],
                    "requires_confirmation": False,
                    "document_id": result.document_id,
                    "sources": result.sources,
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return

            if route == "rag":
                yield (
                    "data: "
                    f"{json.dumps({'type': 'status', 'message': 'Searching your knowledge…'})}\n\n"
                )
                result = _run_ask(body.message, body.document_id)
                payload = {
                    "type": "final",
                    "success": True,
                    "message": result["answer"],
                    "route": "rag",
                    "steps": [{"tool": "rag_retrieve", "status": "completed"}],
                    "requires_confirmation": False,
                    "document_id": result.get("document_id"),
                    "sources": result.get("sources") or [],
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return

            rag_context = None
            sources: list = []
            if route == "hybrid":
                yield (
                    "data: "
                    f"{json.dumps({'type': 'status', 'message': 'Loading document context…'})}\n\n"
                )
                rag_context, sources, _ = _rag_bundle(
                    body.message,
                    body.document_id,
                )

            for event in iter_agent_events(
                body.message,
                history=history,
                rag_context=rag_context,
            ):
                if event.get("type") == "final":
                    event = {
                        **event,
                        "route": route,
                        "sources": sources,
                        "document_id": body.document_id,
                        "conversation_id": body.conversation_id,
                    }
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent stream failed")
            payload = {
                "type": "final",
                "success": False,
                "message": f"Agent stream error: {exc}",
                "route": route,
                "steps": [],
                "requires_confirmation": False,
            }
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ingest", response_model=WebIngestResponse)
async def agent_ingest(body: WebIngestRequest):
    result = ingest_web_content(
        url=body.url,
        mode=body.mode,
        limit=body.limit,
        search=body.search,
        document_id=body.document_id,
    )
    return WebIngestResponse(**result)
