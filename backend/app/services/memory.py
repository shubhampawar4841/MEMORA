"""Normalize Supermemory profile / search / graph payloads for the UI."""

from __future__ import annotations

from typing import Any

from app.config import NERVA_USER_ID
from app.supermemory import client as sm
from app.supermemory.containers import (
    container_tag_for_user,
    resolve_container_tag,
)


def _tag_for(user_id: str | None) -> str:
    if user_id and str(user_id).strip():
        return container_tag_for_user(user_id)
    return resolve_container_tag(None)


def _as_str_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                text = (
                    item.get("memory")
                    or item.get("content")
                    or item.get("text")
                    or item.get("fact")
                )
                if isinstance(text, str) and text.strip():
                    out.append(text.strip())
        return out
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def get_profile(user_id: str | None = None) -> dict[str, Any]:
    if not sm.is_configured():
        return {
            "ok": False,
            "error": "SUPERMEMORY_API_KEY is not configured.",
            "user_id": user_id or NERVA_USER_ID,
            "container_tag": _tag_for(user_id),
            "static": [],
            "dynamic": [],
        }

    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    tag = container_tag_for_user(uid)
    try:
        raw = sm.get_profile(container_tag=tag)
    except sm.SupermemoryError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "user_id": uid,
            "container_tag": tag,
            "static": [],
            "dynamic": [],
        }

    profile = raw.get("profile") if isinstance(raw.get("profile"), dict) else raw
    if not isinstance(profile, dict):
        profile = {}

    static = _as_str_list(profile.get("static"))
    dynamic = _as_str_list(profile.get("dynamic"))

    return {
        "ok": True,
        "user_id": uid,
        "container_tag": tag,
        "static": static,
        "dynamic": dynamic,
        "static_count": len(static),
        "dynamic_count": len(dynamic),
        "raw": raw,
    }


def _result_kind(item: dict[str, Any]) -> str:
    if item.get("memory") or item.get("type") == "memory":
        return "memory"
    if item.get("chunk") or item.get("document") or item.get("documentId"):
        return "document"
    # hybrid payloads sometimes only have similarity + text fields
    if "similarity" in item and "chunk" not in item and item.get("memory"):
        return "memory"
    return "memory" if item.get("memory") else "document"


def _result_text(item: dict[str, Any]) -> str:
    for key in ("memory", "chunk", "content", "text", "summary"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    doc = item.get("document")
    if isinstance(doc, dict):
        for key in ("content", "summary", "title"):
            val = doc.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def _result_id(item: dict[str, Any], index: int) -> str:
    for key in ("id", "memoryId", "documentId", "customId"):
        val = item.get(key)
        if val:
            return str(val)
    doc = item.get("document")
    if isinstance(doc, dict):
        for key in ("id", "customId"):
            if doc.get(key):
                return str(doc[key])
    return f"hit_{index}"


def normalize_search_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
    results = raw.get("results") or raw.get("memories") or []
    out: list[dict[str, Any]] = []
    for i, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        text = _result_text(item)
        if not text:
            continue
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        score = float(item.get("similarity") or item.get("score") or 0.0)
        kind = _result_kind(item)
        out.append({
            "id": _result_id(item, i),
            "text": text,
            "score": score,
            "kind": kind,
            "source": meta.get("title") or meta.get("source") or item.get("title"),
            "metadata": meta,
            "related": item.get("relatedMemories") or item.get("relations") or [],
            "raw": item,
        })
    return out


def search_memory(
    *,
    query: str,
    mode: str = "hybrid",
    limit: int = 10,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not sm.is_configured():
        return {
            "ok": False,
            "error": "SUPERMEMORY_API_KEY is not configured.",
            "query": query,
            "mode": mode,
            "results": [],
            "container_tag": _tag_for(user_id),
        }

    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    tag = container_tag_for_user(uid)
    mode_clean = (mode or "hybrid").strip().lower()
    if mode_clean not in {"hybrid", "memories", "documents"}:
        mode_clean = "hybrid"

    try:
        raw = sm.search(
            query=query,
            limit=limit,
            container_tag=tag,
            search_mode=mode_clean,
            rerank=True,
            include={
                "documents": True,
                "summaries": False,
                "relatedMemories": False,
                "forgottenMemories": False,
            },
        )
    except sm.SupermemoryError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "query": query,
            "mode": mode_clean,
            "results": [],
            "user_id": uid,
            "container_tag": tag,
        }

    results = normalize_search_results(raw)
    return {
        "ok": True,
        "query": query,
        "mode": mode_clean,
        "user_id": uid,
        "container_tag": tag,
        "results": results,
        "count": len(results),
    }


def _related_list(item: dict[str, Any]) -> list[dict[str, Any]]:
    related = item.get("related") or []
    if isinstance(related, dict):
        # sometimes nested under updates/extends/derives
        bundled: list[dict[str, Any]] = []
        for rel_type, entries in related.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    bundled.append({**entry, "relation": rel_type})
                elif isinstance(entry, str):
                    bundled.append({"memory": entry, "relation": rel_type})
        return bundled
    if isinstance(related, list):
        return [r for r in related if isinstance(r, (dict, str))]
    return []


def build_graph(
    *,
    query: str,
    limit: int = 12,
    user_id: str | None = None,
) -> dict[str, Any]:
    if not sm.is_configured():
        return {
            "ok": False,
            "error": "SUPERMEMORY_API_KEY is not configured.",
            "query": query,
            "nodes": [],
            "edges": [],
            "results": [],
            "container_tag": _tag_for(user_id),
        }

    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    tag = container_tag_for_user(uid)

    try:
        raw = sm.search(
            query=query,
            limit=limit,
            container_tag=tag,
            search_mode="hybrid",
            rerank=True,
            include={
                "documents": True,
                "summaries": False,
                "relatedMemories": True,
                "forgottenMemories": False,
            },
        )
    except sm.SupermemoryError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "query": query,
            "nodes": [],
            "edges": [],
            "results": [],
            "user_id": uid,
            "container_tag": tag,
        }

    results = normalize_search_results(raw)
    # re-attach related from raw items (normalize may have nested)
    for i, item in enumerate(raw.get("results") or []):
        if i < len(results) and isinstance(item, dict):
            results[i]["related"] = (
                item.get("relatedMemories")
                or item.get("relations")
                or results[i].get("related")
                or []
            )

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def upsert_node(
        node_id: str,
        *,
        label: str,
        kind: str,
        score: float | None = None,
    ) -> None:
        if node_id in nodes:
            if score is not None and (nodes[node_id].get("score") or 0) < score:
                nodes[node_id]["score"] = score
            return
        nodes[node_id] = {
            "id": node_id,
            "label": (label or node_id)[:160],
            "kind": kind,
            "score": score or 0.0,
        }

    for hit in results:
        hid = hit["id"]
        upsert_node(
            hid,
            label=hit["text"],
            kind=hit["kind"],
            score=hit["score"],
        )
        for related in _related_list(hit):
            if isinstance(related, str):
                rid = f"rel_{hash(related) & 0xFFFFFFF:x}"
                rtext = related
                rel = "related"
            else:
                rtext = (
                    related.get("memory")
                    or related.get("content")
                    or related.get("text")
                    or ""
                )
                rid = str(
                    related.get("id")
                    or related.get("memoryId")
                    or f"rel_{hash(rtext) & 0xFFFFFFF:x}"
                )
                rel = str(
                    related.get("relation")
                    or related.get("type")
                    or related.get("relationship")
                    or "related"
                )
            if not rtext:
                continue
            upsert_node(rid, label=rtext, kind="memory", score=None)
            edges.append({
                "id": f"{hid}->{rid}:{rel}",
                "source": hid,
                "target": rid,
                "relation": rel.lower(),
            })

    return {
        "ok": True,
        "query": query,
        "user_id": uid,
        "container_tag": tag,
        "nodes": list(nodes.values()),
        "edges": edges,
        "results": results,
        "count": len(results),
    }


def get_activity(user_id: str | None = None, limit: int = 30) -> dict[str, Any]:
    uid = (user_id or NERVA_USER_ID).strip() or NERVA_USER_ID
    tag = container_tag_for_user(uid)
    items: list[dict[str, Any]] = []

    if not sm.is_configured():
        return {
            "ok": False,
            "error": "SUPERMEMORY_API_KEY is not configured.",
            "user_id": uid,
            "container_tag": tag,
            "items": [],
        }

    try:
        docs_raw = sm.list_documents(container_tag=tag, limit=min(limit, 50))
        batch = docs_raw.get("memories") or docs_raw.get("documents") or []
        for doc in batch:
            if not isinstance(doc, dict):
                continue
            meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            title = (
                meta.get("title")
                or meta.get("source")
                or doc.get("title")
                or doc.get("customId")
                or doc.get("id")
            )
            items.append({
                "id": str(doc.get("id") or doc.get("customId") or title),
                "type": "document",
                "title": str(title),
                "status": doc.get("status") or "unknown",
                "at": doc.get("updatedAt") or doc.get("createdAt") or doc.get("updated_at"),
                "provider": meta.get("source_type") or meta.get("source"),
            })
    except sm.SupermemoryError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "user_id": uid,
            "container_tag": tag,
            "items": [],
        }

    try:
        connections = sm.list_connections(container_tag=tag)
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            items.append({
                "id": str(conn.get("id") or conn.get("provider")),
                "type": "connection",
                "title": f"{conn.get('provider', 'connector')} connected",
                "status": "connected",
                "at": conn.get("createdAt") or conn.get("created_at"),
                "provider": conn.get("provider"),
                "email": conn.get("email"),
            })
    except sm.SupermemoryError:
        pass

    # Newest-ish first when timestamps exist
    items.sort(key=lambda x: str(x.get("at") or ""), reverse=True)
    return {
        "ok": True,
        "user_id": uid,
        "container_tag": tag,
        "items": items[:limit],
    }
