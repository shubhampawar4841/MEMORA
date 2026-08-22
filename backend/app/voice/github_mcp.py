"""GitHub remote MCP helpers for the Nerva LiveKit voice agent."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("nerva.voice.github_mcp")

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"
GITHUB_OWNER = "shubhampawar4841"
GITHUB_AUTHORIZED_REPOS: tuple[str, ...] = (
    "shubhampawar4841/cognito-crawl",
    "shubhampawar4841/Reeler",
    "shubhampawar4841/MEMORA",
)

# Read-only toolsets per GitHub remote MCP docs.
GITHUB_MCP_TOOLSETS = "repos,git,issues,pull_requests,actions,notifications"

_MCP_ACCEPT = "application/json, text/event-stream"
_MCP_PROTOCOL_VERSION = "2024-11-05"
_GITHUB_MCP_HTTP_TIMEOUT = 30.0
_GITHUB_MCP_SESSION_TIMEOUT = 120.0


def get_github_token() -> str | None:
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    return token or None


def build_github_mcp_headers(token: str) -> dict[str, str]:
    """
    Headers for GitHub's official remote MCP server.

    See: https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md
    """
    return {
        "Authorization": f"Bearer {token.strip()}",
        "X-MCP-Toolsets": GITHUB_MCP_TOOLSETS,
        "X-MCP-Readonly": "true",
    }


def probe_github_mcp_server(
    auth_headers: dict[str, str],
    *,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Run MCP initialize + tools/list. Never logs credentials."""
    result: dict[str, Any] = {
        "url": GITHUB_MCP_URL,
        "connected": False,
        "initialize_ok": False,
        "tools_discovered": 0,
        "tool_names_sample": [],
        "error": None,
    }

    headers = {
        **auth_headers,
        "Content-Type": "application/json",
        "Accept": _MCP_ACCEPT,
    }
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": _MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "nerva", "version": "0.1.0"},
        },
    }
    tools_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            init_response = client.post(
                GITHUB_MCP_URL,
                headers=headers,
                json=init_payload,
            )
            init_body = init_response.json()
            if init_response.status_code >= 400 or "error" in init_body:
                result["error"] = (
                    f"initialize failed (HTTP {init_response.status_code})"
                )
                return result

            result["initialize_ok"] = bool(init_body.get("result"))

            tools_response = client.post(
                GITHUB_MCP_URL,
                headers=headers,
                json=tools_payload,
            )
            tools_body = tools_response.json()
            if "error" in tools_body:
                result["error"] = "tools/list returned MCP error"
                return result

            tools = tools_body.get("result", {}).get("tools", [])
            if not isinstance(tools, list):
                result["error"] = "tools/list returned unexpected payload"
                return result

            tool_names = [
                str(tool.get("name"))
                for tool in tools
                if isinstance(tool, dict) and tool.get("name")
            ]
            result["tools_discovered"] = len(tool_names)
            result["tool_names_sample"] = tool_names[:10]
            result["connected"] = result["initialize_ok"] and len(tool_names) > 0
    except httpx.HTTPError as exc:
        result["error"] = f"HTTP error: {exc.__class__.__name__}"
        logger.warning("GitHub MCP probe failed: %s", result["error"])

    return result


def log_github_mcp_status(probe: dict[str, Any], *, token_configured: bool) -> None:
    logger.info("GitHub token configured: %s", "yes" if token_configured else "no")
    logger.info(
        "GitHub MCP enabled: %s",
        "yes" if probe.get("connected") else "no",
    )
    logger.info(
        "GitHub MCP discovery: connected=%s tools=%s sample=%s error=%s",
        probe.get("connected"),
        probe.get("tools_discovered"),
        probe.get("tool_names_sample"),
        probe.get("error"),
    )
