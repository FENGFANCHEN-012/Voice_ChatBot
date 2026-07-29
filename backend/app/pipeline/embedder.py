import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        # loads the BGE-M3 model from HuggingFace (~2.2 GB download on first run)
        self.model = SentenceTransformer(model_name, trust_remote_code=True)

    def embed(self, texts: list[str]) -> list[list[float]]:
        # encodes texts into 1024-dim vectors, normalized for cosine similarity
        embeddings = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()
