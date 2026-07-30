from fastapi import APIRouter, Depends
from app.models.schemas import SessionResponse
from app.services.session_service import SessionService
from app.core.dependencies import get_session_service

router = APIRouter()


@router.post("", response_model=SessionResponse)
async def create_session(
    service: SessionService = Depends(get_session_service),
):
    return SessionResponse(**service.create())



@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    service: SessionService = Depends(get_session_service),
):
    return [SessionResponse(**s) for s in service.list_all()]


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    ok = service.delete(session_id)
    return {"ok": ok}
