from datetime import datetime, timezone
from app.pipeline.orchestrator import PipelineOrchestrator
from app.store.session_store import SessionStore
from app.models.domain import Message


class ChatService:
    def __init__(self, orchestrator: PipelineOrchestrator, session_store: SessionStore):
        self.orchestrator = orchestrator
        self.session_store = session_store

    async def query(self, session_id: str, text: str) -> dict:
        session = self.session_store.get(session_id)
        if session is None:
            return {"error": "Session not found"}

        session.messages.append(Message(role="user", content=text))

        history = [
            {"role": m.role, "content": m.content}
            for m in session.messages[:-1]
        ]
        result = await self.orchestrator.answer_question(text, history=history)

        session.messages.append(Message(role="assistant", content=result["answer_text"]))

        return {
            "answer_text": result["answer_text"],
            "audio_url": "",
            "chunks": result["chunks"],
        }

    def get_messages(self, session_id: str) -> list[dict]:
        session = self.session_store.get(session_id)
        if session is None:
            return []
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in session.messages
        ]
