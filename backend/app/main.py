from contextlib import asynccontextmanager


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.config import settings
from app.api.v1.router import api_router
from app.store.session_store import SessionStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.session_store = SessionStore()
    app.state.orchestrator = None
    yield
    app.state.session_store = None
    app.state.orchestrator = None


app = FastAPI(
    title="Voice RAG Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
