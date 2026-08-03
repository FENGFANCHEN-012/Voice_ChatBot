import asyncio
import io
import os
import re
import hashlib
import tempfile
from pathlib import Path

import edge_tts
from faster_whisper import WhisperModel
from app.config import settings

_ffmpeg_dirs = [
    str(Path(__file__).resolve().parent.parent.parent.parent / "venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries"),
    str(Path(__file__).resolve().parent.parent.parent.parent / ".venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries"),
]
for d in _ffmpeg_dirs:
    if os.path.isdir(d):
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        break


def clean_text_for_tts(text: str) -> str:
    # Replace slashes between word characters or standalone slashes with spaces so TTS doesn't say "slash"
    text = re.sub(r'(?<=\w)/(?=\w)', ' ', text)
    text = re.sub(r'[/\\#*_`~|{}]', ' ', text)
    text = re.sub(r'[—–]', ', ', text)
    text = re.sub(r'\s+-\s+', ', ', text)
    text = re.sub(r'(?m)^\s*[-•]\s+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class TTSCache:
    def __init__(self, max_size: int = 100):
        self._cache: dict[str, bytes] = {}
        self._max_size = max_size

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> bytes | None:
        return self._cache.get(self._key(text))

    def set(self, text: str, audio: bytes):
        if len(self._cache) >= self._max_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[self._key(text)] = audio

    def clear(self):
        self._cache.clear()


class AudioService:
    def __init__(self, model_size: str = "base"):
        use_gpu = settings.whisper_use_gpu
        device = "cuda" if use_gpu else "cpu"
        compute = "float16" if use_gpu else "int8"
        try:
            import torch
            if use_gpu and not torch.cuda.is_available():
                device = "cpu"
                compute = "int8"
        except ImportError:
            device = "cpu"
            compute = "int8"
        self.whisper = WhisperModel(model_size, device=device, compute_type=compute)
        self.tts_cache = TTSCache(max_size=100)

    async def transcribe(self, audio_data: bytes, filename: str = "audio.webm") -> dict:
        suffix = Path(filename).suffix or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            def _do_transcribe():
                segments, info = self.whisper.transcribe(tmp_path, beam_size=1)
                text = " ".join(seg.text for seg in segments)
                return text.strip(), info.language, info.duration

            text, lang, duration = await asyncio.to_thread(_do_transcribe)
            return {"text": text, "language": lang, "duration": duration}
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def synthesize(self, text: str) -> bytes:
        text = clean_text_for_tts(text[:500])
        if not text:
            return b""

        cached = self.tts_cache.get(text)
        if cached:
            return cached

        voices_to_try = [settings.tts_voice, "en-US-AvaNeural", "en-US-ChristopherNeural"]
        for v in voices_to_try:
            try:
                async def _stream_tts(voice_name: str):
                    communicate = edge_tts.Communicate(text, voice=voice_name, rate=settings.tts_rate, pitch=settings.tts_pitch)
                    buf = io.BytesIO()
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            buf.write(chunk["data"])
                    buf.seek(0)
                    return buf.getvalue()

                audio = await asyncio.wait_for(_stream_tts(v), timeout=12.0)
                if audio and len(audio) > 100:
                    self.tts_cache.set(text, audio)
                    return audio
            except Exception as e:
                from loguru import logger
                logger.warning(f"[TTS] Edge-TTS voice {v} failed or timed out: {e}")
                continue

        return b""


    async def synthesize_stream(self, text: str):
        text = clean_text_for_tts(text[:500])
        if not text:
            return

        cached = self.tts_cache.get(text)
        if cached:
            yield cached
            return

        try:
            communicate = edge_tts.Communicate(text, voice=settings.tts_voice, rate=settings.tts_rate, pitch=settings.tts_pitch)
            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
                    yield chunk["data"]
            buf.seek(0)
            audio = buf.getvalue()
            if audio:
                self.tts_cache.set(text, audio)
        except Exception as e:
            from loguru import logger
            logger.warning(f"[TTS] Edge-TTS stream failed: {e}")
