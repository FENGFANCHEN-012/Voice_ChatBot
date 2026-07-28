import os
import uuid
from pathlib import Path


class FileStore:
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> str:
        doc_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        file_path = self.upload_dir / f"{doc_id}{ext}"
        file_path.write_bytes(content)
        return doc_id, str(file_path)

    def delete(self, doc_id: str) -> bool:
        for f in self.upload_dir.iterdir():
            if f.stem == doc_id:
                f.unlink()
                return True
        return False

    def get_path(self, doc_id: str) -> str | None:
        for f in self.upload_dir.iterdir():
            if f.stem == doc_id:
                return str(f)
        return None
