from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from loguru import logger
from app.models.schemas import QueryResponse, MessageResponse
from app.services.chat_service import ChatService
from app.services.audio_service import AudioService
from app.core.dependencies import get_chat_service, get_audio_service

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(
    session_id: str = Form(...),
    text: str = Form(""),
    chat_service: ChatService = Depends(get_chat_service),
):
    result = await chat_service.query(session_id, text)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return QueryResponse(**result)


@router.post("/voice-query", response_model=QueryResponse)
async def voice_query(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    chat_service: ChatService = Depends(get_chat_service),
    audio_service: AudioService = Depends(get_audio_service),
):
    try:
        audio_data = await audio.read()
        if not audio_data or len(audio_data) < 100:
            raise HTTPException(status_code=400, detail="Audio too short or empty")
        transcript = await audio_service.transcribe(audio_data, audio.filename or "audio.webm")
        logger.info(f"[VoiceQuery] Whisper transcribed ({transcript['language']}, {transcript['duration']:.1f}s): {transcript['text']}")
        if not transcript.get("text", "").strip():
            raise HTTPException(status_code=400, detail="Could not understand the audio")
        result = await chat_service.query(session_id, transcript["text"])
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return QueryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    msgs = chat_service.get_messages(session_id)
    return [MessageResponse(**m) for m in msgs]
