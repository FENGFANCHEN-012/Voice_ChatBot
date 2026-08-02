from loguru import logger


class Fallback:
    def __init__(self, hybrid_search, embedder, reranker, query_expander, llm, top_k: int = 20):
        self.hybrid_search = hybrid_search
        self.embedder = embedder
        self.reranker = reranker
        self.query_expander = query_expander
        self.llm = llm
        self.top_k = top_k

    def execute(self, original_query: str, history: list[dict] | None = None) -> dict:
        stages = [
            ("hybrid + reranker", self._stage_full),
            ("expanded query + reranker", self._stage_expanded),
        ]

        result = {"answer_text": "", "chunks": [], "passed": False}
        for stage_name, stage_fn in stages:
            logger.info(f"[Fallback] Trying stage: {stage_name}")
            result = stage_fn(original_query, history)
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

    def _stage_full(self, query: str, history: list[dict] | None = None) -> dict:
        chunks = self.hybrid_search.search(query)
        if not chunks:
            return {"answer_text": "", "chunks": [], "passed": False}
        reranked = self.reranker.rerank(query, chunks, top_k=5)
        if not reranked:
            return {"answer_text": "", "chunks": [], "passed": False}
        context = [c["text"] for c in reranked]
        answer = self.llm.generate(query, context, history=history)
        return {"answer_text": answer, "chunks": reranked, "passed": True}

    def _stage_expanded(self, query: str, history: list[dict] | None = None) -> dict:
        expanded = self.query_expander.expand(query)
        return self._stage_full(expanded, history=history)
