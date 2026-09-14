"""TTS provider abstraction.

Kokoro-82M runs locally on CUDA/CPU and produces WAV; edge-tts streams MP3.
Selection lives in create_tts_provider(): settings.tts_provider == "auto"
picks kokoro only when CUDA is present, because on CPU kokoro synthesizes at
roughly real-time speed which makes sentence playback stutter.
"""

import asyncio
import hashlib
import io
import threading
from typing import AsyncIterator

import numpy as np
import soundfile as sf

SAMPLE_RATE = 24000
# WebSocket frame size for progressive transfer of finished WAV payloads
WS_CHUNK_BYTES = 8192


def wav_bytes_from_array(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, samplerate=sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


class KokoroTTS:
    format = "wav"

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self.voice = voice
        self.speed = speed
        self._pipeline = None
        # kokoro model is not thread-safe; serialize generation across requests
        self._gen_lock = threading.Lock()
        self._init_lock = threading.Lock()

    def _ensure_loaded(self):
        if self._pipeline is not None:
            return
        with self._init_lock:
            if self._pipeline is not None:
                return
            from kokoro import KPipeline

            # KModel picks CUDA automatically when torch sees a GPU,
            # falls back to CPU otherwise — same pattern as whisper init.
            self._pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")

    def _generate(self, text: str) -> bytes:
        import torch

        self._ensure_loaded()
        pieces: list[np.ndarray] = []
        with self._gen_lock:
            for _gs, _ps, audio in self._pipeline(
                text, voice=self.voice, speed=self.speed
            ):
                pieces.append(audio.detach().cpu().numpy())
        if not pieces:
            return b""
        return wav_bytes_from_array(np.concatenate(pieces))

    async def synthesize(self, text: str) -> bytes:
        return await asyncio.to_thread(self._generate, text)

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text)
        if not audio:
            return
        for i in range(0, len(audio), WS_CHUNK_BYTES):
            yield audio[i : i + WS_CHUNK_BYTES]


class EdgeTTSProvider:
    format = "mpeg"

    def __init__(self, voice: str, rate: str, pitch: str):
        import edge_tts

        self.edge_tts = edge_tts
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def synthesize(self, text: str) -> bytes:
        buf = io.BytesIO()

        async def _run():
            communicate = self.edge_tts.Communicate(
                text, voice=self.voice, rate=self.rate, pitch=self.pitch
            )
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])

        await asyncio.wait_for(_run(), timeout=12.0)
        buf.seek(0)
        return buf.getvalue()

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        communicate = self.edge_tts.Communicate(
            text, voice=self.voice, rate=self.rate, pitch=self.pitch
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]


def create_tts_provider(settings):
    """Factory honouring tts_provider=auto|kokoro|edge from config."""
    choice = settings.tts_provider.lower().strip()
    if choice == "auto":
        try:
            import torch

            cuda_ok = torch.cuda.is_available()
        except ImportError:
            cuda_ok = False
        if cuda_ok:
            try:
                import kokoro  # noqa: F401 — only check importability

                choice = "kokoro"
            except Exception:
                choice = "edge"
        else:
            choice = "edge"
    if choice == "kokoro":
        return KokoroTTS(voice=settings.tts_kokoro_voice, speed=settings.tts_kokoro_speed)
    return EdgeTTSProvider(voice=settings.tts_voice, rate=settings.tts_rate, pitch=settings.tts_pitch)


def cache_key(text: str, provider_name: str, voice: str) -> str:
    # provider+voice in the key so switching engines can't serve stale audio
    return hashlib.md5(f"{provider_name}:{voice}:{text}".encode()).hexdigest()
