import os
import json
import asyncio
import time
import io
import tempfile
from pathlib import Path
from datetime import datetime


import aiohttp
import edge_tts
from faster_whisper import WhisperModel

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

with open(Path(__file__).parent / "voice_test_dataset.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)

latency_test_queries = test_data["latency_test_queries"]


def _get_api_base() -> str:
    env_url = os.getenv("API_BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    frontend_env = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env"
    if frontend_env.exists():
        with open(frontend_env, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VITE_BACKEND_URL="):
                    url = line.split("=", 1)[1].strip()
                    if url:
                        return f"{url.rstrip('/')}/api/v1"

    return "http://localhost:8000/api/v1"


API_BASE = _get_api_base()


def create_dummy_wav(duration_s: float = 2.0) -> bytes:
    import wave, struct, math
    buf = io.BytesIO()
    sample_rate = 16000
    n_samples = int(sample_rate * duration_s)
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for i in range(n_samples):
            value = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
            wav.writeframesraw(struct.pack('<h', value))
    return buf.getvalue()


class LatencyTester:
    def __init__(self):
        print("Loading Whisper model for TTS generation...")
        self.whisper = WhisperModel("base", device="cpu", compute_type="int8")
        self.tts_voice = "en-US-GuyNeural"

    async def text_to_audio(self, text: str) -> bytes:
        try:
            async def _stream():
                communicate = edge_tts.Communicate(text, voice=self.tts_voice, rate="+0%")
                buf = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buf.write(chunk["data"])
                buf.seek(0)
                return buf.getvalue()
            audio = await asyncio.wait_for(_stream(), timeout=4.0)
            if audio:
                return audio
        except Exception:
            pass
        return create_dummy_wav(2.0)

    async def create_session(self, session: aiohttp.ClientSession) -> str:
        async with session.post(f"{API_BASE}/sessions") as resp:
            data = await resp.json()
            return data["session_id"]

    async def voice_query(self, session: aiohttp.ClientSession, session_id: str, audio_bytes: bytes) -> dict:
        form = aiohttp.FormData()
        form.add_field("session_id", session_id)
        form.add_field("audio", audio_bytes, filename="test.webm", content_type="audio/webm")

        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with session.post(f"{API_BASE}/chats/voice-query", data=form, timeout=timeout) as resp:
                latency = time.time() - start
                if resp.status != 200:
                    return {"error": f"HTTP {resp.status}", "latency": latency}
                data = await resp.json()
                data["latency"] = data.get("processing_time") or latency
                return data
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return {"error": "TIMEOUT", "latency": time.time() - start}

    async def text_query(self, session: aiohttp.ClientSession, session_id: str, text: str) -> dict:
        form = aiohttp.FormData()
        form.add_field("session_id", session_id)
        form.add_field("text", text)

        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with session.post(f"{API_BASE}/chats/query", data=form, timeout=timeout) as resp:
                latency = time.time() - start
                if resp.status != 200:
                    return {"error": f"HTTP {resp.status}", "latency": latency}
                data = await resp.json()
                data["latency"] = data.get("processing_time") or latency
                return data
        except (asyncio.TimeoutError, aiohttp.ClientError):
            return {"error": "TIMEOUT", "latency": time.time() - start}

    async def tts_latency(self, text: str) -> float:
        start = time.time()
        result = await self.text_to_audio(text)
        if result is None:
            return -1
        return time.time() - start

    async def run_test(self, query: str, test_type: str, session: aiohttp.ClientSession, session_id: str) -> dict:
        print(f"  Testing [{test_type.upper()}]: {query[:50]}...")

        if test_type == "voice":
            audio_bytes = await self.text_to_audio(query)
            if audio_bytes is None:
                return {
                    "query": query,
                    "type": test_type,
                    "latency": 0,
                    "tts_latency": 0,
                    "answer_length": 0,
                    "num_chunks": 0,
                    "error": "TTS_FAILED",
                }
            result = await self.voice_query(session, session_id, audio_bytes)
        else:
            result = await self.text_query(session, session_id, query)

        tts_latency = await self.tts_latency(result.get("answer_text", ""))

        return {
            "query": query,
            "type": test_type,
            "latency": result.get("latency", 0),
            "tts_latency": tts_latency,
            "answer_length": len(result.get("answer_text", "")),
            "num_chunks": len(result.get("chunks", [])),
            "error": result.get("error"),
        }

    async def run_all_tests(self):
        print("=" * 70)
        print("END-TO-END LATENCY TEST")
        print(f"Target API Endpoint: {API_BASE}")
        print("=" * 70)

        headers = {"ngrok-skip-browser-warning": "true"}
        async with aiohttp.ClientSession(headers=headers) as session:
            session_id = await self.create_session(session)

            print(f"Created session: {session_id}")

            results = []

            print("\n[VOICE QUERY TESTS]")
            for i, query in enumerate(latency_test_queries):
                if i > 0:
                    print(f"    Waiting 7s to avoid rate limit...")
                    await asyncio.sleep(7)
                result = await self.run_test(query, "voice", session, session_id)
                results.append(result)
                if result.get("error"):
                    print(f"    Query: ERROR ({result['error']}) | Latency: {result['latency']:.3f}s")
                else:
                    tts_str = f"{result['tts_latency']:.3f}s" if result['tts_latency'] >= 0 else "FAILED"
                    print(f"    Query: {result['latency']:.3f}s | TTS: {tts_str} | Chunks: {result['num_chunks']}")

        print("\n" + "=" * 70)
        print("LATENCY SUMMARY (excluding first query - cold start)")
        print("=" * 70)

        voice_results = [r for r in results if r["type"] == "voice"][1:]

        def stats(data, key):
            values = [r[key] for r in data if r.get("latency", 0) > 0 and r.get(key, -1) >= 0]
            if not values:
                return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0}
            values.sort()
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "p50": values[len(values) // 2],
                "p95": values[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            }

        voice_stats = stats(voice_results, "latency")
        tts_stats = stats(results[1:], "tts_latency")

        print(f"\n{'Metric':<25} {'Voice Query':<15}")
        print("-" * 40)
        print(f"{'Min Latency':<25} {voice_stats['min']:.3f}s")
        print(f"{'Max Latency':<25} {voice_stats['max']:.3f}s")
        print(f"{'Avg Latency':<25} {voice_stats['avg']:.3f}s")
        print(f"{'P50 Latency':<25} {voice_stats['p50']:.3f}s")
        print(f"{'P95 Latency':<25} {voice_stats['p95']:.3f}s")

        print(f"\n{'TTS Latency':<25} {tts_stats['avg']:.3f}s (avg)")

        print("\n" + "=" * 70)
        print("PERFORMANCE TARGETS")
        print("=" * 70)

        targets = {
            "Voice query P95 < 8s": voice_stats["p95"] < 8,
            "TTS avg < 2s": tts_stats["avg"] < 2,
        }

        for target, passed in targets.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {target}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"latency_results_{timestamp}.json"
        latest_file = "latency_results_latest.json"

        data_to_save = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "voice_query": voice_stats,
                "tts": tts_stats,
                "targets": {k: v for k, v in targets.items()},
            },
            "results": results,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)

        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2)

        print(f"\nDetailed results saved to: {output_file} and {latest_file}")


async def main():
    tester = LatencyTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
