from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from app.agent.context import ContextBuilder
from app.agent.gateway import execute_tool, openai_tool_schemas, status_for, toolset_for_route
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.agent.safety import gate_tool_call
from app.config import GROQ_MODEL_NAME, MAX_AGENT_STEPS
from app.firecrawl.client import truncate_text
from app.llm import client as groq_client

logger = logging.getLogger("nerva.agent")

StatusCallback = Any
_TOOL_RESULT_LIMIT = 5000


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {"_raw": raw}


def _append_tool_message(
    messages: list[dict[str, Any]],
    tool_call_id: str,
    name: str,
    result: dict[str, Any],
) -> None:
    payload = json.dumps(result, default=str)
    if len(payload) > _TOOL_RESULT_LIMIT:
        payload = payload[:_TOOL_RESULT_LIMIT] + "…[truncated]"
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": payload,
        }
    )


def _history_for_gate(
    message: str,
    history: list[dict[str, str]] | None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = list(history or [])
    items.append({"role": "user", "content": message})
    return items


def _friendly_llm_error(exc: Exception) -> str:
    text = str(exc)
    lower = text.lower()
    if "413" in text or "request too large" in lower or "tokens per minute" in lower:
        return (
            "The web agent request exceeded the current Groq token limit. "
            "Try a shorter question, or wait a minute and retry."
        )
    if "rate_limit" in lower or "429" in text:
        return "The LLM is rate-limited right now. Please wait a moment and try again."
    return f"Agent LLM error: {exc}"


def run_agent(
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    rag_context: str | None = None,
    document_id: str | None = None,
    route: str = "web",
    on_status: StatusCallback | None = None,
) -> dict[str, Any]:
    """
    Planner → MCP client layer (local RAG tools + Firecrawl MCP) → Context Builder → Groq.
    """
    logger.info("Agent started route=%s", route)
    steps: list[dict[str, str]] = []
    context_builder = ContextBuilder()
    if rag_context:
        context_builder.add_rag_context(rag_context)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
    ]

    if rag_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "Knowledge-base context (prefetched):\n"
                    f"{truncate_text(rag_context, 2500)}"
                ),
            }
        )

    if history:
        for item in history[-6:]:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and content:
                messages.append(
                    {
                        "role": role,
                        "content": truncate_text(str(content), 1500) or "",
                    }
                )

    messages.append({"role": "user", "content": message})
    tools = openai_tool_schemas(toolset_for_route(route))
    gate_history = _history_for_gate(message, history)

    for step in range(MAX_AGENT_STEPS):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL_NAME,
                messages=messages,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                temperature=0.2,
                max_tokens=800,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent LLM call failed")
            return {
                "success": False,
                "message": _friendly_llm_error(exc),
                "steps": steps,
                "requires_confirmation": False,
                "sources": context_builder.sources,
            }

        choice = response.choices[0]
        assistant_message = choice.message
        finish_reason = choice.finish_reason
        tool_calls = getattr(assistant_message, "tool_calls", None) or []

        assistant_payload: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_message.content or "",
        }
        if tool_calls:
            assistant_payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in tool_calls
            ]
        messages.append(assistant_payload)

        if tool_calls:
            for tc in tool_calls:
                name = tc.function.name
                arguments = _parse_arguments(tc.function.arguments)
                if name == "rag_search" and document_id and not arguments.get("document_id"):
                    arguments["document_id"] = document_id
                logger.info("Tool selected: %s", name)

                gate = gate_tool_call(name, arguments, gate_history)
                if gate is not None:
                    steps.append({"tool": name, "status": "needs_confirmation"})
                    if on_status:
                        on_status("needs_confirmation", gate["message"])
                    logger.info("Agent paused for confirmation")
                    return {
                        "success": True,
                        "message": gate["message"],
                        "steps": steps,
                        "requires_confirmation": True,
                        "pending_tool": gate.get("pending_tool"),
                        "pending_arguments": gate.get("pending_arguments"),
                        "sources": context_builder.sources,
                    }

                if on_status:
                    on_status("status", status_for(name))

                result = execute_tool(name, arguments)
                status = "completed" if result.get("success") else "failed"
                steps.append({"tool": name, "status": status})
                logger.info("Tool completed: %s (%s)", name, status)
                context_builder.add_tool_result(name, result)
                _append_tool_message(messages, tc.id, name, result)
            continue

        # Final answer path: inject Context Builder evidence once, then answer.
        evidence = context_builder.as_system_message()
        if evidence and not any(
            m.get("role") == "system" and "Evidence gathered from tools" in (m.get("content") or "")
            for m in messages
        ):
            messages.insert(1, evidence)
            if on_status:
                on_status("status", "Building answer from evidence…")
            try:
                synthesis = groq_client.chat.completions.create(
                    model=GROQ_MODEL_NAME,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=800,
                )
                final = (synthesis.choices[0].message.content or "").strip()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Context synthesis failed; using draft answer")
                final = (assistant_message.content or "").strip() or _friendly_llm_error(exc)
        else:
            final = (assistant_message.content or "").strip()
            if not final and finish_reason == "stop":
                final = "I finished the task but had nothing further to report."

        logger.info("Agent completed (step=%s)", step + 1)
        if on_status:
            on_status("status", "Finished.")

        return {
            "success": True,
            "message": final,
            "steps": steps,
            "requires_confirmation": False,
            "sources": context_builder.sources,
        }

    logger.warning("Agent hit MAX_AGENT_STEPS=%s", MAX_AGENT_STEPS)
    return {
        "success": False,
        "message": (
            "I reached the maximum number of agent steps before finishing. "
            "Please narrow the task or confirm the next action."
        ),
        "steps": steps,
        "requires_confirmation": False,
        "sources": context_builder.sources,
    }


def iter_agent_events(
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    rag_context: str | None = None,
    document_id: str | None = None,
    route: str = "web",
) -> Iterator[dict[str, Any]]:
    """Yield status/final event dicts for SSE."""
    collected: list[dict[str, Any]] = []

    def collect(event_type: str, text: str | None) -> None:
        if text:
            collected.append({"type": "status", "message": text})

    result = run_agent(
        message,
        history=history,
        rag_context=rag_context,
        document_id=document_id,
        route=route,
        on_status=collect,
    )

    for event in collected:
        yield event

    yield {
        "type": "final",
        "success": result.get("success", True),
        "message": result.get("message", ""),
        "steps": result.get("steps", []),
        "requires_confirmation": result.get("requires_confirmation", False),
        "pending_tool": result.get("pending_tool"),
        "pending_arguments": result.get("pending_arguments"),
        "sources": result.get("sources") or [],
    }
