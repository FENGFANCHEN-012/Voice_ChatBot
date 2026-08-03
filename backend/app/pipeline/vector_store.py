"""
Vector store backends — ChromaDB or FAISS.

Switch between them by setting VECTOR_STORE_TYPE=chroma or VECTOR_STORE_TYPE=faiss in .env.
Both implement the same interface: add_chunks, search, delete_document, save, load.
"""

from uuid import uuid4
import numpy as np


# ── ChromaDB backend ──────────────────────────────────────────────────────────

class ChromaVectorStore:
    def __init__(self, persist_dir: str, collection_name: str = "documents"):
        import chromadb
        from chromadb.config import Settings
        self.client = chromadb.PersistentClient(
            path=persist_dir, settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"},
        )


    def add_chunks(self, embeddings, metadata):
        
        # create unique IDs for each chunk and prepare documents and metadatas for ChromaDB
        ids = [str(uuid4()) for _ in embeddings]
        
        documents = [m["text"] for m in metadata]
        metadatas = [{k: v for k, v in m.items() if k != "text" and v is not None} for m in metadata]
        
        
        # store the embeddings, metadata, and documents in ChromaDB
        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
      
        return ids


    def get_all_texts(self) -> list[str]:
        results = self.collection.get(include=["documents"])
        return results.get("documents", [])

    def get_all_chunks_with_metadata(self) -> list[dict]:
        results = self.collection.get(include=["documents", "metadatas"])
        chunks = []
        for i, doc in enumerate(results.get("documents", [])):
            meta = results.get("metadatas", [{}])[i] if i < len(results.get("metadatas", [])) else {}
            chunks.append({"text": doc, "metadata": meta})
        return chunks

    def search(self, query_vector, k=20, where: dict | None = None):
        kwargs = {"query_embeddings": [query_vector], "n_results": k}
        if where:
            kwargs["where"] = where
        results = self.collection.query(**kwargs)
        output = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i] or {}
            meta["text"] = results["documents"][0][i]
            meta["score"] = results["distances"][0][i]
            output.append(meta)
        return output

    def delete_document(self, doc_id):
        self.collection.delete(where={"doc_id": doc_id})

    def save(self):
        pass

    def load(self):
        pass


# ── FAISS backend ─────────────────────────────────────────────────────────────

class FaissVectorStore:
    def __init__(self, index_path: str, metadata_path: str, dimension: int = 1024):
        import faiss, pickle
        from pathlib import Path
        self.index_path = Path(index_path)
        self.metadata_path = Path(metadata_path)
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: dict[str, dict] = {}
        self.next_id = 0
        self.load()

    def add_chunks(self, embeddings, metadata):
        
        import faiss
        vectors = np.array(embeddings).astype(np.float32)
        ids = list(range(self.next_id, self.next_id + len(vectors)))
        self.index.add(vectors)
        
        for i, m in zip(ids, metadata):
            self.metadata[str(i)] = m
        self.next_id += len(vectors)
        self.save()
        return [str(i) for i in ids]


    def get_all_texts(self) -> list[str]:
        return [m.get("text", "") for m in self.metadata.values()]

    def get_all_chunks_with_metadata(self) -> list[dict]:
        return [{"text": m.get("text", ""), "metadata": m} for m in self.metadata.values()]

    def search(self, query_vector, k=20):
        import faiss
        vector = np.array([query_vector]).astype(np.float32)
        distances, indices = self.index.search(vector, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = dict(self.metadata.get(str(idx), {}))
            meta["score"] = float(dist)
            results.append(meta)
        return results
    

    def delete_document(self, doc_id):
        keep_ids = []
        keep_vectors = []
        for str_id, meta in list(self.metadata.items()):
            if meta.get("doc_id") != doc_id:
                keep_ids.append(int(str_id))
                keep_vectors.append(self.index.reconstruct(int(str_id)))
            else:
                del self.metadata[str_id]
        import faiss, numpy as np
        if keep_vectors:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(np.array(keep_vectors).astype(np.float32))
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
        self.next_id = max(keep_ids, default=-1) + 1
        self.save()

    def save(self):
        import faiss, pickle
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "wb") as f:
            pickle.dump({"metadata": self.metadata, "next_id": self.next_id}, f)

    def load(self):
        import faiss, pickle
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
        if self.metadata_path.exists():
            with open(self.metadata_path, "rb") as f:
                data = pickle.load(f)
                self.metadata = data.get("metadata", {})
                self.next_id = data.get("next_id", 0)


# ── Factory ───────────────────────────────────────────────────────────────────

def create_vector_store(settings) -> ChromaVectorStore | FaissVectorStore:
    """
    Returns a vector store instance based on settings.vector_store_type.

    Set VECTOR_STORE_TYPE=chroma or VECTOR_STORE_TYPE=faiss in .env.
    """
    if settings.vector_store_type == "faiss":
        return FaissVectorStore(settings.faiss_index_path, settings.faiss_metadata_path)
    return ChromaVectorStore(settings.chroma_db_path)
