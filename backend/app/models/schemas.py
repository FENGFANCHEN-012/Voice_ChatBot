from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HealthResponse(BaseModel):
    status: str


class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    title: str = ""


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    file_path: str = ""
    chunk_count: int
    total_chunks: int = 0
    uploaded_at: datetime


class QueryRequest(BaseModel):
    session_id: str
    text: Optional[str] = None


class ChunkInfo(BaseModel):
    content: str
    page: Optional[int] = None
    score: float


class QueryResponse(BaseModel):
    answer_text: str
    audio_url: str = ""
    chunks: list[ChunkInfo]
    processing_time: Optional[float] = None


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration: float


class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    detail: str
