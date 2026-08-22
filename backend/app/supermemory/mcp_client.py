"""Supermemory MCP HTTP client — same endpoint as the LiveKit voice agent."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import SUPERMEMORY_API_KEY

logger = logging.getLogger("nerva.supermemory.mcp")

SUPERMEMORY_MCP_URL = "https://mcp.supermemory.ai/mcp"

_SSE_DATA_RE = re.compile(r"^data:\s*(.+)$", re.MULTILINE)


class SupermemoryMcpError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool((SUPERMEMORY_API_KEY or "").strip())


def _headers() -> dict[str, str]:
    if not is_configured():
        raise SupermemoryMcpError("SUPERMEMORY_API_KEY is not configured")
    return {
        "Authorization": f"Bearer {SUPERMEMORY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }


def _parse_sse_json(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        match = _SSE_DATA_RE.match(line.strip())
        if match:
            return json.loads(match.group(1))
    raise SupermemoryMcpError("MCP response did not contain SSE data payload")


def call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    timeout: float = 60.0,
) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            SUPERMEMORY_MCP_URL,
            headers=_headers(),
            json=payload,
        )

    if response.status_code >= 400:
        raise SupermemoryMcpError(
            f"MCP call failed ({response.status_code}): {response.text[:500]}"
        )

    data = _parse_sse_json(response.text)
    if data.get("error"):
        raise SupermemoryMcpError(str(data["error"]))

    result = data.get("result") or {}
    content = result.get("content") or []
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())

    if not parts:
        raise SupermemoryMcpError("MCP tool returned no text content")

    return "\n\n".join(parts)


def search_memory(
    query: str,
    *,
    include_profile: bool = True,
    container_tag: str | None = None,
) -> str:
    """
    Call Supermemory MCP search_memory — mirrors app/voice/agent.py MCPToolset.

    Voice does not pass containerTag, so account-wide profile + memories are used.
    """
    args: dict[str, Any] = {
        "query": query,
        "includeProfile": include_profile,
    }
    if container_tag:
        args["containerTag"] = container_tag

    logger.info("Supermemory MCP search_memory query=%r container=%s", query, container_tag)
    return call_tool("search_memory", args)


def has_usable_context(context: str) -> bool:
    text = (context or "").strip()
    if not text:
        return False
    if text.lower() == "no matching memories found.":
        return False
    return True
