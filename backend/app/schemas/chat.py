from pydantic import BaseModel, Field


class AskSource(BaseModel):
    source: str | None = None
    page: int | None = None
    chunk_index: int | None = None
    distance: float
    rerank_score: float
    text: str | None = None


class AskResponse(BaseModel):
    query: str
    document_id: str | None = None
    answer: str
    sources: list[AskSource] = Field(default_factory=list)


class ConversationCreate(BaseModel):
    title: str | None = None
    document_id: str | None = None


class ConversationRename(BaseModel):
    title: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    document_id: str | None = None
    created_at: str
    updated_at: str
    message_count: int = 0


class ConversationMessage(BaseModel):
    id: str
    role: str
    content: str
    sources: list[AskSource] = Field(default_factory=list)
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    document_id: str | None = None
    created_at: str
    updated_at: str
    messages: list[ConversationMessage] = Field(default_factory=list)


class ConversationsResponse(BaseModel):
    conversations: list[ConversationSummary]


class ChatAskRequest(BaseModel):
    query: str
    document_id: str | None = None
    conversation_id: str | None = None


class AppendMessagesRequest(BaseModel):
    user_content: str
    assistant_content: str
    sources: list[AskSource] = Field(default_factory=list)
