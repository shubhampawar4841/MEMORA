from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.agent.tools.base import AgentTool, fail, ok
from app.config import (
    AGENT_TOOL_CONTENT_LIMIT,
    FIRECRAWL_DEFAULT_CRAWL_LIMIT,
    FIRECRAWL_MAX_CRAWL_LIMIT,
)
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


def _crawl(args: dict[str, Any]) -> dict[str, Any]:
    tool = "crawl_website"
    url = (args.get("url") or "").strip()
    if not url:
        return fail(tool, "url is required")
    if not _valid_url(url):
        return fail(tool, f"Invalid URL: {url}")

    limit = int(args.get("limit") or FIRECRAWL_DEFAULT_CRAWL_LIMIT)
    limit = max(1, min(limit, FIRECRAWL_MAX_CRAWL_LIMIT))

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: crawl_website")
        job = client.crawl(
            url,
            limit=limit,
            scrape_options={"formats": ["markdown"], "only_main_content": True},
        )
        logger.info("Tool completed: crawl_website")

        data = document_to_dict(job)
        pages = data.get("data") or []
        per_page = max(800, min(2000, AGENT_TOOL_CONTENT_LIMIT // max(limit, 1)))
        summarized = []
        for page in pages[:limit]:
            page_data = document_to_dict(page)
            meta = page_data.get("metadata") or {}
            summarized.append(
                {
                    "url": meta.get("source_url") or meta.get("url"),
                    "title": meta.get("title"),
                    "markdown": truncate_text(page_data.get("markdown"), per_page),
                }
            )

        return ok(
            tool,
            {
                "url": url,
                "limit": limit,
                "pages": summarized,
                "count": len(summarized),
                "status": data.get("status"),
            },
            url=url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("crawl_website failed")
        return fail(tool, f"Unable to crawl website: {exc}", url=url)


crawl_website_tool = AgentTool(
    name="crawl_website",
    description="Crawl site pages with a small limit.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "limit": {"type": "integer", "default": FIRECRAWL_DEFAULT_CRAWL_LIMIT},
        },
        "required": ["url"],
    },
    execute=_crawl,
    status_message="Crawling website…",
)
