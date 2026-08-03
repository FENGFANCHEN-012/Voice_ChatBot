import json
import asyncio
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import aiohttp

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

with open(Path(__file__).parent / "voice_test_dataset.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)

load_test_config = test_data["load_test_config"]


import os
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
TEST_QUERIES = [
    "What is the mandatory procedure when an employee experiences an SSO lockout error (Error Code ERR-SSO-4039)?",
    "My VPN keeps disconnecting every 10 minutes while working remotely. What should I do?",
    "What is the mandatory protocol when a facility building-wide fire alarm sounds (Alarm EVAC-FIRE-01)?",
    "What is the troubleshooting workflow when a CI/CD pipeline fails during database migration with Error LARAVEL-MIGRATE-FAIL?",
    "What is the server room temperature alert threshold?",
]


class LoadTester:
    def __init__(self):
        self.results = []

    async def create_session(self, session: aiohttp.ClientSession) -> str:
        async with session.post(f"{API_BASE}/sessions") as resp:
            data = await resp.json()
            return data["session_id"]

    async def query(self, session: aiohttp.ClientSession, session_id: str, query: str) -> dict:
        form = aiohttp.FormData()
        form.add_field("session_id", session_id)
        form.add_field("text", query)

        start = time.time()
        try:
            async with session.post(f"{API_BASE}/chats/query", data=form, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                latency = time.time() - start
                if resp.status != 200:
                    return {"status": "error", "code": resp.status, "latency": latency}
                data = await resp.json()
                return {"status": "success", "latency": latency, "answer_length": len(data.get("answer_text", ""))}
        except asyncio.TimeoutError:
            return {"status": "timeout", "latency": time.time() - start}
        except Exception as e:
            return {"status": "error", "error": str(e), "latency": time.time() - start}

    async def user_simulation(self, user_id: int, num_queries: int, delay: float) -> list:
        results = []
        async with aiohttp.ClientSession() as session:
            session_id = await self.create_session(session)

            for i in range(num_queries):
                query = TEST_QUERIES[i % len(TEST_QUERIES)]
                result = await self.query(session, session_id, query)
                result["user_id"] = user_id
                result["query_num"] = i
                results.append(result)
                await asyncio.sleep(delay)

        return results

    async def run_load_test(self, num_users: int, queries_per_user: int, ramp_up: float):
        print(f"\n  Running load test: {num_users} users, {queries_per_user} queries each")

        user_delay = ramp_up / max(num_users, 1)
        all_results = []

        start_time = time.time()

        tasks = []
        for i in range(num_users):
            task = asyncio.create_task(self.user_simulation(i, queries_per_user, 0.5))
            tasks.append(task)
            await asyncio.sleep(user_delay)

        user_results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        for user_result in user_results:
            if isinstance(user_result, Exception):
                continue
            all_results.extend(user_result)

        success = [r for r in all_results if r.get("status") == "success"]
        errors = [r for r in all_results if r.get("status") == "error"]
        timeouts = [r for r in all_results if r.get("status") == "timeout"]

        latencies = [r["latency"] for r in success]
        latencies.sort()

        total_queries = len(all_results)
        success_rate = len(success) / max(total_queries, 1)
        throughput = total_queries / max(total_time, 0.1)

        def percentile(data, p):
            if not data:
                return 0
            return data[min(int(len(data) * p), len(data) - 1)]

        stats = {
            "num_users": num_users,
            "queries_per_user": queries_per_user,
            "total_queries": total_queries,
            "success": len(success),
            "errors": len(errors),
            "timeouts": len(timeouts),
            "success_rate": success_rate,
            "total_time": total_time,
            "throughput": throughput,
            "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
            "p50_latency": percentile(latencies, 0.5),
            "p95_latency": percentile(latencies, 0.95),
            "p99_latency": percentile(latencies, 0.99),
        }

        print(f"    Queries: {total_queries} | Success: {len(success)} | Errors: {len(errors)} | Timeouts: {len(timeouts)}")
        print(f"    Throughput: {throughput:.2f} queries/sec | Success Rate: {success_rate*100:.1f}%")
        print(f"    Latency - Avg: {stats['avg_latency']:.3f}s | P50: {stats['p50_latency']:.3f}s | P95: {stats['p95_latency']:.3f}s | P99: {stats['p99_latency']:.3f}s")

        return stats

    async def run_all_tests(self):
        print("=" * 70)
        print("LOAD TEST")
        print("=" * 70)

        all_stats = []

        for num_users in load_test_config["concurrent_users"]:
            stats = await self.run_load_test(
                num_users=num_users,
                queries_per_user=load_test_config["queries_per_user"],
                ramp_up=load_test_config["ramp_up_seconds"],
            )
            all_stats.append(stats)
            await asyncio.sleep(2)

        print("\n" + "=" * 70)
        print("LOAD TEST SUMMARY")
        print("=" * 70)

        print(f"\n{'Users':<10} {'Queries':<10} {'Success%':<12} {'Throughput':<15} {'Avg Lat':<12} {'P95 Lat':<12}")
        print("-" * 71)

        for stats in all_stats:
            print(f"{stats['num_users']:<10} {stats['total_queries']:<10} {stats['success_rate']*100:<12.1f} {stats['throughput']:<15.2f} {stats['avg_latency']:<12.3f} {stats['p95_latency']:<12.3f}")

        print("\n" + "=" * 70)
        print("PERFORMANCE ASSESSMENT")
        print("=" * 70)

        max_users = all_stats[-1] if all_stats else None
        if max_users:
            if max_users["success_rate"] >= 0.99:
                print("[EXCELLENT] System handles load with >99% success rate")
            elif max_users["success_rate"] >= 0.95:
                print("[GOOD] System handles load with >95% success rate")
            elif max_users["success_rate"] >= 0.90:
                print("[WARNING] System shows degradation at high load")
            else:
                print("[CRITICAL] System fails under high load")

            if max_users["p95_latency"] < 5:
                print("[EXCELLENT] P95 latency under 5s at max load")
            elif max_users["p95_latency"] < 10:
                print("[GOOD] P95 latency under 10s at max load")
            else:
                print("[WARNING] High latency at max load")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"load_test_results_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "config": load_test_config,
                "results": all_stats,
            }, f, indent=2)

        print(f"\nDetailed results saved to: {output_file}")


async def main():
    tester = LoadTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
