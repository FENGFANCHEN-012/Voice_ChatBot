from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import Response
from app.models.schemas import TranscribeResponse
from app.services.audio_service import AudioService
from app.core.dependencies import get_audio_service

router = APIRouter()


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    service: AudioService = Depends(get_audio_service),
):
    data = await audio.read()
    result = await service.transcribe(data, audio.filename or "audio.webm")
    return TranscribeResponse(**result)


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    service: AudioService = Depends(get_audio_service),
):
    audio_bytes = await service.synthesize(text)
    return Response(content=audio_bytes, media_type="audio/mpeg")
