from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str
    conversation_id: str | None = Field(
        default=None,
        alias="conversationId",
    )
    document_id: str | None = Field(default=None, alias="documentId")
    force_web: bool = Field(default=False, alias="forceWeb")
    history: list[dict[str, str]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class AgentStep(BaseModel):
    tool: str
    status: str


class AgentChatResponse(BaseModel):
    success: bool = True
    message: str
    route: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    requires_confirmation: bool = False
    pending_tool: str | None = None
    pending_arguments: dict[str, Any] | None = None
    conversation_id: str | None = None
    document_id: str | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)


class WebIngestRequest(BaseModel):
    url: str
    mode: str = "scrape"
    limit: int | None = None
    search: str | None = None
    document_id: str | None = Field(default=None, alias="documentId")

    model_config = {"populate_by_name": True}


class WebIngestResponse(BaseModel):
    document_id: str | None = None
    source: str | None = None
    url: str | None = None
    mode: str | None = None
    pages: int = 0
    chunks: int = 0
    embedding_dimension: int = 0
    error: str | None = None
