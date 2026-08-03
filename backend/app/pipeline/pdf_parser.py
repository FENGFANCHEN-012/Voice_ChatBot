import re
import json
import fitz
from pathlib import Path
from typing import Callable
from langchain_text_splitters import RecursiveCharacterTextSplitter
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import Document as LlamaDocument
from llama_index.core.embeddings import BaseEmbedding


CHAPTER_PATTERN = re.compile(
    r'(?:^|\n)\s*Chapter\s+(\d+)\s*[:\-\s]*(.*?)(?:\n|$)',
    re.IGNORECASE
)

KEYWORDS_FILE = Path(__file__).parent / "chapter_keywords.json"


def _load_chapter_keywords() -> dict[str, list[str]]:
    if KEYWORDS_FILE.exists():
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def detect_chapter(text: str) -> str | None:
    match = CHAPTER_PATTERN.search(text)
    if match:
        num = match.group(1)
        title = match.group(2).strip()
        return f"Chapter {num}: {title}" if title else f"Chapter {num}"
    return None


def extract_chapters(full_text: str) -> dict[int, str]:
    chapters = {}
    for match in CHAPTER_PATTERN.finditer(full_text):
        num = int(match.group(1))
        title = match.group(2).strip()
        chapters[num] = f"Chapter {num}: {title}" if title else f"Chapter {num}"
    return chapters


class EmbeddingAdapter(BaseEmbedding):
    def __init__(self, embed_fn: Callable):
        super().__init__()
        self._embed_fn = embed_fn

    def _embed(self, text: str) -> list[float]:
        return self._embed_fn([text])[0]

    async def _aget_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    async def _aget_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._embed_fn(texts)

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._embed_fn(texts)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _ahandle_openai_key_error(self, *args, **kwargs):
        raise ValueError("No API key found")

    def _infer_api_key(self):
        return None


CHAPTER_KEYWORDS: dict[str, list[str]] = {}


def _ensure_keywords_loaded() -> dict[str, list[str]]:
    global CHAPTER_KEYWORDS
    if not CHAPTER_KEYWORDS:
        CHAPTER_KEYWORDS = _load_chapter_keywords()
    return CHAPTER_KEYWORDS


class PdfParser:
    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def parse(
        self,
        file_path: str,
        doc_id: str,
        strategy: str = "recursive",
        embedding_fn: Callable | None = None,
    ) -> list[dict]:
        pages = self._extract_pages(file_path)
        full_text = "\n".join(text for _, text in pages)
        chapters = extract_chapters(full_text)
        
        if strategy == "semantic":
            if embedding_fn is None:
                raise ValueError("embedding_fn is required for semantic chunking")
            return self._chunk_semantic(pages, doc_id, embedding_fn, chapters)
        return self._chunk_recursive(pages, doc_id, chapters)

    def _extract_pages(self, file_path: str) -> list[tuple[int, str]]:
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages.append((page.number + 1, text))
        doc.close()
        return pages

    def _assign_chapter(self, text: str, chapters: dict[int, str]) -> str | None:
        for chapter_name in chapters.values():
            if chapter_name in text:
                return chapter_name
        
        keywords = _ensure_keywords_loaded()
        text_lower = text.lower()
        best_chapter = None
        best_score = 0
        
        for chapter_name, kws in keywords.items():
            score = sum(1 for kw in kws if kw in text_lower)
            if score > best_score:
                best_score = score
                best_chapter = chapter_name
        
        return best_chapter if best_score >= 2 else None

    def _chunk_recursive(
        self, pages: list[tuple[int, str]], doc_id: str, chapters: dict[int, str]
    ) -> list[dict]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.overlap,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""],
            length_function=len,
        )
        
        chunks = []
        idx = 0
        for page_num, text in pages:
            for chunk_text in splitter.split_text(text):
                chapter = self._assign_chapter(chunk_text, chapters)
                chunks.append({
                    "doc_id": doc_id,
                    "page": page_num,
                    "chunk_index": idx,
                    "text": chunk_text,
                    "chapter": chapter,
                })
                idx += 1
        return chunks

    def _chunk_semantic(
        self,
        pages: list[tuple[int, str]],
        doc_id: str,
        embedding_fn: Callable,
        chapters: dict[int, str],
    ) -> list[dict]:
        adapter = EmbeddingAdapter(embed_fn=embedding_fn)
        splitter = SemanticSplitterNodeParser(
            embed_model=adapter,
            breakpoint_percentile_threshold=75,
            buffer_size=1,
        )

        llama_docs = []
        for page_num, text in pages:
            doc = LlamaDocument(text=text, metadata={"page": page_num})
            llama_docs.append(doc)

        nodes = splitter.get_nodes_from_documents(llama_docs)

        chunks = []
        for idx, node in enumerate(nodes):
            page_num = node.metadata.get("page", 1)
            chapter = self._assign_chapter(node.text, chapters)
            chunks.append(self._make_chunk(doc_id, page_num, idx, node.text, chapter))
        return chunks

    def _make_chunk(self, doc_id: str, page: int, idx: int, text: str, chapter: str | None = None) -> dict:
        return {
            "doc_id": doc_id,
            "page": page,
            "chunk_index": idx,
            "text": text,
            "chapter": chapter,
        }
