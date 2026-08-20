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


def _schema_from_args(args: dict[str, Any]) -> dict[str, Any] | None:
    schema = args.get("schema")
    if not isinstance(schema, dict) or not schema:
        return None
    if "type" in schema or "properties" in schema:
        return schema
    properties = {
        key: {"type": value if isinstance(value, str) else "string"}
        for key, value in schema.items()
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
    }


def _extract(args: dict[str, Any]) -> dict[str, Any]:
    tool = "extract_data"
    urls = args.get("urls") or []
    url = (args.get("url") or "").strip()
    if url:
        urls = [url, *urls]
    urls = [u.strip() for u in urls if isinstance(u, str) and u.strip()]
    if not urls:
        return fail(tool, "url or urls is required")
    for u in urls:
        if not _valid_url(u):
            return fail(tool, f"Invalid URL: {u}")

    prompt = (args.get("prompt") or "").strip() or "Extract structured data."
    schema = _schema_from_args(args)
    formats: list[Any] = [
        {
            "type": "json",
            "prompt": prompt,
            **({"schema": schema} if schema else {}),
        }
    ]

    try:
        client = get_firecrawl_client()
        logger.info("Tool selected: extract_data")
        extracted = []
        for target in urls[:5]:
            doc = client.scrape(
                target,
                formats=formats,
                only_main_content=True,
            )
            data = document_to_dict(doc)
            extracted.append({"url": target, "json": data.get("json")})
        logger.info("Tool completed: extract_data")
        return ok(tool, {"results": extracted})
    except Exception as exc:  # noqa: BLE001
        logger.exception("extract_data failed")
        return fail(tool, f"Unable to extract data: {exc}")


extract_data_tool = AgentTool(
    name="extract_data",
    description="Extract structured JSON from page URL(s).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "urls": {"type": "array", "items": {"type": "string"}},
            "prompt": {"type": "string"},
            "schema": {"type": "object"},
        },
    },
    execute=_extract,
    status_message="Extracting structured data…",
)
