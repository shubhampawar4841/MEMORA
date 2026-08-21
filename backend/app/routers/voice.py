"""LiveKit room token for the Call UI (standard TokenSource endpoint)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import (
    LIVEKIT_AGENT_NAME,
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_URL,
)

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceTokenRequest(BaseModel):
    """Matches LiveKit TokenSource.endpoint request fields (snake_case)."""

    room_name: str | None = None
    participant_identity: str | None = None
    participant_name: str | None = None
    participant_metadata: str | None = None
    participant_attributes: dict[str, str] | None = None
    room_config: dict[str, Any] | None = None
    # Legacy fields used by older Call UI
    identity: str | None = Field(
        default=None, description="Alias for participant_identity"
    )


def _room_configuration(api: Any, room_config: dict[str, Any] | None):
    """Build a protobuf RoomConfiguration (dicts break AccessToken.to_jwt)."""
    from google.protobuf import json_format

    config = api.RoomConfiguration()
    if room_config:
        json_format.ParseDict(room_config, config, ignore_unknown_fields=True)

    # Ensure named agent is always dispatched for the Call UI.
    if not list(config.agents):
        config.agents.append(
            api.RoomAgentDispatch(agent_name=LIVEKIT_AGENT_NAME)
        )
    return config


@router.post("/token")
def create_voice_token(body: VoiceTokenRequest):
    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail=(
                "LiveKit is not configured. Set LIVEKIT_URL, "
                "LIVEKIT_API_KEY, and LIVEKIT_API_SECRET."
            ),
        )

    try:
        from livekit import api
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="livekit-api is not installed on the backend.",
        ) from exc

    room_name = (body.room_name or "").strip() or f"nerva-{uuid.uuid4().hex[:10]}"
    identity = (
        (body.participant_identity or body.identity or "").strip()
        or f"caller-{uuid.uuid4().hex[:8]}"
    )
    name = (body.participant_name or "").strip() or identity

    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(name)
        .with_ttl(timedelta(hours=2))
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .with_room_config(_room_configuration(api, body.room_config))
    )

    if body.participant_metadata:
        token = token.with_metadata(body.participant_metadata)
    if body.participant_attributes:
        token = token.with_attributes(body.participant_attributes)

    return JSONResponse(
        status_code=201,
        content={
            "server_url": LIVEKIT_URL,
            "participant_token": token.to_jwt(),
        },
    )


@router.get("/status")
def voice_status():
    return {
        "configured": bool(
            LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET
        ),
        "url_set": bool(LIVEKIT_URL),
        "agent_name": LIVEKIT_AGENT_NAME,
    }
