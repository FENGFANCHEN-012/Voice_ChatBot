import asyncio
import os
import re
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel
from loguru import logger
from app.config import settings
from app.pipeline.tts_engine import (
    EdgeTTSProvider,
    KokoroTTS,
    cache_key,
    create_tts_provider,
)

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

    def get(self, key: str) -> bytes | None:
        return self._cache.get(key)

    def set(self, key: str, audio: bytes):
        if len(self._cache) >= self._max_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = audio

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

        self.provider = create_tts_provider(settings)
        logger.info(f"[TTS] Provider selected: {type(self.provider).__name__} (format={self.provider.format})")

        # edge-tts kept as emergency fallback so the bot never goes silent
        # if kokoro fails (e.g. GPU OOM mid-session)
        if isinstance(self.provider, KokoroTTS):
            self.fallback_provider = EdgeTTSProvider(
                voice=settings.tts_voice, rate=settings.tts_rate, pitch=settings.tts_pitch
            )
        else:
            self.fallback_provider = None

        self.tts_cache = TTSCache(max_size=100)
        self._tts_lock = asyncio.Lock()

    @property
    def tts_format(self) -> str:
        return self.provider.format

    async def transcribe(self, audio_data: bytes, filename: str = "audio.webm") -> dict:
        suffix = Path(filename).suffix or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            def _do_transcribe():
                segments, info = self.whisper.transcribe(
                    tmp_path,
                    beam_size=1,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                text = " ".join(seg.text for seg in segments)
                return text.strip(), info.language, info.duration

            text, lang, duration = await asyncio.to_thread(_do_transcribe)
            return {"text": text, "language": lang, "duration": duration}
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _synth_via(self, provider, text: str) -> bytes:
        chunks = []
        async for chunk in provider.synthesize_stream(text):
            chunks.append(chunk)
        return b"".join(chunks)

    async def synthesize(self, text: str) -> bytes:
        """Full synthesis used by REST endpoint and WS stream."""
        text = clean_text_for_tts(text[:500])
        if not text:
            return b""

        key = cache_key(text, type(self.provider).__name__, getattr(self.provider, "voice", settings.tts_voice))
        cached = self.tts_cache.get(key)
        if cached is not None:
            return cached

        async with self._tts_lock:
            cached = self.tts_cache.get(key)
            if cached is not None:
                return cached
            try:
                audio = await self._synth_via(self.provider, text)
                if not audio:
                    raise RuntimeError("empty synthesis output")
            except Exception as e:
                logger.warning(f"[TTS] {type(self.provider).__name__} failed ({e}); trying edge-tts fallback")
                if self.fallback_provider is None:
                    return b""
                try:
                    audio = await self._synth_via(self.fallback_provider, text)
                except Exception as e2:
                    logger.warning(f"[TTS] edge-tts fallback also failed: {e2}")
                    return b""
            self.tts_cache.set(key, audio)
            return audio

    async def synthesize_stream(self, text: str):
        audio = await self.synthesize(text)
        if not audio:
            return
        for i in range(0, len(audio), 8192):
            yield audio[i : i + 8192]
