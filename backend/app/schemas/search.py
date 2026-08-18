from pydantic import BaseModel, Field


class SearchResultMetadata(BaseModel):
    source: str | None = None
    page: int | None = None
    document_id: str | None = None
    chunk_index: int | None = None


class SearchResultItem(BaseModel):
    text: str
    distance: float
    rerank_score: float
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    document_id: str | None = None
    results: list[SearchResultItem]
