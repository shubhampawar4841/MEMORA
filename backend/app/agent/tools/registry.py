from __future__ import annotations

from typing import Any

from app.agent.tools.base import AgentTool, fail
from app.agent.tools.crawl import crawl_website_tool
from app.agent.tools.extract import extract_data_tool
from app.agent.tools.interact import interact_with_page_tool
from app.agent.tools.map import map_website_tool
from app.agent.tools.scrape import scrape_page_tool
from app.agent.tools.screenshot import screenshot_tool
from app.agent.tools.search import web_search_tool

_TOOLS: list[AgentTool] = [
    web_search_tool,
    scrape_page_tool,
    map_website_tool,
    crawl_website_tool,
    extract_data_tool,
    interact_with_page_tool,
    screenshot_tool,
]

TOOL_REGISTRY: dict[str, AgentTool] = {t.name: t for t in _TOOLS}


def list_tools() -> list[AgentTool]:
    return list(_TOOLS)


def openai_tool_schemas() -> list[dict[str, Any]]:
    return [t.openai_schema() for t in _TOOLS]


def get_tool(name: str) -> AgentTool | None:
    return TOOL_REGISTRY.get(name)


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = get_tool(name)
    if tool is None:
        return fail(name or "unknown", f"Unknown tool: {name}")
    return tool.execute(arguments or {})


def status_for(name: str) -> str:
    tool = get_tool(name)
    if tool is None:
        return f"Running {name}…"
    return tool.status_message
