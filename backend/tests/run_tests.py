import sys
import asyncio
import aiohttp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

API_BASE = "http://localhost:8000/api/v1"


async def clear_cache():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_BASE}/chats/clear-cache") as resp:
                if resp.status == 200:
                    print("  Cache cleared")
    except Exception:
        pass


async def clear_sessions():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/sessions") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for s in data:
                        async with session.delete(f"{API_BASE}/sessions/{s['session_id']}") as r:
                            pass
                    print(f"  Cleared {len(data)} sessions")
    except Exception:
        pass


async def main():
    print("=" * 70)
    print("VOICE AGENT COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print("\nSelect test to run:")
    print("1. ASR Accuracy Test (tests Whisper transcription)")
    print("2. Latency Test (end-to-end response time)")
    print("3. Load Test (concurrent user performance)")
    print("4. RAG Evaluation (answer quality)")
    print("5. Run All Tests")
    print("0. Exit")

    choice = input("\nEnter choice (0-5): ").strip()

    if choice == "0":
        print("Exiting...")
        return

    print("\nPreparing tests...")
    await clear_cache()
    await clear_sessions()

    if choice == "1":
        from test_asr import main as asr_main
        await asr_main()
    elif choice == "2":
        from test_latency import main as latency_main
        await latency_main()
    elif choice == "3":
        from test_load import main as load_main
        await load_main()
    elif choice == "4":
        from evaluate_ragas import run_ragas_evaluation
        await run_ragas_evaluation()
    elif choice == "5":
        print("\nRunning all tests...\n")

        print("\n[1/4] ASR Accuracy Test")
        print("-" * 40)
        try:
            from test_asr import main as asr_main
            await asr_main()
        except Exception as e:
            print(f"ASR test failed: {e}")

        print("\n[2/4] Latency Test")
        print("-" * 40)
        try:
            await clear_cache()
            from test_latency import main as latency_main
            await latency_main()
        except Exception as e:
            print(f"Latency test failed: {e}")

        print("\n[3/4] Load Test")
        print("-" * 40)
        try:
            await clear_cache()
            from test_load import main as load_main
            await load_main()
        except Exception as e:
            print(f"Load test failed: {e}")

        print("\n[4/4] RAG Evaluation")
        print("-" * 40)
        try:
            await clear_cache()
            from evaluate_ragas import run_ragas_evaluation
            await run_ragas_evaluation()
        except Exception as e:
            print(f"RAG evaluation failed: {e}")

        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETE")
        print("=" * 70)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
