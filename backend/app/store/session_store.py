from app.models.domain import Session


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def set(self, session_id: str, session: Session) -> None:
        self._sessions[session_id] = session

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def rename(self, session_id: str, title: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.title = title
        return session

    def list_all(self) -> list[Session]:
        return list(self._sessions.values())
