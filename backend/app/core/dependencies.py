from fastapi import Request, HTTPException, Depends
from app.store.session_store import SessionStore
from app.pipeline.orchestrator import PipelineOrchestrator


def get_session_store() -> SessionStore:
    raise NotImplementedError("Inject via app.state.session_store")


def get_orchestrator() -> PipelineOrchestrator:
    raise NotImplementedError("Inject via app.state.orchestrator")


async def get_current_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
):
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
