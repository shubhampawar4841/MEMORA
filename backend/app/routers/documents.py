from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.folders import normalize_folder
from app.schemas.documents import (
    DeleteDocumentResponse,
    DocumentsResponse,
    ReindexDocumentResponse,
    RenameDocumentRequest,
    RenameDocumentResponse,
)
from app.services import documents as document_service
from app.services.ingestion import ingest_file

router = APIRouter(tags=["documents"])


async def _ingest_upload(
    file: UploadFile,
    folder: str,
    source: str | None,
):
    print("\n========== DOCUMENT UPLOAD ==========")
    print(f"File: {file.filename}")
    print(f"Folder: {folder}")

    contents = await file.read()
    print(f"Size: {len(contents) / 1024:.2f} KB")

    return ingest_file(
        contents,
        file.filename,
        folder=normalize_folder(folder),
        source=source,
    )


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    folder: str = Form("other"),
    source: str | None = Form(None),
):
    return await _ingest_upload(file, folder, source)


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    folder: str = Form("other"),
    source: str | None = Form(None),
):
    """Backward-compatible alias for /upload-document."""
    return await _ingest_upload(file, folder, source)


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
    if body.source is None and body.folder is None:
        raise HTTPException(
            status_code=400,
            detail="Provide source and/or folder to update",
        )
    result = document_service.rename_document(
        document_id,
        source=body.source,
        folder=body.folder,
    )
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
            detail="Document or stored file not found",
        )
    return result
