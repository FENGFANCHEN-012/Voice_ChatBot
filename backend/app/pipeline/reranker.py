




import asyncio
import torch
from loguru import logger
from sentence_transformers import CrossEncoder
from app.config import settings

_device = "cuda" if torch.cuda.is_available() else "cpu"

_reranker_model = None

def get_reranker_model():
    global _reranker_model
    if _reranker_model is None:
        model_name = getattr(settings, "reranker_model_name", "BAAI/bge-reranker-v2-m3")
        logger.info(f"[Reranker] Initializing CrossEncoder model: {model_name} on {_device}")
        _reranker_model = CrossEncoder(model_name, device=_device)
    return _reranker_model


class Reranker:
    def __init__(self, model_name: str | None = None):
        pass

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not candidates:
            return []

        model = get_reranker_model()
        pairs = [(query, c["text"]) for c in candidates]
        scores = model.predict(pairs)

        for i, c in enumerate(candidates):
            c["score"] = float(scores[i])

        ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]

        logger.info(f"[Reranker] {len(candidates)} candidates → top {top_k}")
        for i, r in enumerate(ranked):
            logger.info(f"  #{i+1} score={r['score']:.4f} | {r['text'][:100]}...")

        return ranked