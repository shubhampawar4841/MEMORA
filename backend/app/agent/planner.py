from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from app.agent.prompts import PLANNER_SYSTEM_PROMPT
from app.config import GROQ_MODEL_NAME
from app.llm import client as groq_client

logger = logging.getLogger("nerva.agent.planner")

Route = Literal["rag", "web", "hybrid", "ingest_web"]

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

_WEB_HINTS = (
    "search the web",
    "google",
    "browse",
    "go to",
    "open this",
    "open the website",
    "scrape",
    "crawl",
    "pricing page",
    "on the internet",
    "online",
    "latest",
    "current",
    "job",
    "jobs",
    "click",
    "fill",
    "screenshot",
)

_INGEST_HINTS = (
    "add this website to my knowledge",
    "add this site to my knowledge",
    "add to my knowledge base",
    "ingest this website",
    "index this website",
    "save this page to my knowledge",
    "add this url to my knowledge",
)

_HYBRID_HINTS = (
    "compare",
    "using my docs",
    "using my documents",
    "from my pdf",
    "and the website",
    "vs the live",
    "versus the",
)


def _heuristic_route(message: str) -> Route | None:
    lower = message.lower().strip()
    if any(h in lower for h in _INGEST_HINTS):
        return "ingest_web"
    if _URL_RE.search(message) and any(h in lower for h in _HYBRID_HINTS):
        return "hybrid"
    if any(h in lower for h in _HYBRID_HINTS) and (
        _URL_RE.search(message) or any(h in lower for h in _WEB_HINTS)
    ):
        return "hybrid"
    if _URL_RE.search(message) or any(h in lower for h in _WEB_HINTS):
        return "web"
    return None


def plan_route(
    message: str,
    *,
    document_id: str | None = None,
    force_web: bool = False,
) -> dict[str, Any]:
    """Return {"route": Route, "reason": str}."""
    if force_web:
        return {"route": "web", "reason": "Client requested agent/web mode"}

    heuristic = _heuristic_route(message)
    if heuristic:
        logger.info("Planner heuristic route=%s", heuristic)
        return {"route": heuristic, "reason": "Matched web/ingest heuristics"}

    # Document-scoped chat without web cues stays on RAG.
    if document_id and not _URL_RE.search(message):
        return {
            "route": "rag",
            "reason": "Document-scoped query without web intent",
        }

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=120,
        )
        content = (response.choices[0].message.content or "").strip()
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            route = data.get("route")
            if route in {"rag", "web", "hybrid", "ingest_web"}:
                logger.info("Planner LLM route=%s", route)
                return {
                    "route": route,
                    "reason": data.get("reason") or "LLM routing",
                }
    except Exception:  # noqa: BLE001
        logger.exception("Planner LLM failed; defaulting")

    return {"route": "rag", "reason": "Default to RAG"}
