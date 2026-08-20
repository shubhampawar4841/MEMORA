"""Supermemory profile, hybrid search, and memory graph exploration."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import memory as memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class MemorySearchRequest(BaseModel):
    q: str = Field(..., min_length=1)
    mode: str = Field(default="hybrid")
    limit: int = Field(default=10, ge=1, le=50)
    user_id: str | None = None


class MemoryGraphRequest(BaseModel):
    q: str = Field(..., min_length=1)
    limit: int = Field(default=12, ge=1, le=40)
    user_id: str | None = None


@router.get("/profile")
def memory_profile(user_id: str | None = Query(default=None)):
    result = memory_service.get_profile(user_id)
    if not result.get("ok") and result.get("error"):
        # Return payload so UI can show empty state; 400 only if misconfigured key path wants it
        if "not configured" in str(result.get("error")):
            raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/search")
def memory_search(body: MemorySearchRequest):
    result = memory_service.search_memory(
        query=body.q.strip(),
        mode=body.mode,
        limit=body.limit,
        user_id=body.user_id,
    )
    if not result.get("ok") and "not configured" in str(result.get("error") or ""):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.post("/graph")
def memory_graph(body: MemoryGraphRequest):
    result = memory_service.build_graph(
        query=body.q.strip(),
        limit=body.limit,
        user_id=body.user_id,
    )
    if not result.get("ok") and "not configured" in str(result.get("error") or ""):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.get("/activity")
def memory_activity(
    user_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
):
    result = memory_service.get_activity(user_id, limit=limit)
    if not result.get("ok") and "not configured" in str(result.get("error") or ""):
        raise HTTPException(status_code=503, detail=result["error"])
    return result
