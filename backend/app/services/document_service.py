class DocumentService:
    async def upload(self, filename: str, file_bytes: bytes) -> dict:
        pass

    async def delete(self, doc_id: str) -> bool:
        pass

    def list_all(self) -> list[dict]:
        pass
