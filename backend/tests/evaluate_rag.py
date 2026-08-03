import json
import asyncio
import aiohttp
import csv
from datetime import datetime


API_BASE = "http://localhost:8000/api/v1"


async def create_session(session: aiohttp.ClientSession) -> str:
    async with session.post(f"{API_BASE}/sessions") as resp:
        data = await resp.json()
        return data["session_id"]


async def query_rag(session: aiohttp.ClientSession, session_id: str, question: str) -> dict:
    form = aiohttp.FormData()
    form.add_field("session_id", session_id)
    form.add_field("text", question)
    async with session.post(f"{API_BASE}/chats/query", data=form) as resp:
        if resp.status != 200:
            return {"answer_text": f"ERROR: {resp.status}", "chunks": []}
        return await resp.json()


def score_answer(generated: str, ground_truth: str) -> int:
    generated_lower = generated.lower().strip()
    ground_truth_lower = ground_truth.lower().strip()

    if ground_truth_lower == "not mentioned in the document.":
        if "not mentioned" in generated_lower or "cannot find" in generated_lower or "not in" in generated_lower:
            return 2
        return 0

    truth_words = set(ground_truth_lower.split())
    gen_words = set(generated_lower.split())
    overlap = len(truth_words & gen_words) / max(len(truth_words), 1)

    if overlap > 0.7:
        return 2
    elif overlap > 0.3:
        return 1
    return 0


def score_faithfulness(answer: str, chunks: list) -> int:
    if not chunks:
        return 1
    return 2


async def run_evaluation():
    with open("evaluation_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    results = []
    async with aiohttp.ClientSession() as session:
        session_id = await create_session(session)

        for i, item in enumerate(dataset):
            print(f"[{i+1}/{len(dataset)}] {item['category']}: {item['question'][:60]}...")

            response = await query_rag(session, session_id, item["question"])
            answer = response.get("answer_text", "")
            chunks = response.get("chunks", [])

            retrieval_score = 2 if chunks else 0
            answer_score = score_answer(answer, item["ground_truth"])
            faithfulness_score = score_faithfulness(answer, chunks)
            completeness_score = answer_score

            results.append({
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "generated_answer": answer,
                "ground_truth": item["ground_truth"],
                "retrieval_score": retrieval_score,
                "answer_score": answer_score,
                "faithfulness_score": faithfulness_score,
                "completeness_score": completeness_score,
                "num_chunks": len(chunks),
                "keywords": ", ".join(item.get("keywords", [])),
            })

            await asyncio.sleep(0.5)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"evaluation_results_{timestamp}.csv"

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"EVALUATION COMPLETE")
    print(f"{'='*60}")

    total = len(results)
    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "retrieval": 0, "answer": 0, "faithfulness": 0, "completeness": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["retrieval"] += r["retrieval_score"]
        by_category[cat]["answer"] += r["answer_score"]
        by_category[cat]["faithfulness"] += r["faithfulness_score"]
        by_category[cat]["completeness"] += r["completeness_score"]

    print(f"\nCategory Scores (avg /2):")
    print(f"{'Category':<25} {'Retrieval':<12} {'Answer':<12} {'Faithful':<12} {'Complete':<12}")
    print("-" * 73)

    for cat, scores in sorted(by_category.items()):
        n = scores["count"]
        print(f"{cat:<25} {scores['retrieval']/n:.1f}/2{'':<7} {scores['answer']/n:.1f}/2{'':<7} {scores['faithfulness']/n:.1f}/2{'':<7} {scores['completeness']/n:.1f}/2")

    total_retrieval = sum(r["retrieval_score"] for r in results)
    total_answer = sum(r["answer_score"] for r in results)
    total_faithfulness = sum(r["faithfulness_score"] for r in results)
    total_completeness = sum(r["completeness_score"] for r in results)

    print("-" * 73)
    print(f"{'OVERALL':<25} {total_retrieval/total:.1f}/2{'':<7} {total_answer/total:.1f}/2{'':<7} {total_faithfulness/total:.1f}/2{'':<7} {total_completeness/total:.1f}/2")
    print(f"\nResults saved to: {csv_file}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
