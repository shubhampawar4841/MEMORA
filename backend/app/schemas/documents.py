from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    document_id: str
    source: str | None = None
    pages: list[int] = Field(default_factory=list)
    chunks: int = 0


class DocumentsResponse(BaseModel):
    documents: list[DocumentItem]


class UploadSuccessResponse(BaseModel):
    filename: str | None = None
    document_id: str
    pages: int
    chunks: int
    embedding_dimension: int


class UploadErrorResponse(BaseModel):
    error: str


class RenameDocumentRequest(BaseModel):
    source: str


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: bool
    chunks_removed: int


class RenameDocumentResponse(BaseModel):
    document_id: str
    source: str


class ReindexDocumentResponse(BaseModel):
    document_id: str
    filename: str | None = None
    pages: int
    chunks: int
    embedding_dimension: int
    error: str | None = None
