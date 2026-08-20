from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from app.agent.tools.base import AgentTool, fail, ok
from app.firecrawl.client import document_to_dict, get_firecrawl_client

logger = logging.getLogger("nerva.agent.tools")


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:  # noqa: BLE001
        return False


def _map(args: dict[str, Any]) -> dict[str, Any]:
    tool = "map_website"
    url = (args.get("url") or "").strip()
    if not url:
        return fail(tool, "url is required")
    if not _valid_url(url):
        return fail(tool, f"Invalid URL: {url}")

    limit = max(1, min(int(args.get("limit") or 50), 100))
    kwargs: dict[str, Any] = {"limit": limit}
    if args.get("search"):
        kwargs["search"] = str(args["search"])

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: map_website")
        result = client.map(url, **kwargs)
        logger.info("Tool completed: map_website")

        data = document_to_dict(result)
        urls: list[str] = []
        for link in data.get("links") or []:
            if isinstance(link, str):
                urls.append(link)
            else:
                dumped = document_to_dict(link)
                href = dumped.get("url") or dumped.get("href")
                if href:
                    urls.append(href)

        return ok(
            tool,
            {"url": url, "links": urls[:limit], "count": len(urls[:limit])},
            url=url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("map_website failed")
        return fail(tool, f"Unable to map website: {exc}", url=url)


map_website_tool = AgentTool(
    name="map_website",
    description="List URLs on a website.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "search": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": ["url"],
    },
    execute=_map,
    status_message="Mapping website…",
)
