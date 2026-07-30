import io
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel
from gtts import gTTS


class AudioService:
    def __init__(self, model_size: str = "base"):
        self.whisper = WhisperModel(model_size, device="cpu", compute_type="int8")

    async def transcribe(self, audio_data: bytes, filename: str = "audio.webm") -> dict:
        suffix = Path(filename).suffix or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # start transcribing the audio file using the Whisper model
            segments, info = self.whisper.transcribe(tmp_path, beam_size=5)
            
            text = " ".join(seg.text for seg in segments)
            return {"text": text.strip(), "language": info.language, "duration": info.duration}
        finally:
            Path(tmp_path).unlink(missing_ok=True)




    # Synthesize text to speech using gTTS and return the audio as bytes.
    async def synthesize(self, text: str) -> bytes:
        tts = gTTS(text=text, lang="en", slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.getvalue()
