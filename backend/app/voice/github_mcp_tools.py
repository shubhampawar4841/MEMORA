"""Build LiveKit MCPToolset for GitHub remote MCP."""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import mcp

from app.voice.github_mcp import (
    GITHUB_MCP_URL,
    _GITHUB_MCP_HTTP_TIMEOUT,
    _GITHUB_MCP_SESSION_TIMEOUT,
    build_github_mcp_headers,
    get_github_token,
    log_github_mcp_status,
    probe_github_mcp_server,
)

logger = logging.getLogger("nerva.voice.github_mcp_tools")

LAST_GITHUB_MCP_BUILD: dict[str, bool] = {"github": False}


def build_github_mcp_toolset(
    *,
    runtime_probe: dict[str, Any] | None = None,
) -> mcp.MCPToolset | None:
    """Create the GitHub MCPToolset when token + MCP discovery succeed."""
    token = get_github_token()
    if not token:
        LAST_GITHUB_MCP_BUILD["github"] = False
        log_github_mcp_status({"connected": False, "error": "no_token"}, token_configured=False)
        return None

    headers = build_github_mcp_headers(token)
    probe = runtime_probe or probe_github_mcp_server(headers)
    log_github_mcp_status(probe, token_configured=True)

    if not probe.get("connected"):
        LAST_GITHUB_MCP_BUILD["github"] = False
        logger.warning(
            "GitHub MCP disabled — check GITHUB_TOKEN scopes and network access"
        )
        return None

    LAST_GITHUB_MCP_BUILD["github"] = True
    return mcp.MCPToolset(
        id="GitHub",
        mcp_server=mcp.MCPServerHTTP(
            url=GITHUB_MCP_URL,
            headers=headers,
            transport_type="streamable_http",
            timeout=_GITHUB_MCP_HTTP_TIMEOUT,
            client_session_timeout_seconds=_GITHUB_MCP_SESSION_TIMEOUT,
        ),
    )
