"""Centralized Firecrawl hosted-API client (official firecrawl-py SDK)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from firecrawl import Firecrawl

from app.config import FIRECRAWL_API_KEY

logger = logging.getLogger("nerva.firecrawl")


class FirecrawlNotConfiguredError(RuntimeError):
    """Raised when FIRECRAWL_API_KEY is missing."""


@lru_cache(maxsize=1)
def get_firecrawl_client() -> Firecrawl:
    if not FIRECRAWL_API_KEY:
        raise FirecrawlNotConfiguredError(
            "FIRECRAWL_API_KEY is missing. "
            "Add it to the backend .env file."
        )
    logger.info("Firecrawl client initialized")
    return Firecrawl(api_key=FIRECRAWL_API_KEY)


def document_to_dict(doc: Any) -> dict[str, Any]:
    """Normalize a Firecrawl Document (or similar) into a plain dict."""
    if doc is None:
        return {}
    if isinstance(doc, dict):
        return doc
    if hasattr(doc, "model_dump"):
        return doc.model_dump(exclude_none=True)
    if hasattr(doc, "dict"):
        return doc.dict(exclude_none=True)
    return {"value": str(doc)}


def truncate_text(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated {len(text) - limit} chars]"
