from app.config import settings
from app.pipeline.retriever import Retriever
from app.pipeline.reranker import Reranker
from app.pipeline.llm import LLMClient
from app.pipeline.query_expander import QueryExpander
from app.pipeline.hybrid_search import HybridSearch
from app.pipeline.self_rag import SelfRAG
from app.pipeline.fallback import Fallback
from app.pipeline.agent_rag import AgentRAG


# central orchestrator that manages the entire pipeline
class PipelineOrchestrator:
    def __init__(
        self,
        retriever: Retriever,
        reranker: Reranker,
        llm: LLMClient,
        query_expander: QueryExpander,
        hybrid: HybridSearch,
        self_rag: SelfRAG,
        fallback: Fallback,
        agent: AgentRAG,
    ):
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm
        self.query_expander = query_expander
        self.hybrid = hybrid
        self.self_rag = self_rag
        self.fallback = fallback
        self.agent = agent

    async def answer_question(self, text: str, history: list[dict] | None = None) -> dict:
        category = self.agent.classify(text)

        if category == AgentRAG.OUT_OF_SCOPE:
            return self._handle_out_of_scope(text, history)

        expanded = self.query_expander.expand(text)

        if category == AgentRAG.SIMPLE:
            return self._simple_path(expanded, text, history)

        return self._full_path(expanded, text, history)

    def _handle_out_of_scope(self, text: str, history: list[dict] | None = None) -> dict:
        answer = self.llm.generate(text, [], history=history)
        return {
            "answer_text": answer,
            "chunks": [],
        }

    def _simple_path(self, expanded: str, original: str, history: list[dict] | None = None) -> dict:
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

    def _full_path(self, expanded: str, original: str, history: list[dict] | None = None) -> dict:
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
