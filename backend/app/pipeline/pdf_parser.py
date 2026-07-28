

import fitz

class PdfParser:
    def __init__(self):
        self.doc = None
    
    def parse(self, file_path: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            
            text = page.get_text()
            # Split text into chunks with overlap
            chunks = [
                text[i:i + chunk_size]
                for i in range(0, len(text), chunk_size - overlap)
            ]
            pages.extend([{"page": page.number, "chunk": chunk} for chunk in chunks])
        return pages
