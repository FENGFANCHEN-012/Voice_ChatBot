import json
import asyncio
import aiohttp
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from google import genai
from ragas import evaluate, EvaluationDataset
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness, ContextRecall, ContextPrecision, AnswerCorrectness

from pathlib import Path

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NUM_QUESTIONS = 30



async def create_session(session: aiohttp.ClientSession) -> str:
    async with session.post(f"{API_BASE}/sessions") as resp:
        data = await resp.json()
        return data["session_id"]


async def query_rag(session: aiohttp.ClientSession, session_id: str, question: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            form = aiohttp.FormData()
            form.add_field("session_id", session_id)
            form.add_field("text", question)
            timeout = aiohttp.ClientTimeout(total=120)
            async with session.post(f"{API_BASE}/chats/query", data=form, timeout=timeout) as resp:
                if resp.status != 200:
                    return {"answer_text": f"ERROR: {resp.status}", "chunks": []}
                return await resp.json()
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            if attempt < max_retries - 1:
                print(f"    Retry {attempt + 1}/{max_retries} for query...")
                await asyncio.sleep(2)
            else:
                return {"answer_text": f"TIMEOUT after {max_retries} retries", "chunks": []}


async def run_ragas_evaluation():
    print("=" * 70)
    print("RAGAS EVALUATION (Real RAGAS Library + Gemini 3.5 Flash Lite)")
    print("=" * 70)

    print("\nLoading evaluation dataset...")
    dataset_path = Path(__file__).parent / "evaluation_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        full_dataset = json.load(f)

    dataset = full_dataset[:NUM_QUESTIONS]
    print(f"Loaded {len(full_dataset)} questions, using {len(dataset)} for evaluation")

    print("\nCollecting RAG responses...")
    results = []
    headers = {"ngrok-skip-browser-warning": "true"}
    async with aiohttp.ClientSession(headers=headers) as session:
        session_id = await create_session(session)
        print(f"Created session: {session_id}")

        for i, item in enumerate(dataset):
            print(f"  [{i+1}/{len(dataset)}] {item['category']}: {item['question'][:50]}...")

            response = await query_rag(session, session_id, item["question"])
            answer = response.get("answer_text", "")
            chunks = response.get("chunks", [])

            results.append({
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "generated_answer": answer,
                "ground_truth": item["ground_truth"],
                "chunks": chunks,
                "num_chunks": len(chunks),
            })

            await asyncio.sleep(0.5)

    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    preferred_provider = os.getenv("LLM_PROVIDER", "deepseek").lower()

    if preferred_provider == "gemini" and gemini_key:
        print("\nInitializing RAGAS evaluator with Google Gemini...")
        client = genai.Client(api_key=gemini_key)
        evaluator_llm = llm_factory("gemini-2.0-flash-lite", provider="google", client=client)
    elif deepseek_key:
        print("\nInitializing RAGAS evaluator with DeepSeek V3 (deepseek-chat)...")
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
        evaluator_llm = llm_factory("deepseek-chat", provider="openai", client=openai_client)
    elif gemini_key:
        print("\nInitializing RAGAS evaluator with Google Gemini...")
        client = genai.Client(api_key=gemini_key)
        evaluator_llm = llm_factory("gemini-2.0-flash-lite", provider="google", client=client)
    else:
        raise ValueError("Please set either DEEPSEEK_API_KEY or GEMINI_API_KEY to run RAGAS evaluation.")

    print("Building RAGAS evaluation dataset...")
    eval_data = []
    for r in results:
        contexts = [c["content"] for c in r.get("chunks", [])]
        eval_data.append({
            "user_input": r["question"],
            "retrieved_contexts": contexts if contexts else ["No context retrieved"],
            "response": r["generated_answer"],
            "reference": r["ground_truth"],
        })

    evaluation_dataset = EvaluationDataset.from_list(eval_data)

    metrics = [
        Faithfulness(llm=evaluator_llm),
        ContextRecall(llm=evaluator_llm),
        ContextPrecision(llm=evaluator_llm),
        AnswerCorrectness(llm=evaluator_llm),
    ]

    print(f"\nRunning RAGAS evaluation on {len(dataset)} questions...")
    print("This will make ~120 LLM calls (4 metrics x 30 questions)")
    print("Estimated time: 5-10 minutes\n")

    result = evaluate(
        dataset=evaluation_dataset,
        metrics=metrics,
    )

    print("\n" + "=" * 70)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 70)

    def _to_avg(val):
        if isinstance(val, (list, tuple)):
            clean = [x for x in val if x is not None]
            return sum(clean) / len(clean) if clean else 0.0
        return float(val) if val is not None else 0.0

    metric_scores = {
        "faithfulness": _to_avg(result["faithfulness"]),
        "context_recall": _to_avg(result["context_recall"]),
        "context_precision": _to_avg(result["context_precision"]),
        "answer_correctness": _to_avg(result["answer_correctness"]),
    }


    for metric_name, score in metric_scores.items():
        print(f"{metric_name:<25}: {score:.3f}/1.000")

    print("-" * 70)
    overall = sum(metric_scores.values()) / len(metric_scores)
    print(f"{'OVERALL SCORE':<25}: {overall:.3f}/1.000")

    print("\n" + "=" * 70)
    print("SCORES BY CATEGORY")
    print("=" * 70)
    print(f"{'Category':<25} {'Faithful':<12} {'Recall':<12} {'Precision':<12} {'Correct':<12}")
    print("-" * 73)

    category_metrics = {}
    for i, item in enumerate(dataset):
        cat = item["category"]
        if cat not in category_metrics:
            category_metrics[cat] = {
                "faithfulness": [],
                "context_recall": [],
                "context_precision": [],
                "answer_correctness": [],
            }
        category_metrics[cat]["faithfulness"].append(metric_scores["faithfulness"][i])
        category_metrics[cat]["context_recall"].append(metric_scores["context_recall"][i])
        category_metrics[cat]["context_precision"].append(metric_scores["context_precision"][i])
        category_metrics[cat]["answer_correctness"].append(metric_scores["answer_correctness"][i])

    for cat, cat_scores in sorted(category_metrics.items()):
        n = len(cat_scores["faithfulness"])
        avg_faith = sum(cat_scores["faithfulness"]) / n
        avg_recall = sum(cat_scores["context_recall"]) / n
        avg_prec = sum(cat_scores["context_precision"]) / n
        avg_correct = sum(cat_scores["answer_correctness"]) / n
        print(f"{cat:<25} {avg_faith:.3f}{'':<7} {avg_recall:.3f}{'':<7} {avg_prec:.3f}{'':<7} {avg_correct:.3f}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ragas_results_{timestamp}.json"

    output_data = {
        "summary": {
            "total_questions": len(dataset),
            "overall_score": overall,
            "metrics": metric_scores,
        },
        "by_category": {
            cat: {
                metric: sum(scores) / len(scores) if scores else 0
                for metric, scores in cat_metrics.items()
            }
            for cat, cat_metrics in category_metrics.items()
        },
        "detailed_results": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: {output_file}")

    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    if metric_scores["faithfulness"] < 0.7:
        print("- LOW FAITHFULNESS: Answers may contain hallucinations")
        print("  → Improve context retrieval or add source verification")
    if metric_scores["context_recall"] < 0.7:
        print("- LOW RECALL: Missing relevant context from documents")
        print("  → Increase top_k or improve chunking strategy")
    if metric_scores["context_precision"] < 0.7:
        print("- LOW PRECISION: Retrieved chunks are not relevant")
        print("  → Improve retrieval (hybrid search, reranking)")
    if metric_scores["answer_correctness"] < 0.7:
        print("- LOW CORRECTNESS: Answers are factually wrong")
        print("  → Improve LLM prompt or add more context")


if __name__ == "__main__":
    asyncio.run(run_ragas_evaluation())
