from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    document_id: str
    source: str | None = None
    folder: str = "other"
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
    folder: str = "other"
    source: str | None = None


class UploadErrorResponse(BaseModel):
    error: str


class RenameDocumentRequest(BaseModel):
    source: str | None = None
    folder: str | None = None


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted: bool
    chunks_removed: int


class RenameDocumentResponse(BaseModel):
    document_id: str
    source: str | None = None
    folder: str = "other"


class ReindexDocumentResponse(BaseModel):
    document_id: str
    filename: str | None = None
    pages: int
    chunks: int
    embedding_dimension: int
    error: str | None = None
    folder: str | None = None
