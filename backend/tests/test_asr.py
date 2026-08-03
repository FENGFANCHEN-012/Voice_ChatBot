import json
import asyncio
import time
import os
import io
import tempfile
from pathlib import Path
from datetime import datetime

import edge_tts
from faster_whisper import WhisperModel

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))

with open(Path(__file__).parent / "voice_test_dataset.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)

asr_test_cases = test_data["asr_test_cases"]


class ASRTester:
    def __init__(self, model_size: str = "base"):
        print(f"Loading Whisper model: {model_size}")
        self.whisper = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.voice = "en-US-GuyNeural"

    async def text_to_audio(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, voice=self.voice, rate="+0%")
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return buf.getvalue()

    def transcribe(self, audio_path: str) -> str:
        segments, info = self.whisper.transcribe(audio_path, beam_size=5)
        return " ".join(seg.text for seg in segments)

    def compute_wer(self, reference: str, hypothesis: str) -> float:
        ref_words = reference.lower().split()
        hyp_words = hypothesis.lower().split()

        d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

        for i in range(len(ref_words) + 1):
            d[i][0] = i
        for j in range(len(hyp_words) + 1):
            d[0][j] = j

        for i in range(1, len(ref_words) + 1):
            for j in range(1, len(hyp_words) + 1):
                if ref_words[i-1] == hyp_words[j-1]:
                    d[i][j] = d[i-1][j-1]
                else:
                    d[i][j] = min(
                        d[i-1][j] + 1,
                        d[i][j-1] + 1,
                        d[i-1][j-1] + 1
                    )

        return d[len(ref_words)][len(hyp_words)] / max(len(ref_words), 1)

    def compute_cer(self, reference: str, hypothesis: str) -> float:
        ref_chars = list(reference.lower())
        hyp_chars = list(hypothesis.lower())

        d = [[0] * (len(hyp_chars) + 1) for _ in range(len(ref_chars) + 1)]

        for i in range(len(ref_chars) + 1):
            d[i][0] = i
        for j in range(len(hyp_chars) + 1):
            d[0][j] = j

        for i in range(1, len(ref_chars) + 1):
            for j in range(1, len(hyp_chars) + 1):
                if ref_chars[i-1] == hyp_chars[j-1]:
                    d[i][j] = d[i-1][j-1]
                else:
                    d[i][j] = min(
                        d[i-1][j] + 1,
                        d[i][j-1] + 1,
                        d[i-1][j-1] + 1
                    )

        return d[len(ref_chars)][len(hyp_chars)] / max(len(ref_chars), 1)

    def keyword_accuracy(self, expected_text: str, transcribed: str, keywords: list) -> float:
        expected_lower = expected_text.lower()
        transcribed_lower = transcribed.lower()

        found = sum(1 for kw in keywords if kw.lower() in transcribed_lower)
        return found / max(len(keywords), 1)

    async def run_test(self, test_case: dict) -> dict:
        test_id = test_case["id"]
        expected = test_case["expected_text"]
        keywords = test_case.get("keywords", [])

        print(f"  [{test_id:02d}] Generating audio for: {expected[:50]}...")

        audio_bytes = await self.text_to_audio(expected)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            start_time = time.time()
            transcribed = self.transcribe(tmp_path)
            latency = time.time() - start_time

            wer = self.compute_wer(expected, transcribed)
            cer = self.compute_cer(expected, transcribed)
            kw_acc = self.keyword_accuracy(expected, transcribed, keywords)

            return {
                "id": test_id,
                "category": test_case["category"],
                "difficulty": test_case["difficulty"],
                "expected": expected,
                "transcribed": transcribed,
                "wer": wer,
                "cer": cer,
                "keyword_accuracy": kw_acc,
                "latency_seconds": latency,
                "pass": wer < 0.3,
            }
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def run_all_tests(self):
        print("=" * 70)
        print("ASR ACCURACY TEST")
        print("=" * 70)

        results = []
        for test_case in asr_test_cases:
            result = await self.run_test(test_case)
            results.append(result)

            status = "PASS" if result["pass"] else "FAIL"
            print(f"  [{result['id']:02d}] {status} WER={result['wer']:.3f} CER={result['cer']:.3f} KW={result['keyword_accuracy']:.3f}")

        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)

        total = len(results)
        passed = sum(1 for r in results if r["pass"])
        avg_wer = sum(r["wer"] for r in results) / total
        avg_cer = sum(r["cer"] for r in results) / total
        avg_kw = sum(r["keyword_accuracy"] for r in results) / total
        avg_latency = sum(r["latency_seconds"] for r in results) / total

        print(f"Total Tests:     {total}")
        print(f"Passed:          {passed}/{total} ({passed/total*100:.1f}%)")
        print(f"Average WER:     {avg_wer:.3f}")
        print(f"Average CER:     {avg_cer:.3f}")
        print(f"Average KW Acc:  {avg_kw:.3f}")
        print(f"Average Latency: {avg_latency:.3f}s")

        by_category = {}
        for r in results:
            cat = r["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(r)

        print("\nBy Category:")
        for cat, cat_results in sorted(by_category.items()):
            n = len(cat_results)
            cat_wer = sum(r["wer"] for r in cat_results) / n
            cat_passed = sum(1 for r in cat_results if r["pass"])
            print(f"  {cat:<25} WER={cat_wer:.3f} Pass={cat_passed}/{n}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"asr_results_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "pass_rate": passed / total,
                    "avg_wer": avg_wer,
                    "avg_cer": avg_cer,
                    "avg_keyword_accuracy": avg_kw,
                    "avg_latency": avg_latency,
                },
                "results": results,
            }, f, indent=2)

        print(f"\nDetailed results saved to: {output_file}")
        return results


async def main():
    tester = ASRTester(model_size="base")
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
