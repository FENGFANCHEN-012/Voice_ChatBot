import asyncio
from loguru import logger
from app.pipeline.rate_limiter import gemini_rate_limiter


class HyDE:
    def __init__(self, llm, hybrid_search, reranker, embedder, top_k: int = 5, score_threshold: float = 0.3):
        self.llm = llm
        self.hybrid_search = hybrid_search
        self.reranker = reranker
        self.embedder = embedder
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def generate_hypothetical(self, query: str) -> str:
        prompt = f"""Write a detailed, factual answer to the following question as if it were from an enterprise policy document. 
Include specific error codes, form numbers, directive names, time limits, and step-by-step procedures where applicable.
Do NOT say "I don't know" or "not mentioned". Write as if the answer exists in the document.

Question: {query}

Answer:"""
        for attempt in range(3):
            try:
                await gemini_rate_limiter.acquire()
                response = self.llm.model.generate_content(prompt)
                hypo = response.text.strip()
                if hypo:
                    logger.info(f"[HyDE] Generated hypothetical ({len(hypo)} chars): {hypo[:120]}...")
                    return hypo
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = 5 * (attempt + 1)
                    logger.warning(f"[HyDE] Quota hit, waiting {wait}s")
                    await asyncio.sleep(wait)
                else:
                    raise
        logger.error("[HyDE] Failed to generate hypothetical after 3 retries")
        return ""

    async def search(self, query: str) -> list[dict]:
        hypo = await self.generate_hypothetical(query)
        if not hypo:
            return []

        chunks = self.hybrid_search.search(hypo)
        if not chunks:
            logger.info("[HyDE] No chunks found from hypothetical")
            return []

        reranked = self.reranker.rerank(hypo, chunks, top_k=self.top_k)

        if reranked:
            avg_score = sum(c["score"] for c in reranked) / len(reranked)
            logger.info(f"[HyDE] Reranked {len(reranked)} chunks, avg_score={avg_score:.4f}")

        return reranked
