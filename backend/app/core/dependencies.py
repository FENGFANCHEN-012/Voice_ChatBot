from fastapi import Request, HTTPException, Depends
from app.store.session_store import SessionStore
from app.services.document_service import DocumentService


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


async def get_current_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
