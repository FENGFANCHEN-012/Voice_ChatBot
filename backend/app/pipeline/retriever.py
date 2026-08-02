from app.pipeline.embedder import Embedder


class Retriever:
    def __init__(self, vector_store, embedder: Embedder, k: int = 20):
        self.vector_store = vector_store
        self.embedder = embedder
        self.k = k

    def retrieve(self, query_text: str) -> list[dict]:
        query_vector = self.embedder.embed_query(query_text)
        return self.vector_store.search(query_vector, k=self.k)
