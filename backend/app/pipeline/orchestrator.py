from app.config import settings
from app.pipeline.retriever import Retriever
from app.pipeline.reranker import Reranker
from app.pipeline.llm import LLMClient


class PipelineOrchestrator:
    def __init__(self, retriever: Retriever, reranker: Reranker, llm: LLMClient):
        self.retriever = retriever
        self.reranker = reranker
        self.llm = llm



    async def answer_question(self, text: str, history: list[dict] | None = None) -> dict:
        chunks = self.retriever.retrieve(text)
        top_chunks = self.reranker.rerank(text, chunks, top_k=settings.reranker_top_k)
        context = [c["text"] for c in top_chunks]
        answer = self.llm.generate(text, context, history=history)
        return {
            "answer_text": answer,
            "chunks": [
                {"content": c["text"], "page": c["page"], "score": float(c.get("score", 0))}
                for c in top_chunks
            ],
        }
