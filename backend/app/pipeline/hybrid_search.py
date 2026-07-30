import numpy as np
from rank_bm25 import BM25Okapi


class HybridSearch:
    def __init__(self, vector_store, embedder, k: int = 20, rrf_k: int = 60):
        self.vector_store = vector_store
        self.embedder = embedder
        self.k = k
        self.rrf_k = rrf_k
        self._bm25 = None
        self._bm25_texts = []

    def rebuild(self):
        self._bm25_texts = self.vector_store.get_all_texts()
        if not self._bm25_texts:
            self._bm25 = None
            return
        tokenized = [doc.lower().split() for doc in self._bm25_texts]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query_text: str, where: dict | None = None) -> list[dict]:
        if self._bm25 is None:
            self.rebuild()

        query_vector = self.embedder.embed([query_text])[0]
        vec_results = self.vector_store.search(query_vector, k=self.k, where=where)

        tokenized_query = query_text.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        bm25_ranked = sorted(
            [(i, score) for i, score in enumerate(bm25_scores) if score > 0],
            key=lambda x: x[1], reverse=True
        )[:self.k]

        vec_ranks = {r["text"]: idx for idx, r in enumerate(vec_results)}
        bm25_texts_map = {t: i for i, t in enumerate(self._bm25_texts)}

        fused = {}
        for idx, result in enumerate(vec_results):
            text = result["text"]
            fused[text] = {
                "vec_rank": idx,
                "result": result,
            }

        for idx, (doc_idx, _) in enumerate(bm25_ranked):
            text = self._bm25_texts[doc_idx]
            if text in fused:
                fused[text]["bm25_rank"] = idx
            else:
                fused[text] = {
                    "vec_rank": None,
                    "bm25_rank": idx,
                    "result": {"text": text, "score": 0.0},
                }

        for text, data in fused.items():
            vec_score = 1.0 / (self.rrf_k + data["vec_rank"] + 1) if data["vec_rank"] is not None else 0
            bm25_score = 1.0 / (self.rrf_k + data["bm25_rank"] + 1) if "bm25_rank" in data else 0
            data["rrf_score"] = vec_score + bm25_score

        ranked = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)[:self.k]
        results = []
        for item in ranked:
            r = dict(item["result"])
            r["score"] = float(item["rrf_score"])
            results.append(r)
        return results
