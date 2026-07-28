from fastapi import APIRouter, Depends, UploadFile, File, Form
from typing import Optional
from app.models.schemas import QueryResponse, SessionResponse, MessageResponse
from app.services.chat_service import ChatService
from app.services.session_service import SessionService

router = APIRouter()


@router.post("/sessions", response_model=SessionResponse)
async def create_session():
    pass


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions():
    pass


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    pass


@router.post("/query", response_model=QueryResponse)
async def query(
    session_id: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
):
    pass


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str):
    pass
