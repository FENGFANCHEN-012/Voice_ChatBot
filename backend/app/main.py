from contextlib import asynccontextmanager
from loguru import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.store.session_store import SessionStore
from app.store.file_store import FileStore

from app.pipeline.pdf_parser import PdfParser
from app.pipeline.embedder import Embedder
from app.pipeline.vector_store import create_vector_store

from app.services.document_service import DocumentService


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: loading models and stores...")

    # data stores
    app.state.session_store = SessionStore()
    file_store = FileStore(settings.upload_dir)

    # pipeline components
    pdf_parser = PdfParser(chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)

    logger.info(f"Loading embedding model: {settings.embedding_model_name}")
    
    embedder = Embedder(settings.embedding_model_name)

    logger.info(f"Loading vector store: {settings.vector_store_type}")
    vector_store = create_vector_store(settings)

    # services
    app.state.document_service = DocumentService(file_store, pdf_parser, embedder, vector_store)

    logger.info("Startup complete")
    yield

    logger.info("Shutting down...")
    app.state.document_service = None
    app.state.session_store = None


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
