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


def _screenshot_ref(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value.startswith("data:"):
            return {"type": "inline_data_uri", "note": "binary omitted", "length": len(value)}
        return {"type": "url", "url": value}
    if isinstance(value, dict):
        return {
            "type": "object",
            "url": value.get("url") or value.get("src"),
            "note": "binary omitted",
        }
    return {"type": type(value).__name__, "note": "reference only"}


def _screenshot(args: dict[str, Any]) -> dict[str, Any]:
    tool = "screenshot"
    url = (args.get("url") or "").strip()
    if not url:
        return fail(tool, "url is required")
    if not _valid_url(url):
        return fail(tool, f"Invalid URL: {url}")

    full_page = bool(args.get("full_page") or args.get("fullPage") or False)

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: screenshot")
        doc = client.scrape(
            url,
            formats=[{"type": "screenshot", "full_page": full_page}],
            only_main_content=False,
        )
        logger.info("Tool completed: screenshot")
        data = document_to_dict(doc)
        metadata = data.get("metadata") or {}
        return ok(
            tool,
            {
                "url": url,
                "screenshot": _screenshot_ref(data.get("screenshot")),
                "metadata": {
                    "title": metadata.get("title"),
                    "scrape_id": metadata.get("scrape_id") or metadata.get("scrapeId"),
                },
            },
            url=url,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("screenshot failed")
        return fail(tool, f"Unable to capture screenshot: {exc}", url=url)


screenshot_tool = AgentTool(
    name="screenshot",
    description="Capture page screenshot metadata (no binary).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "full_page": {"type": "boolean", "default": False},
        },
        "required": ["url"],
    },
    execute=_screenshot,
    status_message="Capturing screenshot…",
)
