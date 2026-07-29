


from sentence_transformers import CrossEncoder

reranker = CrossEncoder(
    "BAAI/bge-reranker-v2-m3"
)


class Reranker:
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        pass

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        pairs = [(query, c["text"]) for c in candidates]
       
        scores = reranker.predict(pairs)
       
        for i, c in enumerate(candidates):
            c["score"] = scores[i]
            
        return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]