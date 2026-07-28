class VectorStore:
    def __init__(self, index_path: str, metadata_path: str):
        pass

    def add_chunks(self, embeddings: list[list[float]], metadata: list[dict]) -> list[str]:
        pass

    def search(self, query_vector: list[float], k: int = 20) -> list[dict]:
        pass

    def delete_document(self, doc_id: str) -> None:
        pass

    def save(self) -> None:
        pass

    def load(self) -> None:
        pass
