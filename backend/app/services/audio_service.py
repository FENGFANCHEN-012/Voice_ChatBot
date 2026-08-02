import io
import os
import re
import tempfile
from pathlib import Path

import edge_tts
from faster_whisper import WhisperModel

_ffmpeg_dirs = [
    str(Path(__file__).resolve().parent.parent.parent.parent / "venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries"),
    str(Path(__file__).resolve().parent.parent.parent.parent / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries"),
]
for d in _ffmpeg_dirs:
    if os.path.isdir(d):
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        break


def clean_text_for_tts(text: str) -> str:
    text = re.sub(r'[^\w\s.,!?\-\'\"]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class AudioService:
    def __init__(self, model_size: str = "base"):
        self.whisper = WhisperModel(model_size, device="cpu", compute_type="int8")

    async def transcribe(self, audio_data: bytes, filename: str = "audio.webm") -> dict:
        
        suffix = Path(filename).suffix or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            segments, info = self.whisper.transcribe(tmp_path, beam_size=5)
            
            text = " ".join(seg.text for seg in segments)
            return {"text": text.strip(), "language": info.language, "duration": info.duration}
        finally:
            Path(tmp_path).unlink(missing_ok=True)


    async def synthesize(self, text: str) -> bytes:
        
        # remove unsupported characters and limit to 500 characters for TTS
        text = clean_text_for_tts(text[:500])
        if not text:
            return b""
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural", rate="+10%")
        buf = io.BytesIO()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return buf.getvalue()

    async def synthesize_stream(self, text: str):
        text = clean_text_for_tts(text[:500])
        if not text:
            return
        communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural", rate="+10%")
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
