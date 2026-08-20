"""Unified tool gateway: local RAG tools + Firecrawl MCP tools."""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.agent.tools.base import AgentTool
from app.agent.tools.rag import rag_search_tool
from app.mcp.firecrawl_client import get_firecrawl_mcp

logger = logging.getLogger("nerva.agent.gateway")

ToolSet = Literal["rag", "web", "hybrid", "all"]

_STATUS: dict[str, str] = {
    "rag_search": "Searching your knowledge base…",
    "search": "Searching the web…",
    "scrape": "Scraping page…",
    "crawl": "Crawling site…",
    "map": "Mapping site URLs…",
    "interact": "Interacting with page…",
}

# Static schemas so we do not open MCP just to list tools (avoids extra
# native/network work on every agent turn; MCP connects on first call_tool).
_FIRECRAWL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search",
        "description": (
            "Search the live web via Firecrawl MCP. Returns ranked results; "
            "follow up with scrape for full page content."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "scrape",
        "description": (
            "Scrape one URL into clean markdown/text via Firecrawl MCP."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Absolute http(s) URL"},
                "formats": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "e.g. markdown, links",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "crawl",
        "description": (
            "Crawl a site starting at a URL via Firecrawl MCP. Use a small limit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "description": "Max pages (keep small, e.g. 5-10)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "map",
        "description": "List URLs under a website via Firecrawl MCP (no page bodies).",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "limit": {"type": "integer"},
                "search": {"type": "string"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "interact",
        "description": (
            "Browser interaction via Firecrawl MCP. Needs scrapeId from a prior "
            "scrape when continuing a session. Ask before consequential actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "scrapeId": {"type": "string"},
                "url": {"type": "string"},
                "prompt": {"type": "string"},
                "code": {"type": "string"},
            },
        },
    },
]


def _openai_schema(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def _local_tools() -> list[AgentTool]:
    return [rag_search_tool]


def openai_tool_schemas(toolset: ToolSet = "hybrid") -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []

    if toolset in {"rag", "hybrid", "all"}:
        for tool in _local_tools():
            schemas.append(tool.openai_schema())

    if toolset in {"web", "hybrid", "all"}:
        for meta in _FIRECRAWL_SCHEMAS:
            schemas.append(
                _openai_schema(
                    meta["name"],
                    meta["description"],
                    meta["parameters"],
                )
            )

    return schemas


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    for tool in _local_tools():
        if tool.name == name:
            return tool.execute(arguments or {})

    if name in {
        "search",
        "scrape",
        "crawl",
        "map",
        "interact",
        "firecrawl_search",
        "firecrawl_scrape",
        "firecrawl_crawl",
        "firecrawl_map",
        "firecrawl_interact",
    }:
        return get_firecrawl_mcp().call_tool(name, arguments or {})

    return {
        "success": False,
        "tool": name or "unknown",
        "error": f"Unknown tool: {name}",
    }


def status_for(name: str) -> str:
    if name in _STATUS:
        return _STATUS[name]
    for tool in _local_tools():
        if tool.name == name:
            return tool.status_message
    return f"Running {name}…"


def toolset_for_route(route: str) -> ToolSet:
    if route == "rag":
        return "rag"
    if route == "web":
        return "web"
    if route == "hybrid":
        return "hybrid"
    return "all"
