"""Opt-in web page ingest into the existing Chroma knowledge base."""

from __future__ import annotations

import logging
import uuid
from typing import Any
from urllib.parse import urlparse

from app.agent.tools.crawl import crawl_website_tool
from app.agent.tools.map import map_website_tool
from app.agent.tools.scrape import scrape_page_impl
from app.chunking import chunk_text
from app.config import FIRECRAWL_DEFAULT_CRAWL_LIMIT, FIRECRAWL_MAX_CRAWL_LIMIT
from app.embeddings.qwen import embed_texts
from app.vectorstore.chroma import add_documents

logger = logging.getLogger("nerva.web_ingest")


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:  # noqa: BLE001
        return False


def _host_label(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc or url


def ingest_web_content(
    *,
    url: str,
    mode: str = "scrape",
    limit: int | None = None,
    search: str | None = None,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Scrape or crawl a website and store chunks in Chroma.

    mode:
      - scrape: single page
      - map_scrape: map then scrape up to `limit` URLs
      - crawl: Firecrawl crawl with limit
    """
    url = (url or "").strip()
    if not _valid_url(url):
        return {"error": f"Invalid URL: {url}"}

    limit = int(limit or FIRECRAWL_DEFAULT_CRAWL_LIMIT)
    limit = max(1, min(limit, FIRECRAWL_MAX_CRAWL_LIMIT))
    mode = (mode or "scrape").lower()

    pages: list[dict[str, str]] = []

    if mode == "crawl":
        result = crawl_website_tool.execute({"url": url, "limit": limit})
        if not result.get("success"):
            return {"error": result.get("error") or "Crawl failed"}
        for page in (result.get("data") or {}).get("pages") or []:
            md = page.get("markdown") or ""
            if md.strip():
                pages.append(
                    {
                        "url": page.get("url") or url,
                        "title": page.get("title") or "",
                        "markdown": md,
                    }
                )
    elif mode == "map_scrape":
        mapped = map_website_tool.execute(
            {"url": url, "limit": limit, "search": search}
        )
        if not mapped.get("success"):
            return {"error": mapped.get("error") or "Map failed"}
        links = (mapped.get("data") or {}).get("links") or [url]
        for link in links[:limit]:
            scraped = scrape_page_impl(
                {"url": link, "formats": ["markdown"], "onlyMainContent": True}
            )
            if not scraped.get("success"):
                continue
            data = scraped.get("data") or {}
            md = data.get("markdown") or ""
            if md.strip():
                pages.append(
                    {
                        "url": link,
                        "title": (data.get("metadata") or {}).get("title") or "",
                        "markdown": md,
                    }
                )
    else:
        scraped = scrape_page_impl(
            {"url": url, "formats": ["markdown"], "onlyMainContent": True}
        )
        if not scraped.get("success"):
            return {"error": scraped.get("error") or "Scrape failed"}
        data = scraped.get("data") or {}
        md = data.get("markdown") or ""
        if not md.strip():
            return {"error": "No text content found on page"}
        pages.append(
            {
                "url": url,
                "title": (data.get("metadata") or {}).get("title") or "",
                "markdown": md,
            }
        )

    if not pages:
        return {"error": "No pages with content to ingest"}

    chunks: list[str] = []
    metadata: list[dict[str, Any]] = []
    source_label = f"web:{_host_label(url)}"

    for page_index, page in enumerate(pages, start=1):
        page_chunks = chunk_text(page["markdown"])
        for chunk in page_chunks:
            chunks.append(chunk)
            metadata.append(
                {
                    "source": source_label,
                    "page": page_index,
                    "url": page["url"],
                    "title": page.get("title") or "",
                    "content_type": "web",
                }
            )

    if not chunks:
        return {"error": "No chunks were created from web content"}

    logger.info("Embedding %s web chunks for %s", len(chunks), url)
    embeddings = embed_texts(chunks)
    document_id = document_id or str(uuid.uuid4())

    stored = add_documents(
        chunks,
        embeddings,
        metadata,
        document_id=document_id,
    )

    return {
        "document_id": stored["document_id"],
        "source": source_label,
        "url": url,
        "mode": mode,
        "pages": len(pages),
        "chunks": stored["chunks"],
        "embedding_dimension": len(embeddings[0]),
        "error": None,
    }
