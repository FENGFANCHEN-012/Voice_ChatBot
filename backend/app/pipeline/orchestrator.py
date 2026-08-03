import asyncio
from loguru import logger
from app.config import settings
from app.pipeline.retriever import Retriever
from app.pipeline.reranker import Reranker
from app.pipeline.llm import LLMClient
from app.pipeline.query_expander import QueryExpander
from app.pipeline.hybrid_search import HybridSearch
from app.pipeline.fallback import Fallback
from app.pipeline.agent_rag import AgentRAG
from app.pipeline.query_cache import QueryCache
from app.pipeline.hyde import HyDE


class PipelineOrchestrator:
    def __init__(
        self,
        retriever: Retriever,
        reranker: Reranker,
        llm: LLMClient,
        query_expander: QueryExpander,
        hybrid: HybridSearch,
        fallback: Fallback,
        agent: AgentRAG,
        hyde: HyDE | None = None,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm
        self.query_expander = query_expander
        self.hybrid = hybrid
        self.fallback = fallback
        self.agent = agent
        self.hyde = hyde
        self.cache = QueryCache(ttl_seconds=3600, max_size=100)

    async def answer_question(self, text: str, history: list[dict] | None = None) -> dict:
        logger.info(f"[Pipeline] Query: {text}")

        cached = self.cache.get(text)
        if cached:
            logger.info(f"[Pipeline] Cache hit (cache size: {self.cache.size})")
            return cached

        logger.info("[Pipeline] Cache miss → simple path (no agent, no expansion)")
        result = await self._simple_path(text, history)
        self.cache.set(text, result)
        return result

    async def answer_question_stream(self, text: str, history: list[dict] | None = None):
        logger.info(f"[Pipeline] Stream query: {text}")

        cached = self.cache.get(text)
        if cached:
            logger.info(f"[Pipeline] Cache hit (cache size: {self.cache.size})")
            yield {"type": "token", "content": cached["answer_text"]}
            yield {"type": "done", "chunks": cached["chunks"]}
            return

        logger.info("[Pipeline] Cache miss → streaming path")
        chunks = await asyncio.to_thread(self.hybrid.search, text)
        top_chunks = await asyncio.to_thread(self.reranker.rerank, text, chunks, top_k=settings.reranker_top_k)
        context = [c["text"] for c in top_chunks]

        full_answer = ""
        async for token in self.llm.generate_stream(text, context, history=history):
            full_answer += token
            yield {"type": "token", "content": token}

        result_chunks = [
            {"content": c["text"], "page": c.get("page"), "score": float(c.get("score", 0))}
            for c in top_chunks
        ]

        self.cache.set(text, {"answer_text": full_answer, "chunks": result_chunks})
        yield {"type": "done", "chunks": result_chunks}

    async def _handle_out_of_scope(self, text: str, history: list[dict] | None = None) -> dict:
        answer = await self.llm.generate(text, [], history=history)
        return {
            "answer_text": answer,
            "rate_limit_wait": getattr(self.llm, "last_rate_limit_wait", 0.0),
            "chunks": [],
        }

    async def _simple_path(self, original: str, history: list[dict] | None = None) -> dict:
        chunks = await asyncio.to_thread(self.hybrid.search, original)
        top_chunks = await asyncio.to_thread(self.reranker.rerank, original, chunks, top_k=settings.reranker_top_k)
        context = [c["text"] for c in top_chunks]
        answer = await self.llm.generate(original, context, history=history)
        return {
            "answer_text": answer,
            "rate_limit_wait": getattr(self.llm, "last_rate_limit_wait", 0.0),
            "chunks": [
                {"content": c["text"], "page": c.get("page"), "score": float(c.get("score", 0))}
                for c in top_chunks
            ],
        }

    async def _full_path(self, original: str, history: list[dict] | None = None) -> dict:
        result = await self.fallback.execute(original, history=history)

        if result["passed"]:
            final_answer = result["answer_text"]
            chunks = result["chunks"]
            rate_limit_wait = getattr(self.llm, "last_rate_limit_wait", 0.0)
        else:
            chunks = await asyncio.to_thread(self.hybrid.search, original)
            top_chunks = await asyncio.to_thread(self.reranker.rerank, original, chunks, top_k=settings.reranker_top_k)
            context = [c["text"] for c in top_chunks]
            final_answer = await self.llm.generate(original, context, history=history)
            rate_limit_wait = getattr(self.llm, "last_rate_limit_wait", 0.0)
            chunks = top_chunks

        return {
            "answer_text": final_answer,
            "rate_limit_wait": rate_limit_wait,
            "chunks": [
                {"content": c["text"], "page": c.get("page"), "score": float(c.get("score", 0))}
                for c in chunks
            ],
        }
