import asyncio
import torch
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
        self.use_advanced = settings.use_advanced_pipeline and torch.cuda.is_available()
        logger.info(f"[Pipeline] Advanced retrieval (AgentRAG + QueryExpander): "
                    f"{'ENABLED' if self.use_advanced else 'disabled (no CUDA GPU)'}")

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

        category = None
        if self.use_advanced:
            category, chunks = await self._advanced_retrieve(text)
            if category == self.agent.OUT_OF_SCOPE:
                logger.info("[Pipeline] Query classified out-of-scope; answering without context")
                full_answer = ""
                async for token in self.llm.generate_stream(text, [], history=history):
                    full_answer += token
                    yield {"type": "token", "content": token}
                self.cache.set(text, {"answer_text": full_answer, "chunks": []})
                yield {"type": "done", "chunks": []}
                return
        else:
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
        category = None
        if self.use_advanced:
            category, chunks = await self._advanced_retrieve(original)
            if category == self.agent.OUT_OF_SCOPE:
                logger.info("[Pipeline] Query classified out-of-scope; answering without context")
                answer = await self.llm.generate(original, [], history=history)
                return {
                    "answer_text": answer,
                    "rate_limit_wait": getattr(self.llm, "last_rate_limit_wait", 0.0),
                    "chunks": [],
                }
        else:
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

    async def _advanced_retrieve(self, original: str) -> tuple[str, list[dict]]:
        """Classify the query with AgentRAG, expand it with QueryExpander, then
        run multi-query hybrid search and merge the results. Any failure degrades
        gracefully to plain hybrid search."""
        category = None
        try:
            category = await self.agent.classify(original)
            logger.info(f"[Pipeline] AgentRAG classified query as: {category}")
        except Exception as e:
            logger.warning(f"[Pipeline] AgentRAG classify failed ({e}); using plain hybrid search")

        if category == self.agent.OUT_OF_SCOPE:
            return category, []

        expanded = original
        try:
            expanded = await self.query_expander.expand(original)
            logger.info(f"[Pipeline] QueryExpander: '{original}' -> '{expanded}'")
        except Exception as e:
            logger.warning(f"[Pipeline] QueryExpander failed ({e}); using original query")

        sub_queries = self._build_sub_queries(original, expanded)

        all_results: dict[str, dict] = {}
        for q in sub_queries:
            for r in await asyncio.to_thread(self.hybrid.search, q):
                key = r["text"]
                if key not in all_results or r["score"] > all_results[key]["score"]:
                    all_results[key] = r

        chunks = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
        chunks = chunks[: settings.retrieval_fetch_k]
        logger.info(f"[Pipeline] Advanced retrieval: {len(sub_queries)} sub-queries → {len(chunks)} chunks")
        return category or self.agent.COMPLEX, chunks

    def _build_sub_queries(self, original: str, expanded: str) -> list[str]:
        queries = [original]
        if expanded and expanded != original:
            parts = [p.strip() for p in expanded.split(",") if p.strip()]
            queries.extend(parts[:4])
        seen = set()
        unique = []
        for q in queries:
            if q and q not in seen:
                seen.add(q)
                unique.append(q)
        return unique[:5]

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
