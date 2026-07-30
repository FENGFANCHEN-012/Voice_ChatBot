from fastapi import Request, HTTPException, Depends
from app.store.session_store import SessionStore
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.services.session_service import SessionService
from app.services.audio_service import AudioService


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_session_service(request: Request) -> SessionService:
    return request.app.state.session_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_audio_service(request: Request) -> AudioService:
    return request.app.state.audio_service


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
