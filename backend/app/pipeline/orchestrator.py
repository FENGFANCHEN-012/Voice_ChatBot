class PipelineOrchestrator:
    async def process_document(self, file_path: str, doc_id: str) -> int:
        pass

    async def answer_question(
        self, session_id: str, audio_bytes: bytes | None = None, text: str | None = None
    ) -> dict:
        pass
