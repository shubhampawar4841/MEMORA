"""Shared tool primitives for the Firecrawl agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def ok(tool: str, data: Any, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": True,
        "tool": tool,
        "data": data,
    }
    payload.update(extra)
    return payload


def fail(tool: str, error: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "tool": tool,
        "error": error,
    }
    payload.update(extra)
    return payload


@dataclass
class AgentTool:
    name: str
    description: str
    parameters: dict[str, Any]
    execute: Callable[[dict[str, Any]], dict[str, Any]]
    status_message: str = "Working…"
    read_only: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
