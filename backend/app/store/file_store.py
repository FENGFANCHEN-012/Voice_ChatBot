import os
import json
import uuid
from pathlib import Path


class FileStore:
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.upload_dir / "documents.json"
        self._metadata: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.meta_path.exists():
            self._metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))

    def _save(self):
        self.meta_path.write_text(json.dumps(self._metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    def save(self, filename: str, content: bytes, doc_id: str | None = None) -> str:
        from datetime import datetime, timezone
        doc_id = doc_id or str(uuid.uuid4())
        ext = Path(filename).suffix or ".pdf"
        date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_name = Path(filename).stem.replace(" ", "_")[:50]
        file_path = self.upload_dir / f"{date_prefix}_{safe_name}{ext}"
        file_path.write_bytes(content)
        return doc_id, str(file_path)

    def save_metadata(self, doc_id: str, metadata: dict):
        self._metadata[doc_id] = metadata
        self._save()

    def get_metadata(self, doc_id: str) -> dict | None:
        return self._metadata.get(doc_id)

    def get_all_metadata(self) -> list[dict]:
        return list(self._metadata.values())

    def delete(self, doc_id: str) -> bool:
        if doc_id in self._metadata:
            file_path = self._metadata[doc_id].get("file_path")
            if file_path and Path(file_path).exists():
                Path(file_path).unlink()
            del self._metadata[doc_id]
            self._save()
            return True
        return False

    def get_path(self, doc_id: str) -> str | None:
        if doc_id in self._metadata:
            file_path = self._metadata[doc_id].get("file_path")
            if file_path and Path(file_path).exists():
                return file_path
        return None
