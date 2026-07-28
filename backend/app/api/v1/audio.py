from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import Response
from app.models.schemas import TranscribeResponse

router = APIRouter()


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    pass



@router.post("/synthesize")
async def synthesize_speech(text: str = Form(...)):
    pass
