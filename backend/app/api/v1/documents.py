import asyncio
import json
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from app.models.schemas import DocumentResponse
from app.services.document_service import DocumentService
from app.core.dependencies import get_document_service

router = APIRouter()



# Upload a document (PDF) to the server, parse it, embed it, and store it in the vector store.
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    
    result = await service.upload(file.filename or "untitled", await file.read())
    return DocumentResponse(**result)


@router.get("/{doc_id}/progress")
async def embedding_progress(
    doc_id: str,
    service: DocumentService = Depends(get_document_service),
):
    async def event_generator():
        while True:
            events = service.get_progress_events(doc_id)
            for event in events:
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("status") in ("complete", "error"):
                    return
            progress = service.get_progress(doc_id)
            if progress["status"] == "unknown":
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                return
            if progress["status"] == "complete":
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                return
            if progress["status"] == "error":
                yield f"data: {json.dumps({'status': 'error'})}\n\n"
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
