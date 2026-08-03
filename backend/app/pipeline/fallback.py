from loguru import logger



# only will triggered when first retrieval stage fails, then will use agent RAG to classify the query type and decide next step
class Fallback:
    def __init__(self, hybrid_search, embedder, reranker, query_expander, llm, agent_rag=None, hyde=None, top_k: int = 20):
        self.hybrid_search = hybrid_search
        self.embedder = embedder
        self.reranker = reranker
        self.query_expander = query_expander
        self.llm = llm
        self.agent_rag = agent_rag
        self.hyde = hyde
        self.top_k = top_k

    async def execute(self, original_query: str, history: list[dict] | None = None) -> dict:
        stages = [
            ("hybrid + reranker", self._stage_full),
            ("expanded query + reranker", self._stage_expanded),
            # can add more stages here if needed, e.g., HyDE fallback
        ]

        if self.hyde:
            stages.append(("HyDE fallback", self._stage_hyde))

        result = {"answer_text": "", "chunks": [], "passed": False}
        for stage_name, stage_fn in stages:
            logger.info(f"[Fallback] Trying stage: {stage_name}")
            result = await stage_fn(original_query, history)
            if result["passed"]:
                logger.info(f"[Fallback] Passed at: {stage_name}")
                return result
            logger.info(f"[Fallback] Failed at: {stage_name}, trying next...")

        logger.warning("[Fallback] All stages failed")
        return {
            "answer_text": "I couldn't find relevant information in the uploaded documents. Try rephrasing your question or uploading more relevant documents.",
            "chunks": result.get("chunks", []),
            "passed": False,
        }

    async def _stage_full(self, query: str, history: list[dict] | None = None) -> dict:
        chunks = self.hybrid_search.search(query)
        if not chunks:
            return {"answer_text": "", "chunks": [], "passed": False}
        reranked = self.reranker.rerank(query, chunks, top_k=5)
        if not reranked:
            return {"answer_text": "", "chunks": [], "passed": False}
        context = [c["text"] for c in reranked]
        answer = await self.llm.generate(query, context, history=history)
        return {"answer_text": answer, "chunks": reranked, "passed": True}

    async def _stage_expanded(self, query: str, history: list[dict] | None = None) -> dict:
        if self.agent_rag:
            category = await self.agent_rag.classify(query)
            logger.info(f"[Fallback] Agent classified as: {category}")
            if category == "out_of_scope":
                return {"answer_text": "", "chunks": [], "passed": False}
        expanded = await self.query_expander.expand(query)
        logger.info(f"[Fallback] Expanded query: {expanded}")
        return await self._stage_full(expanded, history=history)

    async def _stage_hyde(self, query: str, history: list[dict] | None = None) -> dict:
        reranked = await self.hyde.search(query)
        if not reranked:
            return {"answer_text": "", "chunks": [], "passed": False}
        context = [c["text"] for c in reranked]
        answer = await self.llm.generate(query, context, history=history)
        return {"answer_text": answer, "chunks": reranked, "passed": True}
