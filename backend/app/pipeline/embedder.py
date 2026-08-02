import torch
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, trust_remote_code=True, device=self.device)

    def embed(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, normalize_embeddings=True, show_progress_bar=False, device=self.device)
            all_embeddings.extend(batch_embeddings.tolist())
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], normalize_embeddings=True, show_progress_bar=False, device=self.device)[0].tolist()
