class Fallback:
    def __init__(self, hybrid_search, embedder, reranker, query_expander, self_rag, llm, top_k: int = 20):
        self.hybrid_search = hybrid_search
        self.embedder = embedder
        self.reranker = reranker
        self.query_expander = query_expander
        self.self_rag = self_rag
        self.llm = llm
        self.top_k = top_k

    def execute(self, original_query: str, history: list[dict] | None = None) -> dict:
        stages = [
            ("hybrid + reranker", self._stage_full),
            ("hybrid only (no reranker)", self._stage_no_rerank),
            ("expanded query + reranker", self._stage_expanded),
        ]

        result = {"answer_text": "", "chunks": [], "passed": False}
        for stage_name, stage_fn in stages:
            result = stage_fn(original_query, history)
            if result["passed"]:
                return result

        return {
            "answer_text": "I couldn't find relevant information in the uploaded documents. Try rephrasing your question or uploading more relevant documents.",
            "chunks": result.get("chunks", []),
            "passed": False,
        }

    def _stage_full(self, query: str, history: list[dict] | None = None) -> dict:
        chunks = self.hybrid_search.search(query, k=self.top_k)
        if not chunks:
            return {"answer_text": "", "chunks": [], "passed": False}
        reranked = self.reranker.rerank(query, chunks, top_k=5)
        relevant, passed = self.self_rag.verify_relevance(query, reranked)
        answer = ""
        if passed and relevant:
            context = [c["text"] for c in relevant]
            answer = self.llm.generate(query, context, history=history)
            answer = self.self_rag.verify_answer(query, answer, context)
        return {"answer_text": answer, "chunks": relevant, "passed": passed}

    def _stage_no_rerank(self, query: str, history: list[dict] | None = None) -> dict:
        chunks = self.hybrid_search.search(query, k=self.top_k)
        if not chunks:
            return {"answer_text": "", "chunks": [], "passed": False}
        relevant, passed = self.self_rag.verify_relevance(query, chunks)
        answer = ""
        if passed and relevant:
            context = [c["text"] for c in relevant]
            answer = self.llm.generate(query, context, history=history)
        return {"answer_text": answer, "chunks": relevant, "passed": passed}

    def _stage_expanded(self, query: str, history: list[dict] | None = None) -> dict:
        expanded = self.query_expander.expand(query)
        return self._stage_full(expanded, history=history)
