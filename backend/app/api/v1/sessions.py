from fastapi import APIRouter, Depends, HTTPException, Form
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


@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: str,
    title: str = Form(...),
    service: SessionService = Depends(get_session_service),
):
    result = service.rename(session_id, title)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**result)


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service),
):
    ok = service.delete(session_id)
    return {"ok": ok}
