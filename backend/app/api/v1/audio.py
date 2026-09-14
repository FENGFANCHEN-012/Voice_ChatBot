from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from loguru import logger
from app.models.schemas import TranscribeResponse
from app.services.audio_service import AudioService
from app.core.dependencies import get_audio_service

router = APIRouter()


@router.post("/transcribe", response_model=TranscribeResponse)

async def transcribe_audio(
    audio: UploadFile = File(...),
    service: AudioService = Depends(get_audio_service),
):
    try:
        data = await audio.read()
        result = await service.transcribe(data, audio.filename or "audio.webm")
        return TranscribeResponse(**result)
    except Exception as e:
        logger.error(f"Transcribe failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")




@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    service: AudioService = Depends(get_audio_service),
):
    try:
        audio_bytes = await service.synthesize(text)
        media_type = "audio/wav" if getattr(service, "tts_format", "mpeg") == "wav" else "audio/mpeg"
        return Response(content=audio_bytes, media_type=media_type)
    except Exception as e:
        logger.error(f"Synthesize failed: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@router.post("/synthesize-stream")
async def synthesize_speech_stream(
    text: str = Form(...),
    service: AudioService = Depends(get_audio_service),
):
    try:
        media_type = "audio/wav" if getattr(service, "tts_format", "mpeg") == "wav" else "audio/mpeg"
        return StreamingResponse(
            service.synthesize_stream(text),
            media_type=media_type,
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        logger.error(f"Synthesize stream failed: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")