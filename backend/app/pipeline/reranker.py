




import torch
from loguru import logger
from sentence_transformers import CrossEncoder

_device = "cuda" if torch.cuda.is_available() else "cpu"

reranker = CrossEncoder(
    "BAAI/bge-reranker-v2-m3", device=_device
)


class Reranker:
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        pass

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        pairs = [(query, c["text"]) for c in candidates]
       
        scores = reranker.predict(pairs)
       
        for i, c in enumerate(candidates):
            c["score"] = scores[i]

        ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]

        logger.info(f"[Reranker] {len(candidates)} candidates → top {top_k}")
        for i, r in enumerate(ranked):
            logger.info(f"  #{i+1} score={r['score']:.4f} | {r['text'][:100]}...")

        return ranked