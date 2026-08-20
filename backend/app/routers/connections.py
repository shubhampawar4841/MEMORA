"""Connect Gmail / GitHub via Supermemory OAuth connectors."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import NERVA_USER_ID
from app.services import connections as connection_service

router = APIRouter(tags=["connections"])


class ConnectRequest(BaseModel):
    user_id: str | None = Field(
        default=None,
        description="End-user id; memory is stored under user_<user_id>.",
    )
    redirect_url: str | None = Field(
        default=None,
        description="Where Supermemory sends the browser after OAuth.",
    )
    document_limit: int = Field(default=5000, ge=1, le=10000)


class DisconnectRequest(BaseModel):
    delete_documents: bool = False


@router.post("/connect/gmail")
def connect_gmail(body: ConnectRequest | None = None):
    """
    Start Gmail OAuth via Supermemory (Scale / Enterprise).

    Returns auth_link — open it in the browser. After approval,
    Supermemory syncs mail into container tag user_<user_id>.
    """
    body = body or ConnectRequest()
    result = connection_service.start_connection(
        "gmail",
        user_id=body.user_id,
        redirect_url=body.redirect_url,
        document_limit=body.document_limit,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/connect/github")
def connect_github(body: ConnectRequest | None = None):
    """
    Start GitHub OAuth via Supermemory (Scale / Enterprise).

    Returns auth_link — open it in the browser. After approval,
    select repos to sync; content lands in container tag user_<user_id>.
    """
    body = body or ConnectRequest()
    result = connection_service.start_connection(
        "github",
        user_id=body.user_id,
        redirect_url=body.redirect_url,
        document_limit=body.document_limit,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/connections")
def list_connections(
    user_id: str | None = Query(default=None),
):
    result = connection_service.list_user_connections(user_id)
    if not result.get("ok") and result.get("error"):
        # Still return empty list shape for UI; surface error.
        return result
    return result


@router.delete("/connections/{connection_id}")
def delete_connection(
    connection_id: str,
    delete_documents: bool = Query(default=False),
):
    result = connection_service.disconnect(
        connection_id,
        delete_documents=delete_documents,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/connect/me")
def connect_defaults():
    """Helpers for the UI: default user id + container tag."""
    from app.supermemory.containers import container_tag_for_user

    return {
        "user_id": NERVA_USER_ID,
        "container_tag": container_tag_for_user(NERVA_USER_ID),
        "plan_notes": connection_service.PROVIDER_NOTES,
    }
