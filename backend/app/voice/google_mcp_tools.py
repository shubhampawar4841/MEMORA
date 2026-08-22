"""Build LiveKit MCPToolsets for Google Workspace MCP (Gmail + Calendar)."""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import mcp

from app.auth.google_mcp import CALENDAR_MCP_URL, GMAIL_MCP_URL
from app.auth.google_mcp_bridge import fetch_google_mcp_auth_headers

logger = logging.getLogger("nerva.voice.google_mcp")

# Read-only tool subsets exposed to the voice agent.
GMAIL_MCP_READONLY_TOOLS = [
    "search_threads",
    "get_thread",
    "get_message",
    "list_labels",
    "list_drafts",
]

CALENDAR_MCP_READONLY_TOOLS = [
    "list_events",
    "get_event",
    "list_calendars",
    "search_events",
    "suggest_time",
]

# Google MCP can be slow on first connect; LiveKit defaults are 5s.
_GOOGLE_MCP_HTTP_TIMEOUT = 30.0
_GOOGLE_MCP_SESSION_TIMEOUT = 120.0

LAST_GOOGLE_MCP_BUILD: dict[str, bool] = {"gmail": False, "calendar": False}


def build_google_mcp_toolsets(
    *,
    runtime_status: dict[str, Any] | None = None,
) -> list[mcp.MCPToolset]:
    """
    Create Gmail/Calendar MCPToolsets when OAuth credentials and MCP discovery succeed.

    Uses the backend credential bridge so the LiveKit worker never needs Google's
    client secret or refresh token — only a short-lived access token in headers.
    """
    headers, _refresh, source = fetch_google_mcp_auth_headers()
    if not headers:
        LAST_GOOGLE_MCP_BUILD["gmail"] = False
        LAST_GOOGLE_MCP_BUILD["calendar"] = False
        return []

    gmail_ok = bool((runtime_status or {}).get("gmail_mcp_enabled"))
    calendar_ok = bool((runtime_status or {}).get("calendar_mcp_enabled"))

    toolsets: list[mcp.MCPToolset] = []

    if gmail_ok:
        toolsets.append(
            mcp.MCPToolset(
                id="Gmail",
                mcp_server=mcp.MCPServerHTTP(
                    url=GMAIL_MCP_URL,
                    headers=headers,
                    transport_type="streamable_http",
                    allowed_tools=GMAIL_MCP_READONLY_TOOLS,
                    timeout=_GOOGLE_MCP_HTTP_TIMEOUT,
                    client_session_timeout_seconds=_GOOGLE_MCP_SESSION_TIMEOUT,
                ),
            ),
        )
        LAST_GOOGLE_MCP_BUILD["gmail"] = True
    else:
        LAST_GOOGLE_MCP_BUILD["gmail"] = False

    if calendar_ok:
        toolsets.append(
            mcp.MCPToolset(
                id="Calendar",
                mcp_server=mcp.MCPServerHTTP(
                    url=CALENDAR_MCP_URL,
                    headers=headers,
                    transport_type="streamable_http",
                    allowed_tools=CALENDAR_MCP_READONLY_TOOLS,
                    timeout=_GOOGLE_MCP_HTTP_TIMEOUT,
                    client_session_timeout_seconds=_GOOGLE_MCP_SESSION_TIMEOUT,
                ),
            ),
        )
        LAST_GOOGLE_MCP_BUILD["calendar"] = True
    else:
        LAST_GOOGLE_MCP_BUILD["calendar"] = False

    if headers and not toolsets:
        logger.warning(
            "Google OAuth token resolved via %s but MCP discovery failed — "
            "enable gmailmcp.googleapis.com and calendarmcp.googleapis.com in GCP",
            source,
        )

    return toolsets
