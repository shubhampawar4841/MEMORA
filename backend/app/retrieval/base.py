"""Retriever protocol — planner-agnostic retrieval backend."""

from __future__ import annotations

from typing import Protocol

from app.retrieval.types import RetrievalHit


class Retriever(Protocol):
    name: str

    def search(
        self,
        query: str,
        *,
        folder: str | None = None,
        document_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievalHit]:
        ...
