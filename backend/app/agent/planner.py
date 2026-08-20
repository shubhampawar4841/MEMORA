from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from app.agent.prompts import PLANNER_SYSTEM_PROMPT
from app.config import GROQ_MODEL_NAME
from app.folders import ALLOWED_FOLDERS, normalize_folder
from app.llm import client as groq_client

logger = logging.getLogger("nerva.agent.planner")

Route = Literal["rag", "web", "hybrid", "ingest_web"]

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)

_WEB_HINTS = (
    "search the web",
    "search online",
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
    "recent",
    "today",
    "news",
    "click",
    "fill",
    "screenshot",
)

_INGEST_HINTS = (
    "add this website to my knowledge",
    "add this site to my knowledge",
    "add to my knowledge base",
    "ingest this website",
    "ingest this site",
    "index this website",
    "index this page",
    "save this page to my knowledge",
    "save this website to my knowledge",
    "add this url to my knowledge",
)

_HYBRID_HINTS = (
    "compare",
    "using my docs",
    "using my documents",
    "from my pdf",
    "from my pdfs",
    "and the website",
    "and the web",
    "with the latest",
    "vs the live",
    "versus the live",
    "against the latest",
)

_PERSONAL_HINTS = (
    "resume",
    "cv",
    "skills",
    "my skills",
    "personal",
    "about me",
    "my experience",
    "my education",
    "my projects",
)

_WORK_HINTS = (
    "work related",
    "work-related",
    "at work",
    "my work",
    "internship",
    "office",
    "standup",
    "sprint",
    "jira",
    "ticket",
    "tickets",
    "issues at work",
    "work issues",
)

_STUDY_HINTS = (
    "study",
    "exam",
    "notes",
    "assignment",
    "homework",
    "lecture",
    "course",
    "module",
    "semester",
    "textbook",
)

_CATALOG_CAP = 100


def build_catalog_text(documents: list[dict[str, Any]] | None) -> str:
    """Compact catalog lines: folder | source | document_id."""
    if not documents:
        return "(no documents in knowledge base)"

    lines = []
    for doc in documents[:_CATALOG_CAP]:
        folder = normalize_folder(doc.get("folder"))
        source = (doc.get("source") or "Untitled").replace("|", "/")
        doc_id = doc.get("document_id") or ""
        lines.append(f"{folder} | {source} | {doc_id}")

    if len(documents) > _CATALOG_CAP:
        lines.append(f"... and {len(documents) - _CATALOG_CAP} more")

    return "\n".join(lines)


def _heuristic_folder(message: str) -> str | None:
    lower = message.lower()
    if any(h in lower for h in _WORK_HINTS):
        return "work"
    if any(h in lower for h in _STUDY_HINTS):
        return "study"
    if any(h in lower for h in _PERSONAL_HINTS):
        return "personal"
    return None


def _match_document_ids(
    message: str,
    documents: list[dict[str, Any]] | None,
) -> list[str]:
    """Match query tokens against document titles (source)."""
    if not documents:
        return []

    lower = message.lower()
    tokens = [
        t.strip(".,!?;:\"'()[]{}").lower()
        for t in lower.split()
        if len(t.strip(".,!?;:\"'()[]{}")) >= 3
    ]
    if not tokens:
        return []

    scored: list[tuple[int, str]] = []
    for doc in documents:
        source = (doc.get("source") or "").lower()
        doc_id = doc.get("document_id")
        if not source or not doc_id:
            continue
        hits = sum(1 for t in tokens if t in source)
        if hits:
            scored.append((hits, str(doc_id)))

    scored.sort(key=lambda item: item[0], reverse=True)
    # Keep strong title matches only
    if not scored:
        return []
    best = scored[0][0]
    return [doc_id for hits, doc_id in scored if hits == best and hits >= 1]


def _heuristic_route(message: str) -> Route | None:
    """
    Deterministic routing for obvious web/ingestion requests.

    Important:
    Normal knowledge questions intentionally return None so that
    they can be routed to RAG by default rather than accidentally
    being sent to the web.
    """

    lower = message.lower().strip()

    # Explicit ingestion always wins.
    if any(h in lower for h in _INGEST_HINTS):
        return "ingest_web"

    # Explicit hybrid request.
    if any(h in lower for h in _HYBRID_HINTS):
        return "hybrid"

    # Explicit URL + normal web request.
    if _URL_RE.search(message):
        return "web"

    # Explicit web request.
    if any(h in lower for h in _WEB_HINTS):
        return "web"

    # Everything else is left for the planner.
    return None


def _normalize_scope(
    data: dict[str, Any],
    known_ids: set[str],
) -> tuple[str | None, list[str]]:
    folder = data.get("folder")
    if isinstance(folder, str) and folder.strip():
        folder_norm = folder.strip().lower()
        if folder_norm in {"null", "none", ""}:
            folder = None
        elif folder_norm in ALLOWED_FOLDERS:
            folder = folder_norm
        else:
            folder = None
    else:
        folder = None

    raw_ids = data.get("document_ids") or []
    if isinstance(raw_ids, str):
        raw_ids = [raw_ids]
    document_ids: list[str] = []
    if isinstance(raw_ids, list):
        for item in raw_ids:
            if not item:
                continue
            doc_id = str(item).strip()
            if doc_id in known_ids:
                document_ids.append(doc_id)

    return folder, document_ids


def _normalize_route(
    data: dict[str, Any],
    known_ids: set[str],
) -> dict[str, Any] | None:
    """
    Validate and normalize the LLM planner response.
    """

    route = data.get("route")

    if route not in {"rag", "web", "hybrid", "ingest_web"}:
        return None

    reason = data.get("reason")

    if not isinstance(reason, str) or not reason.strip():
        reason = "LLM routing decision"

    folder, document_ids = _normalize_scope(data, known_ids)

    return {
        "route": route,
        "reason": reason.strip(),
        "folder": folder,
        "document_ids": document_ids,
    }


def _empty_scope() -> dict[str, Any]:
    return {"folder": None, "document_ids": []}


def plan_route(
    message: str,
    *,
    document_id: str | None = None,
    force_web: bool = False,
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Decide how Nerva should handle a user request.

    Returns:
        {
            "route": "rag" | "web" | "hybrid" | "ingest_web",
            "reason": str,
            "folder": str | None,
            "document_ids": list[str],
        }
    """

    message = message.strip()
    documents = documents or []
    known_ids = {
        str(d["document_id"])
        for d in documents
        if d.get("document_id")
    }
    catalog = build_catalog_text(documents)

    if not message:
        return {
            "route": "rag",
            "reason": "Empty query; defaulting to RAG",
            **_empty_scope(),
        }

    # ---------------------------------------------------------
    # 1. Explicit client request for web mode
    # ---------------------------------------------------------

    if force_web:
        logger.info("Planner route=web reason=force_web")
        return {
            "route": "web",
            "reason": "Client requested agent/web mode",
            **_empty_scope(),
        }

    # ---------------------------------------------------------
    # 2. Deterministic routing
    # ---------------------------------------------------------

    heuristic = _heuristic_route(message)

    if heuristic:
        logger.info(
            "Planner heuristic route=%s message=%r",
            heuristic,
            message,
        )

        scope = _empty_scope()
        if heuristic in {"rag", "hybrid"}:
            matched = _match_document_ids(message, documents)
            folder_hint = _heuristic_folder(message)
            scope = {
                "folder": folder_hint if not matched else None,
                "document_ids": matched,
            }

        return {
            "route": heuristic,
            "reason": "Matched explicit web/ingestion intent",
            **scope,
        }

    # ---------------------------------------------------------
    # 3. Document-scoped chat
    # ---------------------------------------------------------

    if document_id:
        logger.info(
            "Planner route=rag reason=document_scoped document_id=%s",
            document_id,
        )

        return {
            "route": "rag",
            "reason": "Document-scoped query without explicit web intent",
            "folder": None,
            "document_ids": [document_id],
        }

    # ---------------------------------------------------------
    # 4. LLM routing (with catalog)
    # ---------------------------------------------------------

    user_content = (
        f"Knowledge catalog (folder | title | document_id):\n"
        f"{catalog}\n\n"
        f"User message:\n{message}"
    )

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": PLANNER_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            temperature=0,
            max_tokens=220,
        )

        content = (
            response.choices[0].message.content or ""
        ).strip()

        logger.info(
            "Planner raw LLM response=%r",
            content,
        )

        match = re.search(
            r"\{.*\}",
            content,
            re.DOTALL,
        )

        if match:
            data = json.loads(match.group(0))

            normalized = _normalize_route(data, known_ids)

            if normalized:
                # Fill gaps with heuristics when LLM omits scope.
                if (
                    normalized["route"] in {"rag", "hybrid"}
                    and not normalized["document_ids"]
                    and not normalized["folder"]
                ):
                    matched = _match_document_ids(message, documents)
                    folder_hint = _heuristic_folder(message)
                    if matched:
                        normalized["document_ids"] = matched
                    elif folder_hint:
                        normalized["folder"] = folder_hint

                logger.info(
                    "Planner LLM route=%s folder=%s ids=%s reason=%s",
                    normalized["route"],
                    normalized.get("folder"),
                    normalized.get("document_ids"),
                    normalized["reason"],
                )

                return normalized

    except Exception:
        logger.exception(
            "Planner LLM failed; defaulting to RAG"
        )

    # ---------------------------------------------------------
    # 5. SAFE DEFAULT
    # ---------------------------------------------------------

    matched = _match_document_ids(message, documents)
    folder_hint = _heuristic_folder(message)

    logger.info(
        "Planner fallback route=rag folder=%s ids=%s message=%r",
        folder_hint if not matched else None,
        matched,
        message,
    )

    return {
        "route": "rag",
        "reason": "Knowledge-base first fallback",
        "folder": folder_hint if not matched else None,
        "document_ids": matched,
    }
