"""Merge local RAG + Firecrawl tool observations into LLM context."""

from __future__ import annotations

import json
from typing import Any

from app.config import AGENT_CONTEXT_CHAR_LIMIT
from app.firecrawl.client import truncate_text


def _snippet_from_result(result: dict[str, Any], limit: int = 2500) -> str:
    if not result.get("success", True):
        err = result.get("error") or "tool failed"
        return f"ERROR: {err}"

    data = result.get("data")
    if data is None:
        return json.dumps(result, default=str)[:limit]

    if isinstance(data, dict):
        if data.get("context"):
            return truncate_text(str(data["context"]), limit) or ""
        if data.get("text"):
            return truncate_text(str(data["text"]), limit) or ""
        if data.get("markdown"):
            return truncate_text(str(data["markdown"]), limit) or ""
        # Prefer compact JSON over dumping huge crawl payloads
        return truncate_text(json.dumps(data, default=str), limit) or ""

    return truncate_text(str(data), limit) or ""


class ContextBuilder:
    """Accumulates evidence from tool calls for the final Groq answer."""

    def __init__(self, char_limit: int = AGENT_CONTEXT_CHAR_LIMIT) -> None:
        self.char_limit = char_limit
        self._parts: list[str] = []
        self.sources: list[dict[str, Any]] = []

    def add_rag_context(self, context: str | None) -> None:
        text = (context or "").strip()
        if not text:
            return
        self._parts.append(f"[local_knowledge]\n{text}")

    def add_tool_result(self, tool_name: str, result: dict[str, Any]) -> None:
        snippet = _snippet_from_result(result)
        if not snippet:
            return
        self._parts.append(f"[{tool_name}]\n{snippet}")

        data = result.get("data")
        if isinstance(data, dict) and isinstance(data.get("sources"), list):
            for src in data["sources"]:
                if isinstance(src, dict):
                    self.sources.append(src)

    def build(self) -> str:
        if not self._parts:
            return ""
        joined = "\n\n---\n\n".join(self._parts)
        return truncate_text(joined, self.char_limit) or ""

    def as_system_message(self) -> dict[str, str] | None:
        body = self.build()
        if not body:
            return None
        return {
            "role": "system",
            "content": (
                "Evidence gathered from tools. Ground your answer only in this "
                "context. Cite URLs or document sources when present.\n\n"
                f"{body}"
            ),
        }
