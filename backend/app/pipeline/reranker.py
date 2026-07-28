class Reranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        pass

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        pass
