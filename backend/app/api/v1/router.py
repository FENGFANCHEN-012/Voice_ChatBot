from fastapi import APIRouter
from app.api.v1 import health, documents, chats, audio, sessions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chats.router, prefix="/chats", tags=["chats"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
