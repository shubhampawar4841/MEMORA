"""FastAPI routers — lazy-loaded so Vercel can import telegram/health only."""

from __future__ import annotations

import importlib

__all__ = [
    "agent",
    "auth",
    "chat",
    "connections",
    "documents",
    "health",
    "memory",
    "search",
    "telegram",
    "voice",
]


def __getattr__(name: str):
    if name in __all__:
        return importlib.import_module(f"app.routers.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
