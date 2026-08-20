from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.agent.tools.base import AgentTool, fail, ok
from app.config import AGENT_TOOL_CONTENT_LIMIT
from app.firecrawl.client import (
    document_to_dict,
    get_firecrawl_client,
    truncate_text,
)

logger = logging.getLogger("nerva.agent.tools")


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:  # noqa: BLE001
        return False


def scrape_page_impl(args: dict[str, Any]) -> dict[str, Any]:
    tool = "scrape_page"
    url = (args.get("url") or "").strip()
    if not url:
        return fail(tool, "url is required")
    if not _valid_url(url):
        return fail(tool, f"Invalid URL: {url}")

    formats = args.get("formats") or ["markdown"]
    if not isinstance(formats, list) or not formats:
        formats = ["markdown"]

    only_main = args.get("onlyMainContent")
    if only_main is None:
        only_main = args.get("only_main_content", True)

    kwargs: dict[str, Any] = {
        "formats": formats,
        "only_main_content": bool(only_main),
    }
    wait_for = args.get("waitFor", args.get("wait_for"))
    if wait_for is not None:
        kwargs["wait_for"] = int(wait_for)

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: scrape_page")
        doc = client.scrape(url, **kwargs)
        logger.info("Tool completed: scrape_page")

        data = document_to_dict(doc)
        metadata = data.get("metadata") or {}
        scrape_id = metadata.get("scrape_id") or metadata.get("scrapeId")

        payload = {
            "url": url,
            "markdown": truncate_text(
                data.get("markdown"),
                min(6000, AGENT_TOOL_CONTENT_LIMIT),
            ),
            "links": (data.get("links") or [])[:30],
            "metadata": {
                "title": metadata.get("title"),
                "scrape_id": scrape_id,
                "status_code": metadata.get("status_code"),
            },
            "json": data.get("json"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return ok(tool, payload, url=url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("scrape_page failed")
        return fail(tool, f"Unable to scrape page: {exc}", url=url)


scrape_page_tool = AgentTool(
    name="scrape_page",
    description="Scrape a URL to markdown. metadata.scrape_id enables interact.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "formats": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["markdown"],
            },
            "onlyMainContent": {"type": "boolean", "default": True},
            "waitFor": {"type": "integer"},
        },
        "required": ["url"],
    },
    execute=scrape_page_impl,
    status_message="Reading page…",
)
