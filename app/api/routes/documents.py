from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.dependencies import get_document_service, get_knowledge_base_service

router = APIRouter(tags=["documents"])


@router.get("/documents")
async def list_documents(document_service=Depends(get_document_service)):
    return document_service.list_documents()


@router.post("/upload")
async def upload_documents(
    files: Annotated[list[UploadFile], File(...)],
    collection_id: Annotated[str | None, Form()] = None,
    document_service=Depends(get_document_service),
):
    uploaded_files = await document_service.upload_documents(files, collection_id=collection_id)
    return {"message": f"Successfully uploaded {len(uploaded_files)} files", "files": uploaded_files}


@router.delete("/documents/{filename:path}")
async def delete_document(filename: str, document_service=Depends(get_document_service)):
    deleted = document_service.delete_document(filename)
    return {"message": f"Deleted {deleted}"}


@router.post("/ingest")
async def ingest_documents(
    force: bool = Query(default=False),
    knowledge_base_service=Depends(get_knowledge_base_service),
):
    chunks = knowledge_base_service.sync(force=force)
    return {"message": "Knowledge base synchronized successfully", "chunks": chunks}
