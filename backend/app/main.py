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
from app.pipeline.retriever import Retriever
from app.pipeline.reranker import Reranker
from app.pipeline.llm import LLMClient
from app.pipeline.orchestrator import PipelineOrchestrator

from app.services.document_service import DocumentService
from app.services.session_service import SessionService
from app.services.chat_service import ChatService
from app.services.audio_service import AudioService


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: loading models and stores...")

    app.state.session_store = SessionStore()
    file_store = FileStore(settings.upload_dir)

    pdf_parser = PdfParser(chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)

    logger.info(f"Loading embedding model: {settings.embedding_model_name}")
    embedder = Embedder(settings.embedding_model_name)

    logger.info(f"Loading vector store: {settings.vector_store_type}")
    vector_store = create_vector_store(settings)

    logger.info(f"Loading reranker model: {settings.reranker_model_name}")
    reranker = Reranker()

    logger.info("Initialising LLM client")
    llm = LLMClient(settings.gemini_api_key)

    retriever = Retriever(vector_store, embedder, k=settings.retrieval_top_k)
    orchestrator = PipelineOrchestrator(retriever, reranker, llm)

    app.state.document_service = DocumentService(file_store, pdf_parser, embedder, vector_store)
    app.state.session_service = SessionService(app.state.session_store)
    app.state.chat_service = ChatService(orchestrator, app.state.session_store)



    logger.info(f"Initialising audio service with whisper model: {settings.whisper_model_size}")
    
    
    app.state.audio_service = AudioService(model_size=settings.whisper_model_size)

    logger.info("Startup complete")
    yield

    logger.info("Shutting down...")
    app.state.document_service = None
    app.state.session_service = None
    app.state.chat_service = None
    app.state.audio_service = None
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
