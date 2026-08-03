import numpy as np
from loguru import logger
from rank_bm25 import BM25Okapi
from app.pipeline.query_normalizer import normalize_query, extract_metadata_hints


class HybridSearch:
    def __init__(self, vector_store, embedder, k: int = 20, rrf_k: int = 60):
        self.vector_store = vector_store
        self.embedder = embedder
        self.k = k
        self.rrf_k = rrf_k
        self._bm25 = None
        self._bm25_texts = []
        self._bm25_metadata = []

    def rebuild(self):
        all_chunks = self.vector_store.get_all_chunks_with_metadata()
        if not all_chunks:
            self._bm25 = None
            self._bm25_texts = []
            self._bm25_metadata = []
            return
        self._bm25_texts = [c["text"] for c in all_chunks]
        self._bm25_metadata = [c.get("metadata", {}) for c in all_chunks]
        tokenized = [doc.lower().split() for doc in self._bm25_texts]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query_text: str, where: dict | None = None) -> list[dict]:
        if self._bm25 is None:
            self.rebuild()

        normalized_query = normalize_query(query_text)
        hints = extract_metadata_hints(normalized_query)

        if hints.get("chapter") and where is None:
            where = {"chapter": hints["chapter"]}
            logger.info(f"[HybridSearch] Metadata filter: chapter={hints['chapter']}")

        query_vector = self.embedder.embed_query(normalized_query)
        vec_results = self.vector_store.search(query_vector, k=self.k, where=where)

        filter_used = where
        if not vec_results and where:
            logger.info(f"[HybridSearch] No results with filter {where}, retrying without filter")
            vec_results = self.vector_store.search(query_vector, k=self.k, where=None)
            filter_used = None

        tokenized_query = normalized_query.lower().split()
        bm25_scores = self._bm25.get_scores(tokenized_query)
        
        bm25_ranked = []
        for i, score in enumerate(bm25_scores):
            if score > 0:
                if filter_used and self._bm25_metadata:
                    meta = self._bm25_metadata[i] if i < len(self._bm25_metadata) else {}
                    if filter_used.get("chapter") and meta.get("chapter") != filter_used["chapter"]:
                        continue
                bm25_ranked.append((i, score))
        
        bm25_ranked = sorted(bm25_ranked, key=lambda x: x[1], reverse=True)[:self.k]

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

        logger.info(f"[HybridSearch] Original: {query_text}")
        logger.info(f"[HybridSearch] Normalized: {normalized_query}")
        if hints:
            logger.info(f"[HybridSearch] Hints: {hints}")
        logger.info(f"[HybridSearch] Retrieved {len(results)} chunks (vec: {len(vec_results)}, bm25: {len(bm25_ranked)})")
        for i, r in enumerate(results[:3]):
            logger.info(f"  #{i+1} score={r['score']:.4f} | {r['text'][:100]}...")

        return results
