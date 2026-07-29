from fastapi import APIRouter, UploadFile, File, Depends
from app.models.schemas import DocumentResponse
from app.services.document_service import DocumentService
from app.core.dependencies import get_document_service

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    result = await service.upload(file.filename or "untitled", await file.read())
    return DocumentResponse(**result)


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    service: DocumentService = Depends(get_document_service),
):
    docs = service.list_all()
    return [DocumentResponse(**d) for d in docs]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    service: DocumentService = Depends(get_document_service),
):
    ok = await service.delete(doc_id)
    return {"ok": ok}
