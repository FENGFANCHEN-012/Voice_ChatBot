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
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm
        self.query_expander = query_expander
        self.hybrid = hybrid
        self.fallback = fallback
        self.agent = agent
        self.cache = QueryCache(ttl_seconds=3600, max_size=100)

    async def answer_question(self, text: str, history: list[dict] | None = None) -> dict:
        logger.info(f"[Pipeline] Query: {text}")

        cached = self.cache.get(text)
        if cached:
            logger.info(f"[Pipeline] Cache hit (cache size: {self.cache.size})")
            return cached

        logger.info("[Pipeline] Cache miss")
        category = self.agent.classify(text)
        logger.info(f"[Pipeline] Agent classified as: {category}")

        if category == AgentRAG.OUT_OF_SCOPE:
            logger.info("[Pipeline] Out of scope → direct LLM answer")
            result = self._handle_out_of_scope(text, history)
        elif category == AgentRAG.SIMPLE:
            result = self._simple_path(text, history)
        else:
            result = self._full_path(text, history)

        self.cache.set(text, result)
        return result

    def _handle_out_of_scope(self, text: str, history: list[dict] | None = None) -> dict:
        answer = self.llm.generate(text, [], history=history)
        return {
            "answer_text": answer,
            "chunks": [],
        }

    def _simple_path(self, original: str, history: list[dict] | None = None) -> dict:
        expanded = self.query_expander.expand(original)
        logger.info(f"[Pipeline] Expanded query: {expanded}")
        chunks = self.hybrid.search(expanded)
        top_chunks = self.reranker.rerank(expanded, chunks, top_k=settings.reranker_top_k)
        context = [c["text"] for c in top_chunks]
        answer = self.llm.generate(original, context, history=history)
        return {
            "answer_text": answer,
            "chunks": [
                {"content": c["text"], "page": c.get("page"), "score": float(c.get("score", 0))}
                for c in top_chunks
            ],
        }

    def _full_path(self, original: str, history: list[dict] | None = None) -> dict:
        expanded = self.query_expander.expand(original)
        logger.info(f"[Pipeline] Expanded query: {expanded}")
        result = self.fallback.execute(expanded, history=history)

        if result["passed"]:
            final_answer = result["answer_text"]
            chunks = result["chunks"]
        else:
            chunks = self.hybrid.search(expanded)
            
            
            top_chunks = self.reranker.rerank(expanded, chunks, top_k=settings.reranker_top_k)
            context = [c["text"] for c in top_chunks]
            
            
            final_answer = self.llm.generate(original, context, history=history)
            chunks = top_chunks

        return {
            "answer_text": final_answer,
            "chunks": [
                {"content": c["text"], "page": c.get("page"), "score": float(c.get("score", 0))}
                for c in chunks
            ],
        }
