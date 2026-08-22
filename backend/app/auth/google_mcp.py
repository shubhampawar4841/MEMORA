"""Probe Google Workspace MCP servers (Gmail, Calendar) for diagnostics."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("nerva.auth.google_mcp")

GMAIL_MCP_URL = "https://gmailmcp.googleapis.com/mcp/v1"
CALENDAR_MCP_URL = "https://calendarmcp.googleapis.com/mcp/v1"

_MCP_ACCEPT = "application/json, text/event-stream"
_MCP_PROTOCOL_VERSION = "2024-11-05"


def _mcp_headers(auth_headers: dict[str, str]) -> dict[str, str]:
    return {
        **auth_headers,
        "Content-Type": "application/json",
        "Accept": _MCP_ACCEPT,
    }


def probe_google_mcp_server(
    *,
    name: str,
    url: str,
    auth_headers: dict[str, str],
    timeout: float = 20.0,
) -> dict[str, Any]:
    """
    Run MCP initialize + tools/list against a Google Workspace MCP server.

    Never logs credentials. Returns a safe summary for logging/UI.
    """
    result: dict[str, Any] = {
        "name": name,
        "url": url,
        "connected": False,
        "initialize_ok": False,
        "tools_discovered": 0,
        "tool_names_sample": [],
        "error": None,
    }

    headers = _mcp_headers(auth_headers)
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
            init_response = client.post(url, headers=headers, json=init_payload)
            init_body = init_response.json()
            if init_response.status_code >= 400 or "error" in init_body:
                result["error"] = (
                    f"initialize failed (HTTP {init_response.status_code})"
                )
                return result

            result["initialize_ok"] = bool(init_body.get("result"))

            tools_response = client.post(url, headers=headers, json=tools_payload)
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
            result["tool_names_sample"] = tool_names[:8]
            result["connected"] = result["initialize_ok"] and len(tool_names) > 0
            if tools_response.status_code >= 400 and not result["connected"]:
                result["error"] = (
                    f"tools/list failed (HTTP {tools_response.status_code})"
                )
    except httpx.HTTPError as exc:
        result["error"] = f"HTTP error: {exc.__class__.__name__}"
        logger.warning("%s MCP probe failed: %s", name, result["error"])
    except Exception as exc:  # pragma: no cover - defensive
        result["error"] = f"{exc.__class__.__name__}"
        logger.warning("%s MCP probe failed: %s", name, result["error"])

    return result


def probe_google_workspace_mcp(
    auth_headers: dict[str, str],
) -> dict[str, Any]:
    """Probe Gmail and Calendar MCP servers."""
    gmail = probe_google_mcp_server(
        name="Gmail",
        url=GMAIL_MCP_URL,
        auth_headers=auth_headers,
    )
    calendar = probe_google_mcp_server(
        name="Calendar",
        url=CALENDAR_MCP_URL,
        auth_headers=auth_headers,
    )
    return {"gmail": gmail, "calendar": calendar}
