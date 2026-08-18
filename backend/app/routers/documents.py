from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.documents import (
    DeleteDocumentResponse,
    DocumentsResponse,
    ReindexDocumentResponse,
    RenameDocumentRequest,
    RenameDocumentResponse,
)
from app.services import documents as document_service
from app.services.ingestion import ingest_pdf

router = APIRouter(tags=["documents"])


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    print("\n========== PDF UPLOAD ==========")
    print(f"File: {file.filename}")

    contents = await file.read()
    print(f"PDF size: {len(contents) / 1024:.2f} KB")

    return ingest_pdf(contents, file.filename)


@router.get("/documents", response_model=DocumentsResponse)
def documents():
    print("\n========== DOCUMENTS ==========")
    docs = document_service.list_document_records()
    print(f"Found {len(docs)} documents.")
    return {"documents": docs}


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentResponse,
)
def delete_document(document_id: str):
    result = document_service.delete_document(document_id)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.patch(
    "/documents/{document_id}",
    response_model=RenameDocumentResponse,
)
def rename_document(document_id: str, body: RenameDocumentRequest):
    result = document_service.rename_document(document_id, body.source)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.post(
    "/documents/{document_id}/reindex",
    response_model=ReindexDocumentResponse,
)
def reindex_document(document_id: str):
    result = document_service.reindex_document(document_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Document or stored PDF not found",
        )
    return result
