"""Firecrawl hosted MCP client (streamable HTTP)."""

from __future__ import annotations

import asyncio
import atexit
import logging
import threading
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import ImageContent, TextContent

from app.config import (
    FIRECRAWL_API_KEY,
    FIRECRAWL_MCP_SSE_READ_TIMEOUT,
    FIRECRAWL_MCP_TIMEOUT,
    FIRECRAWL_MCP_URL,
)

logger = logging.getLogger("nerva.mcp.firecrawl")

# Agent-facing name -> MCP tool name
FIRECRAWL_TOOL_ALIASES: dict[str, str] = {
    "search": "firecrawl_search",
    "scrape": "firecrawl_scrape",
    "crawl": "firecrawl_crawl",
    "map": "firecrawl_map",
    "interact": "firecrawl_interact",
}

# Primary tools from the Nerva architecture diagram (+ map/interact for parity)
EXPOSED_FIRECRAWL_TOOLS: tuple[str, ...] = (
    "search",
    "scrape",
    "crawl",
    "map",
    "interact",
)


class FirecrawlMcpError(RuntimeError):
    """Raised when the Firecrawl MCP client cannot complete a call."""


def _content_to_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, TextContent) or getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
        elif isinstance(block, ImageContent) or getattr(block, "type", None) == "image":
            parts.append("[image omitted]")
        else:
            parts.append(str(block))
    return "\n".join(p for p in parts if p).strip()


class FirecrawlMcpClient:
    """
    Long-lived MCP session on a dedicated event-loop thread.

    Sync callers (agent orchestrator) use call_tool() safely from any thread.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="firecrawl-mcp",
            daemon=True,
        )
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._cm = None
        self._session: ClientSession | None = None
        self._tool_schemas: dict[str, dict[str, Any]] = {}
        self._closed = False
        self._thread.start()
        atexit.register(self.close)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.call_soon(self._ready.set)
        self._loop.run_forever()

    def _submit(self, coro, timeout: float | None = None):
        self._ready.wait(timeout=10)
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    async def _ensure_session(self) -> ClientSession:
        if self._session is not None:
            return self._session
        if not FIRECRAWL_API_KEY:
            raise FirecrawlMcpError(
                "FIRECRAWL_API_KEY is missing. Add it to the backend .env file."
            )

        headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}"}
        self._cm = streamablehttp_client(
            FIRECRAWL_MCP_URL,
            headers=headers,
            timeout=FIRECRAWL_MCP_TIMEOUT,
            sse_read_timeout=FIRECRAWL_MCP_SSE_READ_TIMEOUT,
        )
        read, write, _get_session_id = await self._cm.__aenter__()
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        self._session = session
        await self._refresh_tools()
        logger.info(
            "Firecrawl MCP connected (%s tools)",
            len(self._tool_schemas),
        )
        return session

    async def _refresh_tools(self) -> None:
        assert self._session is not None
        listed = await self._session.list_tools()
        schemas: dict[str, dict[str, Any]] = {}
        by_mcp_name = {t.name: t for t in listed.tools}
        for alias, mcp_name in FIRECRAWL_TOOL_ALIASES.items():
            tool = by_mcp_name.get(mcp_name)
            if tool is None:
                continue
            schemas[alias] = {
                "name": alias,
                "mcp_name": mcp_name,
                "description": tool.description or f"Firecrawl {alias}",
                "parameters": tool.inputSchema
                or {"type": "object", "properties": {}},
            }
        self._tool_schemas = schemas

    async def _reset(self) -> None:
        session = self._session
        cm = self._cm
        self._session = None
        self._cm = None
        self._tool_schemas = {}
        if session is not None:
            try:
                await session.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                logger.debug("MCP session close failed", exc_info=True)
        if cm is not None:
            try:
                await cm.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001
                logger.debug("MCP transport close failed", exc_info=True)

    async def _call_tool_async(
        self,
        alias: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        mcp_name = FIRECRAWL_TOOL_ALIASES.get(alias, alias)
        try:
            session = await self._ensure_session()
            result = await session.call_tool(mcp_name, arguments or {})
        except Exception as first:  # noqa: BLE001
            logger.warning("MCP call failed; reconnecting: %s", first)
            await self._reset()
            session = await self._ensure_session()
            result = await session.call_tool(mcp_name, arguments or {})

        text = _content_to_text(list(result.content or []))
        is_error = bool(getattr(result, "isError", False))
        structured = getattr(result, "structuredContent", None)
        data: Any
        if structured is not None:
            data = structured
        elif text:
            data = {"text": text}
        else:
            data = {}

        if is_error:
            return {
                "success": False,
                "tool": alias,
                "error": text or f"MCP tool {mcp_name} failed",
                "data": data,
            }
        return {
            "success": True,
            "tool": alias,
            "data": data,
            "source": "firecrawl_mcp",
        }

    def list_tool_schemas(self) -> list[dict[str, Any]]:
        with self._lock:
            if not self._tool_schemas:
                self._submit(self._ensure_session(), timeout=FIRECRAWL_MCP_TIMEOUT)
            return [
                self._tool_schemas[name]
                for name in EXPOSED_FIRECRAWL_TOOLS
                if name in self._tool_schemas
            ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        alias = name
        if alias not in FIRECRAWL_TOOL_ALIASES and alias.startswith("firecrawl_"):
            for a, mcp_name in FIRECRAWL_TOOL_ALIASES.items():
                if mcp_name == alias:
                    alias = a
                    break
        if alias not in FIRECRAWL_TOOL_ALIASES:
            return {
                "success": False,
                "tool": name,
                "error": f"Unknown Firecrawl MCP tool: {name}",
            }
        with self._lock:
            try:
                return self._submit(
                    self._call_tool_async(alias, arguments or {}),
                    timeout=FIRECRAWL_MCP_SSE_READ_TIMEOUT + 30,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Firecrawl MCP call_tool failed")
                return {
                    "success": False,
                    "tool": alias,
                    "error": str(exc),
                }

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._ready.is_set():
                self._submit(self._reset(), timeout=10)
        except Exception:  # noqa: BLE001
            pass
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


_client: FirecrawlMcpClient | None = None
_client_lock = threading.Lock()


def get_firecrawl_mcp() -> FirecrawlMcpClient:
    global _client
    with _client_lock:
        if _client is None or _client._closed:
            _client = FirecrawlMcpClient()
        return _client
