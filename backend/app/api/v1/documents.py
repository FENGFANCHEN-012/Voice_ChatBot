from fastapi import APIRouter, UploadFile, File, Depends
from app.models.schemas import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    pass


@router.get("/", response_model=list[DocumentResponse])
async def list_documents():
    pass


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    pass
