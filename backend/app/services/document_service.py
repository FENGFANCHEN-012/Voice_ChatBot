import threading
from datetime import datetime, timezone
from loguru import logger
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
        self._documents: dict[str, dict] = {}
        self._progress: dict[str, dict] = {}
        self._progress_events: dict[str, list] = {}
        self._load_existing()


    def _load_existing(self):
        for meta in self.file_store.get_all_metadata():
            self._documents[meta["doc_id"]] = meta

    def get_progress(self, doc_id: str) -> dict:
        return self._progress.get(doc_id, {"status": "unknown", "current": 0, "total": 0})

    def get_progress_events(self, doc_id: str) -> list:
        events = self._progress_events.get(doc_id, [])
        self._progress_events[doc_id] = []
        return events

    async def upload(self, filename: str, file_bytes: bytes) -> dict:
        doc_id, file_path = self.file_store.save(filename, file_bytes)

        chunks = self.pdf_parser.parse(file_path, doc_id, strategy="recursive")

        now = datetime.now(timezone.utc).isoformat()
        doc_info = {
            "doc_id": doc_id,
            "filename": filename,
            "file_path": file_path,
            "chunk_count": 0,
            "total_chunks": len(chunks),
            "uploaded_at": now,
        }
        self._documents[doc_id] = doc_info
        self.file_store.save_metadata(doc_id, doc_info)

        self._progress[doc_id] = {"status": "embedding", "current": 0, "total": len(chunks)}
        self._progress_events[doc_id] = []

        thread = threading.Thread(target=self._embed_background, args=(doc_id, chunks, filename), daemon=True)
        thread.start()

        return doc_info

    def _embed_background(self, doc_id: str, chunks: list, filename: str):
        embedded_count = 0
        batch_size = 32
        try:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                texts = [c["text"] for c in batch]
                embeddings = self.embedder.embed(texts)

                meta_list = [
                    {"doc_id": c["doc_id"], "page": c["page"], "chunk_index": c["chunk_index"], "text": c["text"]}
                    for c in batch
                ]

                self.vector_store.add_chunks(embeddings, meta_list)
                embedded_count += len(batch)
                self._progress[doc_id]["current"] = embedded_count
                self._progress_events[doc_id].append({"current": embedded_count, "total": len(chunks)})
                logger.info(f"Embedded {embedded_count}/{len(chunks)} chunks for {filename}")

            self._progress[doc_id]["status"] = "complete"
            self._progress_events[doc_id].append({"status": "complete"})
        except Exception as e:
            logger.error(f"Embedding failed at chunk {embedded_count}/{len(chunks)}: {e}")
            self._progress[doc_id]["status"] = "error"
            self._progress_events[doc_id].append({"status": "error", "message": str(e)})

        self._documents[doc_id]["chunk_count"] = embedded_count
        self.file_store.save_metadata(doc_id, self._documents[doc_id])




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
  
  
  