from datetime import datetime, timezone
from app.store.file_store import FileStore
from app.pipeline.pdf_parser import PdfParser
from app.pipeline.embedder import Embedder


from app.pipeline.vector_store import ChromaVectorStore, FaissVectorStore

from app.pipeline.reranker import Reranker

class DocumentService:
    def __init__(
        self,
        file_store: FileStore,
        pdf_parser: PdfParser,
        embedder: Embedder,
        vector_store: ChromaVectorStore | FaissVectorStore,
    ):
        self.file_store = file_store
        self.pdf_parser = pdf_parser
        self.embedder = embedder
        self.vector_store = vector_store
        self._documents: dict[str, dict] = {}  # doc_id -> metadata


    #get pdf from frontend and save it to disk, parse it into chunks, embed the chunks, and store them in FAISS
    async def upload(self, filename: str, file_bytes: bytes) -> dict:
        # 1. save PDF to disk
        doc_id, file_path = self.file_store.save(filename, file_bytes)

        # 2. parse PDF into text chunks
        chunks = self.pdf_parser.parse(file_path, doc_id, strategy="recursive")

        if chunks:
            # 3. embed all chunk texts
            texts = [c["text"] for c in chunks]
            embeddings = self.embedder.embed(texts)

            # 4. build metadata for each chunk
            meta_list = [
                {"doc_id": c["doc_id"], "page": c["page"], "chunk_index": c["chunk_index"], "text": c["text"]}
                for c in chunks
            ]

            # 5. store in FAISS
            self.vector_store.add_chunks(embeddings, meta_list)

        # 6. register document
        now = datetime.now(timezone.utc).isoformat()
        doc_info = {"doc_id": doc_id, "filename": filename, "chunk_count": len(chunks), "uploaded_at": now}
        self._documents[doc_id] = doc_info
        return doc_info




    async def delete(self, doc_id: str) -> bool:
        if doc_id not in self._documents:
            return False
        self.vector_store.delete_document(doc_id)
        self.file_store.delete(doc_id)
        del self._documents[doc_id]
        return True
    
    
    
    async def search(self, query: str, k: int = 20) -> list[dict]:
       
        results = self.vector_store.search(query, k=k)
        rerank_result = Reranker().rerank(query, results, top_k=5)
        return rerank_result
       
    

    def list_all(self) -> list[dict]:
        return list(self._documents.values())
  
  
  