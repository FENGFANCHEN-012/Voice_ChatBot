from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    messages: list[Message] = field(default_factory=list)


@dataclass
class Document:
    doc_id: str
    filename: str
    file_path: str
    uploaded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Chunk:
    doc_id: str
    page: int
    chunk_index: int
    text: str
    embedding: list[float] | None = None
