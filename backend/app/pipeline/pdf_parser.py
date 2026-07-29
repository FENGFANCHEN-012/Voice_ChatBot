import fitz  # PyMuPDF — reads PDF files
import numpy as np  # numerical ops for cosine similarity
from typing import Callable  # type hint for the embedding function parameter
from langchain.text_splitter import RecursiveCharacterTextSplitter  # splits text by paragraphs/sentences/words


class PdfParser:
    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        # chunk_size = target number of characters per chunk
        # overlap = characters shared between adjacent chunks (preserves context at boundaries)
        self.chunk_size = chunk_size
        self.overlap = overlap

    def parse(
        self,
        file_path: str,        # path to the PDF file on disk
        doc_id: str,           # unique ID assigned to this document (used later in FAISS metadata)
        strategy: str = "recursive",  # "recursive" or "semantic"
        embedding_fn: Callable | None = None,  # function that embeds text (only needed for semantic)
) -> list[dict]:           # returns list of chunk dicts
       
       
        pages = self._extract_pages(file_path)  # step 1: get (page_num, text) tuples
      
        if strategy == "semantic":
            if embedding_fn is None:  # semantic needs embeddings to find topic boundaries
              
                raise ValueError("embedding_fn is required for semantic chunking")
            return self._chunk_semantic(pages, doc_id, embedding_fn)
        return self._chunk_recursive(pages, doc_id)  # default: recursive strategy

    def _extract_pages(self, file_path: str) -> list[tuple[int, str]]:
        # opens a PDF and returns list of (page_number, page_text)
        doc = fitz.open(file_path)    # open the PDF file
        pages = []
        for page in doc:              # iterate over every page object
            text = page.get_text().strip()  # extract all text from the page, remove leading/trailing whitespace
            if text:                  # skip completely blank pages
                pages.append((page.number + 1, text))  # page.number is 0-based, we store 1-based
        doc.close()                   # free the file handle
        return pages

    def _chunk_recursive(
        self, pages: list[tuple[int, str]], doc_id: str
    ) -> list[dict]:
        # splits text by natural boundaries: paragraphs → lines → sentences → words → characters
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,      # max chars per chunk
            chunk_overlap=self.overlap,       # overlap between adjacent chunks
            separators=["\n\n", "\n", ".", "?", "!", " ", ""],  # priority order: double newline first, single char last
            length_function=len,              # how to measure chunk size (character count)
        )
        chunks = []
        idx = 0                               # global chunk index across all pages
        for page_num, text in pages:          # process each page separately so we know which page each chunk came from
            for chunk_text in splitter.split_text(text):  # split this page's text into chunks
                chunks.append({
                    "doc_id": doc_id,          # which document this belongs to
                    "page": page_num,          # which page (for citation / source tracking)
                    "chunk_index": idx,        # position in the full document chunk sequence
                    "text": chunk_text,        # the actual text content
                })
                idx += 1
        return chunks

    def _chunk_semantic(
        self,
        pages: list[tuple[int, str]],
        doc_id: str,
        embedding_fn: Callable,
    ) -> list[dict]:
        # splits text where the topic changes (detected by embedding similarity drop)
        sentences, sent_pages = self._split_into_sentences(pages)
       
        if len(sentences) <= 1:  # nothing to split
            return [self._make_chunk(doc_id, sent_pages[0] if sent_pages else 0, 0, " ".join(sentences))]

        group_size = max(3, self.chunk_size // 150)  # ~3-4 sentences per group (150 chars avg per sentence)
        groups, group_pages = self._group_sentences(sentences, sent_pages, group_size)
        
        
        # embed every group using BGE-M3 to get a vector representation of each group's topic
        embeddings = np.array(embedding_fn(groups))  # shape: (num_groups, embedding_dim)

        # compute cosine similarity between each adjacent pair of groups
        similarities = []
        for i in range(len(groups) - 1):
            dot = np.dot(embeddings[i], embeddings[i + 1])  # dot product of two vectors
            norm = np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])  # product of magnitudes
            similarities.append(dot / norm if norm > 0 else 1.0)  # cosine similarity: 1 = same topic, 0 = unrelated

       
        # adaptive threshold: groups must be significantly less similar than average to trigger a break
        threshold = max(np.mean(similarities) - 0.5 * np.std(similarities), 0.3)

        # merge groups into chunks: adjacent groups stay together until similarity drops below threshold
        merge_ranges = []
        start = 0
        for i, sim in enumerate(similarities):
            if sim < threshold:           # topic shift detected here
                merge_ranges.append((start, i + 1))  # close this chunk (groups start..i+1)
                start = i + 1             # start a new chunk
        merge_ranges.append((start, len(groups)))  # final chunk

        chunks = []
        for idx, (s, e) in enumerate(merge_ranges):
            chunk_text = " ".join(groups[s:e])  # join all groups in this chunk
            page_num = group_pages[s]            # use the page number of the first group
            chunks.append(self._make_chunk(doc_id, page_num, idx, chunk_text))
        return chunks

    def _split_into_sentences(
        self, pages: list[tuple[int, str]]
    ) -> tuple[list[str], list[int]]:
        # takes list of (page_num, text) and returns (sentences[], page_of_each_sentence[])
        sentences = []
        sent_pages = []
        for page_num, text in pages:
            # replace newlines with space (they break sentence detection), then split on ". "
            raw = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
            for s in raw:
                sentences.append(s + ("." if not s.endswith(".") else ""))
                sent_pages.append(page_num)  # remember which page this sentence came from
        return sentences, sent_pages

    def _group_sentences(
        self, sentences: list[str], sent_pages: list[int], group_size: int
    ) -> tuple[list[str], list[int]]:
        # batches every N sentences into one group (reduces embedding calls + smooths noise)
        groups = []
        group_pages = []
        for i in range(0, len(sentences), group_size):
            groups.append(" ".join(sentences[i : i + group_size]))
            group_pages.append(sent_pages[i])  # first sentence's page represents the whole group
        return groups, group_pages

    def _make_chunk(self, doc_id: str, page: int, idx: int, text: str) -> dict:
        # simple helper to avoid repeating the dict shape in multiple places
        return {
            "doc_id": doc_id,
            "page": page,
            "chunk_index": idx,
            "text": text,
        }
