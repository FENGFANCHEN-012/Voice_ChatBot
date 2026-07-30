from datetime import datetime, timezone


class SessionService:
    def __init__(self, session_store):
        self._store = session_store

    def create(self) -> dict:
        session = self._store.create()
        return {"session_id": session.session_id, "created_at": session.created_at}

    def get(self, session_id: str) -> dict | None:
        session = self._store.get(session_id)
        if session is None:
            return None
        return {"session_id": session.session_id, "created_at": session.created_at}

    def delete(self, session_id: str) -> bool:
        return self._store.delete(session_id)

    def list_all(self) -> list[dict]:
        return [
            {"session_id": s.session_id, "created_at": s.created_at}
            for s in self._store.list_all()
        ]
