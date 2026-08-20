from __future__ import annotations

import logging
from typing import Any

from app.agent.tools.base import AgentTool, fail, ok
from app.config import AGENT_TOOL_CONTENT_LIMIT
from app.firecrawl.client import (
    document_to_dict,
    get_firecrawl_client,
    truncate_text,
)

logger = logging.getLogger("nerva.agent.tools")


def _search(args: dict[str, Any]) -> dict[str, Any]:
    tool = "web_search"
    query = (args.get("query") or "").strip()
    if not query:
        return fail(tool, "query is required")

    limit = max(1, min(int(args.get("limit") or 5), 10))

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: web_search")
        results = client.search(query, limit=limit)
        logger.info("Tool completed: web_search")

        web_items = []
        for item in getattr(results, "web", None) or []:
            data = document_to_dict(item)
            meta = data.get("metadata") or {}
            web_items.append(
                {
                    "url": data.get("url")
                    or meta.get("source_url")
                    or meta.get("url"),
                    "title": data.get("title") or meta.get("title"),
                    "description": data.get("description")
                    or meta.get("description"),
                    "markdown": truncate_text(
                        data.get("markdown"),
                        min(2000, AGENT_TOOL_CONTENT_LIMIT // 4),
                    ),
                }
            )

        return ok(
            tool,
            {"query": query, "results": web_items, "count": len(web_items)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("web_search failed")
        return fail(tool, f"Unable to search: {exc}")


web_search_tool = AgentTool(
    name="web_search",
    description="Search the web. Returns titles, URLs, snippets.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    execute=_search,
    status_message="Searching the web…",
)
