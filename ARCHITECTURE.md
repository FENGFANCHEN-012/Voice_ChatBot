# Voice RAG Assistant — Architecture Document

**Author:** Senior AI Solution Architect  
**Date:** July 2026  
**Status:** Architecture Proposal v1.0

---

## Table of Contents

1. [Overall System Architecture](#1-overall-system-architecture)
2. [Frontend Architecture](#2-frontend-architecture)
3. [Backend Architecture](#3-backend-architecture)
4. [AI Pipeline](#4-ai-pipeline)
5. [API Design](#5-api-design)
6. [Database & Storage Design](#6-database--storage-design)
7. [Testing Architecture](#7-testing-architecture)
8. [Deployment Architecture](#8-deployment-architecture)
9. [Architecture Decisions](#9-architecture-decisions)

---

## 1. Overall System Architecture

### 1.1 High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  React SPA (Vite + Tailwind)                         │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │   │
│  │  │ Upload   │  │ Record    │  │ Audio Playback   │  │   │
│  │  │ Dropzone │  │ Button    │  │ <audio> element  │  │   │
│  │  └────┬─────┘  └─────┬─────┘  └────────┬─────────┘  │   │
│  │       │              │                  │            │   │
│  │  ┌────▼──────────────▼──────────────────▼─────────┐  │   │
│  │  │              Axios HTTP Client                  │  │   │
│  │  └──────────────────────┬─────────────────────────┘  │   │
│  └─────────────────────────┼────────────────────────────┘   │
└────────────────────────────┼────────────────────────────────┘
                             │ HTTP/REST (JSON + multipart + audio/wav)
                             │
┌────────────────────────────┼────────────────────────────────┐
│                    FastAPI Server                            │
│  ┌─────────────────────────┴─────────────────────────┐      │
│  │                   Routers                          │      │
│  │  ┌──────────┐ ┌──────────┐ ┌───────┐ ┌────────┐  │      │
│  │  │ Documents│ │ Chats    │ │ Audio │ │ Health │  │      │
│  │  └────┬─────┘ └────┬─────┘ └───┬───┘ └────────┘  │      │
│  └───────┼─────────────┼───────────┼──────────────────┘      │
│          │             │           │                         │
│  ┌───────▼─────────────▼───────────▼──────────────────┐      │
│  │                  Services Layer                     │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐  │      │
│  │  │ Document │ │ Chat     │ │ Audio    │ │Session│  │      │
│  │  │ Service  │ │ Service  │ │ Service  │ │Service│  │      │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬───┘  │      │
│  └───────┼─────────────┼────────────┼────────────┘      │      │
│          │             │            │                    │      │
│  ┌───────▼─────────────▼────────────▼────────────────┐   │      │
│  │              AI Pipeline (Orchestrator)             │   │      │
│  │  ┌────────┐ ┌──────────┐ ┌──────┐ ┌───────────┐   │   │      │
│  │  │Whisper │ │ PyMuPDF  │ │ BGE  │ │  FAISS    │   │   │      │
│  │  │(ASR)   │ │ (Parse)  │ │(Embed│ │  (Vector  │   │   │      │
│  │  │        │ │          │ │+Rerk)│ │   Store)  │   │   │      │
│  │  └────────┘ └──────────┘ └──────┘ └───────────┘   │   │      │
│  │  ┌────────┐ ┌──────────┐ ┌─────────────┐          │   │      │
│  │  │LangC.  │ │ Gemini   │ │  Edge-TTS   │          │   │      │
│  │  │Retrvr  │ │ 2.5 API  │ │  (TTS)      │          │   │      │
│  │  └────────┘ └──────────┘ └─────────────┘          │   │      │
│  └────────────────────────────────────────────────────┘   │      │
└────────────────────────────────────────────────────────────┘      │
```

### 1.2 Component Responsibilities

| Component | Responsibility |
|---|---|
| **React SPA** | Browser-based UI. Handles file upload, audio recording, audio playback, chat display. |
| **FastAPI Server** | Backend API gateway. Routes requests, manages sessions, orchestrates the AI pipeline. |
| **Document Service** | Manages PDF upload, storage, and triggers processing pipeline. |
| **Chat Service** | Maintains conversation context, invokes the AI pipeline for QA. |
| **Audio Service** | Manages recording reception, ASR transcription requests, TTS synthesis requests. |
| **Session Service** | Creates and manages conversation sessions with isolated state. |
| **AI Pipeline** | Orchestrates the sequential AI operations: ASR → Retrieval → LLM → TTS. |

### 1.3 Data Flow

**Upload Flow:**
```
PDF Upload → Document Service → PyMuPDF (extract text) → BGE-M3 (embed chunks)
→ FAISS (store vectors + metadata)
```

**Query Flow:**
```
Browser Mic → Audio (WAV) → FastAPI → Audio Service → Whisper (ASR → text)
→ Chat Service → LangChain Retriever (FAISS query + MMR) → BGE Reranker v2
→ Gemini 2.5 Flash (generate answer) → Edge-TTS (synthesize speech)
→ Audio Service → FastAPI → Browser <audio> playback
```

---

## 2. Frontend Architecture

### 2.1 Folder Structure

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── MainLayout.tsx
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── SessionList.tsx
│   │   ├── upload/
│   │   │   ├── FileDropzone.tsx
│   │   │   ├── FileList.tsx
│   │   │   └── UploadProgress.tsx
│   │   ├── audio/
│   │   │   ├── RecordButton.tsx
│   │   │   ├── AudioPlayer.tsx
│   │   │   └── AudioVisualizer.tsx
│   │   └── common/
│   │       ├── Button.tsx
│   │       ├── Spinner.tsx
│   │       └── Toast.tsx
│   ├── hooks/
│   │   ├── useAudioRecorder.ts
│   │   ├── useAudioPlayer.ts
│   │   └── useSessions.ts
│   ├── services/
│   │   └── api.ts              # Axios instance + all API calls
│   ├── types/
│   │   └── index.ts            # TypeScript interfaces
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css               # Tailwind directives
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

### 2.2 Component Hierarchy

```
App
└── MainLayout
    ├── Header (app title, settings)
    ├── Sidebar
    │   └── SessionList (previous conversations)
    └── ChatWindow
        ├── MessageBubble[] (user + assistant messages)
        ├── ChatInput
        │   ├── FileDropzone (drag-drop PDF)
        │   └── RecordButton (mic capture)
        └── AudioPlayer (plays TTS response)
```

### 2.3 State Management

**Recommendation: React Context + useReducer (no Redux).**

Rationale: The application has three primary state concerns — sessions, current chat messages, and UI state (recording, uploading, playing). These do not warrant a global state library. React Context with `useReducer` for the chat state and `useState` for transient UI state is sufficient and avoids dependency overhead.

```
State Shape:
{
  sessions: Session[],
  currentSessionId: string | null,
  messages: Message[],
  isRecording: boolean,
  isUploading: boolean,
  isPlaying: boolean,
  error: string | null
}
```

For a university project, this is ideal. If the app grew beyond ~10 state values, consider Zustand (lighter than Redux, simpler than Context + useReducer for cross-cutting concerns).

### 2.4 API Communication

All HTTP calls are centralized in `src/services/api.ts` using Axios. A single Axios instance is configured with:
- `baseURL` pointing to FastAPI
- `timeout` configuration
- Response interceptor for error normalization

No WebSocket is needed — the workflow is request-response, not streaming. Audio is sent as `multipart/form-data`; TTS audio is returned as a binary blob and played via `URL.createObjectURL`.

### 2.5 Audio Recording

RecordButton uses the **MediaRecorder API**:
- Request `navigator.mediaDevices.getUserMedia({ audio: true })`
- Create a `MediaRecorder` with `audio/wav` MIME type
- Collect `Blob` chunks on `dataavailable`
- On stop, send the blob to `POST /api/audio/transcribe`

The `useAudioRecorder` hook encapsulates start/stop/error/cancel logic with `useRef` for the MediaRecorder instance.

### 2.6 Audio Playback

The `AudioPlayer` component receives a Blob URL from the API response. It uses the native `<audio>` element with `controls` hidden and programmatic `.play()`. The `useAudioPlayer` hook manages play/pause/stop and cleans up object URLs on unmount.

---

## 3. Backend Architecture

### 3.1 Folder Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app creation, lifespan, CORS
│   ├── config.py                 # Settings (pydantic-settings)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # Aggregates all v1 routers
│   │       ├── documents.py      # POST /upload, DELETE /documents/:id
│   │       ├── chats.py          # POST /sessions, POST /chats/query
│   │       ├── audio.py          # POST /audio/transcribe, POST /audio/synthesize
│   │       └── health.py         # GET /health
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dependencies.py       # Dependency injection (get_session, get_pipeline)
│   │   └── exceptions.py         # Custom exception classes + handlers
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py            # Pydantic request/response models
│   │   └── domain.py             # Domain models (Session, Document, Message, Chunk)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py
│   │   ├── chat_service.py
│   │   ├── audio_service.py
│   │   └── session_service.py
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # Coordinates the full AI pipeline
│   │   ├── asr.py                # faster-whisper wrapper
│   │   ├── pdf_parser.py         # PyMuPDF wrapper
│   │   ├── embedder.py           # BGE-M3 embedding wrapper
│   │   ├── vector_store.py       # FAISS index + metadata store
│   │   ├── retriever.py          # LangChain retriever + MMR
│   │   ├── reranker.py           # BGE Reranker v2 wrapper
│   │   ├── llm.py                # Gemini 2.5 Flash client
│   │   └── tts.py                # Edge-TTS wrapper
│   │
│   └── store/
│       ├── __init__.py
│       ├── session_store.py      # In-memory session storage
│       └── file_store.py         # Temporary file management
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── uploads/                      # Temporary PDF storage (gitignored)
├── faiss_index/                  # Persisted FAISS index (gitignored)
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

### 3.2 Layered Architecture

```
 ┌─────────────────────────────┐
 │         Routers             │  — Thin. Validate input, call service, return response.
 │   (api/v1/*.py)             │
 ├─────────────────────────────┤
 │         Services            │  — Business logic. Orchestrate domain operations.
 │   (services/*.py)           │
 ├─────────────────────────────┤
 │    Pipeline (AI Ops)        │  — AI model wrappers and orchestrator.
 │   (pipeline/*.py)           │
 ├─────────────────────────────┤
 │         Store               │  — Data access. In-memory, FAISS, file system.
 │   (store/*.py)              │
 └─────────────────────────────┘
```

**Rules:**
- Routers import only Services and Dependencies.
- Services import Pipeline components and Store.
- Pipeline components are isolated and have no knowledge of HTTP or services.
- Store is the lowest layer with zero dependencies on upper layers.

### 3.3 Router Layer

Routers are thin. They exist to:
1. Parse and validate HTTP input (path params, query params, request body)
2. Call a single service method
3. Return a Pydantic response model

They do NOT contain any business logic or AI pipeline invocation. This keeps them testable with minimal mocking.

### 3.4 Service Layer

Services contain orchestration logic that spans multiple pipeline components. For example:
- `DocumentService.upload()` saves the file, calls `PdfParser.parse()`, calls `Embedder.embed_chunks()`, calls `VectorStore.add_chunks()`.
- `ChatService.query()` calls `AudioService.transcribe()` (if voice input), calls `Retriever.retrieve()`, calls `Reranker.rerank()`, calls `LLM.generate()`, calls `TTs.synthesize()`.

Each service method is a single public method that represents a complete use case.

### 3.5 Dependency Injection

FastAPI's `Depends()` is used for dependency injection. Key dependencies:

| Dependency | Scope | Purpose |
|---|---|---|
| `get_vector_store` | Singleton | Shared FAISS index instance (or per-session with factory) |
| `get_session_store` | Singleton | In-memory session map |
| `get_pipeline_orchestrator` | Singleton | Shared AI pipeline instance |
| `get_current_session` | Request | Resolves session from header/param |

The AI pipeline components (Whisper, BGE, Gemini, Edge-TTS) are initialized once at startup in a `lifespan` context manager and injected into services. This avoids loading models on every request.

**Critical evaluation:** For a single-user assignment, singleton scope is fine. For multi-user, FAISS and session store should use per-session factories or database-backed storage. This architecture makes that swap trivial — changes are isolated to the dependency injection layer.

---

## 4. AI Pipeline

### 4.1 Component Responsibilities

| Component | Role |
|---|---|
| **faster-whisper** | Converts audio bytes to text transcript. Runs locally (CPU-optimized). Lower latency than cloud ASR for short utterances. |
| **PyMuPDF** | Extracts text from uploaded PDFs. Handles multi-column layouts, preserves paragraph structure. Returns raw text per page. |
| **BGE-M3** | Generates dense embeddings for text chunks. Supports multi-language and multi-granularity (token/sentence/document). Used for both indexing and query encoding. |
| **FAISS** | Stores embedded vectors with metadata (source document, page number, chunk index). Supports `IndexFlatIP` for cosine similarity search. In-memory but persistable to disk. |
| **LangChain Retriever** | Wraps FAISS with LangChain's `VectorStoreRetriever`. Provides `.get_relevant_documents()` interface and MMR (Maximum Marginal Relevance) to reduce redundancy in retrieved results. |
| **BGE Reranker v2** | Cross-encoder that re-scores top-K retrieved chunks. Significantly improves precision over pure embedding similarity. Applied after FAISS retrieval on a small candidate set (top-20 → top-5). |
| **Gemini 2.5 Flash** | Generates the final answer given the user question + retrieved chunks. Fast, cost-effective, supports context window of 1M tokens. Called via `google-generativeai` SDK. |
| **Edge-TTS** | Synthesizes text response to speech. Runs locally via Microsoft Edge's TTS engine. No cloud dependency. Multiple voice options available. |

### 4.2 Data Flow (Detailed)

```
PDF Upload:
  PDF bytes
  → PyMuPDF.open() → [page.text for page in doc]
  → TextSplitter(chunk_size=512, chunk_overlap=64)
  → BGE-M3.encode(chunks) → List[float[]]
  → FAISS.add_with_ids(embeddings, metadata={doc_id, page, chunk_idx})

Voice Query:
  WAV blob
  → faster-whisper.transcribe() → {text: "what is...", language: "en"}
  → (text) → BGE-M3.encode([text]) → query_vector
  → FAISS.search(query_vector, k=20) → [(chunk_id, score)]
  → LangChain Retriever (MMR, k=20, fetch_k=40)
  → [Document(page_content, metadata)] (top 20 chunks)
  → BGE Reranker v2.rerank(query, chunks) → [(chunk, relevance_score)]
  → Top 5 chunks
  → Prompt template: "Context: {chunks}\nQuestion: {query}\nAnswer:"
  → Gemini 2.5 Flash.generate(prompt) → answer_text
  → Edge-TTS.synthesize(answer_text) → WAV bytes
  → Return to browser as audio/wav blob
```

### 4.3 Chunking Strategy

Fixed-size chunking with overlap (512 chars, 64 overlap). Why not semantic chunking? For a university project, fixed-size is simpler, predictable, and sufficient. The reranker compensates for any context boundary issues. If this were production with varied document types, I would recommend semantic chunking via langchain's `RecursiveCharacterTextSplitter` — which we use anyway, making migration trivial.

### 4.4 Pipeline Orchestrator

The `Orchestrator` class in `pipeline/orchestrator.py` provides two public methods:

```python
class Orchestrator:
    async def process_document(self, file_path: str, doc_id: str) -> int:
        """Returns chunk count."""
        ...

    async def answer_question(
        self, audio_bytes: bytes | None, text: str | None, session_id: str
    ) -> AnswerResult:
        """Returns transcribed text + answer text + audio bytes."""
        ...
```

This abstraction means services never touch Whisper, FAISS, or Gemini directly. The orchestrator is the single point of change if the pipeline topology changes.

---

## 5. API Design

### 5.1 Endpoints

| Method | Endpoint | Request | Response | Responsibility |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | — | `{ status: "ok" }` | Liveness probe. |
| `POST` | `/api/v1/sessions` | — | `{ session_id, created_at }` | Create a new conversation session. |
| `GET` | `/api/v1/sessions` | — | `[{ session_id, created_at, message_count }]` | List all sessions. |
| `DELETE` | `/api/v1/sessions/:id` | — | `{ ok: true }` | Delete a session and its state. |
| `POST` | `/api/v1/documents/upload` | `multipart: file` | `{ doc_id, filename, chunk_count }` | Upload a PDF, process it, index it. |
| `GET` | `/api/v1/documents` | — | `[{ doc_id, filename, uploaded_at }]` | List uploaded documents. |
| `DELETE` | `/api/v1/documents/:id` | — | `{ ok: true }` | Delete a document and its chunks from FAISS. |
| `POST` | `/api/v1/chats/query` | `{ session_id, audio? (file), text? (str) }` | `{ answer_text, audio_url, chunks[] }` | Core RAG query. Accepts voice or text. |
| `GET` | `/api/v1/chats/:session_id/messages` | — | `[{ role, content, timestamp }]` | Retrieve chat history. |
| `POST` | `/api/v1/audio/transcribe` | `multipart: audio` | `{ text, language, duration }` | Standalone ASR (if needed separately). |
| `POST` | `/api/v1/audio/synthesize` | `{ text }` | `audio/wav` stream | Standalone TTS (if needed separately). |

### 5.2 Design Rationale

- **Versioned API (`/api/v1/`)**: Allows future breaking changes without affecting existing clients.
- **Session-based**: Each conversation gets a unique session, isolating contexts. The session_id is passed on every query.
- **Flexible query input**: The `POST /chats/query` accepts either `audio` (for voice) or `text` (for typing) or both. If both are provided, audio takes precedence for ASR, but text is used for retrieval. This enables future multi-modal input.
- **No streaming**: For simplicity, responses are fully generated before returning. The latency (ASR + retrieval + LLM + TTS) is acceptable for a university project (<10s). Streaming TTS would require WebSocket or chunked transfer, adding complexity without proportional benefit at this scale.
- **Audio returned as binary**: TTS output is returned directly as `audio/wav` with `Content-Type: audio/wav`, not as a base64 string. The browser creates an object URL from the response blob.

---

## 6. Database & Storage Design

### 6.1 FAISS Storage

FAISS indices are stored on disk in `backend/faiss_index/`:
- `index.faiss` — The FAISS binary index file
- `index.pkl` — Serialized metadata mapping (chunk_id → {doc_id, page, chunk_idx, text})

At application startup, these files are loaded. On new document upload, chunks are appended. The FAISS index is persisted after each document insertion.

**Why not a vector database (Pinecone, Qdrant, pgvector)?** For a university assignment, FAISS is sufficient, free, and runs locally. Adding a vector database is infrastructure overhead with zero benefit for a single-user, single-machine application. The architecture abstracts vector operations behind `VectorStore` interface — swapping to Qdrant later requires changing only `pipeline/vector_store.py`.

**Critical evaluation:** FAISS does not support incremental deletion easily. When a document is deleted, the entire index must be rebuilt from remaining chunks. This is a known trade-off. For this project, deletion is rare enough that rebuilding is acceptable. If frequent deletion were required, use SQLite with `sqlite-vec` or a proper vector DB.

### 6.2 Metadata

Metadata is stored as a flat dictionary keyed by FAISS index ID:

```python
{
    "chunk_0": {"doc_id": "uuid1", "page": 1, "chunk_index": 0, "text": "..."},
    "chunk_1": {"doc_id": "uuid1", "page": 1, "chunk_index": 1, "text": "..."},
}
```

Stored in a pickle file alongside the FAISS index. The text is stored in metadata because FAISS stores only embeddings — without text metadata, retrieved results are meaningless.

### 6.3 Temporary Files

Uploaded PDFs are stored in `backend/uploads/` with a UUID filename. After processing, they can be deleted or retained for re-indexing. The architecture retains them by default (allows re-indexing with different chunk parameters without re-uploading).

### 6.4 Session Handling

Sessions are stored in-memory using a dictionary in `store/session_store.py`:

```python
class SessionStore:
    _sessions: dict[str, Session]
    
    def create(self) -> Session: ...
    def get(self, session_id: str) -> Session | None: ...
    def delete(self, session_id: str): ...
    def list(self) -> list[Session]: ...
```

Each `Session` contains:
- `session_id` (UUID)
- `created_at` (datetime)
- `messages` (list of `Message` objects with `role`, `content`, `timestamp`)

**Why in-memory?** No database dependency, zero setup, instant performance. Session data is transient — losing it on restart is acceptable for a university project. For persistence, swapping to SQLite requires changing only this class.

---

## 7. Testing Architecture

### 7.1 Unit Testing

**Framework:** pytest

**What to test:**

| Layer | What to test | Example |
|---|---|---|
| **Schemas** | Pydantic validation, field coercion, error cases | Invalid session_id format, missing required fields |
| **Domain models** | Object creation, equality, serialization | Session creation sets correct defaults |
| **Pipeline components** | Each AI wrapper in isolation (with mocked models) | `PdfParser.parse()` returns correct chunk count; `Embedder.embed_chunks()` returns vectors of correct dimension |
| **Services** | Orchestration logic with all pipeline components mocked | `DocumentService.upload()` calls parse → embed → store in sequence; `ChatService.query()` returns `AnswerResult` |
| **Store** | Session CRUD, FAISS add/search/delete | `SessionStore.create()` returns unique IDs; `VectorStore.search()` returns correct chunks |
| **Routers** | HTTP status codes, response shapes, error responses | `POST /documents/upload` without file returns 422 |

### 7.2 Integration Testing

**What to test:**

| Test | Description |
|---|---|
| **PDF → FAISS pipeline** | Upload a real PDF (small, e.g. 3 pages), verify chunks are in FAISS and searchable |
| **ASR + LLM flow** | Transcribe a known audio file, verify correct text, pass through mocked LLM |
| **Full query endpoint** | `POST /chats/query` with a known document indexed, verify response contains expected answer |
| **Session isolation** | Two sessions query the same document; verify separate histories |

Integration tests use real model instances but small data (e.g., a 100-word PDF, a 3-second audio clip). They run against a test FAISS index stored in a temporary directory.

### 7.3 End-to-End Testing

**Framework:** Playwright (for browser automation)

**What to test:**

| Test | Description |
|---|---|
| **Upload flow** | Navigate to page, upload PDF, verify success toast, verify document appears in list |
| **Voice query flow** | Click mic, speak (simulate via Playwright's mock media), verify audio response plays |
| **Chat display** | Verify messages appear in correct order (user → assistant) |
| **Error handling** | Upload non-PDF file, verify error message |

For a university project, E2E tests are optional but recommended. They catch integration bugs that unit and integration tests miss (e.g., CORS misconfiguration, blob URL handling).

### 7.4 Test Doubles Strategy

- **Pipeline models**: All ML models are expensive to instantiate. Use `pytest.fixture` with `unittest.mock.patch` or dependency injection to replace them with stubs.
- **FAISS**: Use a temporary directory with `tmp_path` fixture and a fresh FAISS index.
- **File system**: Use `tmp_path` for uploaded PDFs.

---

## 8. Deployment Architecture

### 8.1 Recommended Strategy: Single Machine (Docker Compose)

For a university assignment, the simplest deployment that satisfies all requirements is a single machine running:

```
Caddy / nginx (reverse proxy)
├── Frontend (Vite dev server or static build served by nginx)
└── Backend (Uvicorn serving FastAPI)
```

**Docker Compose services:**
1. `caddy` — Reverse proxy, TLS termination (localhost certs), static file serving for frontend
2. `backend` — FastAPI on Uvicorn, mounted `uploads/` and `faiss_index/` as volumes

### 8.2 Why Not Cloud Deployment?

Cloud deployment (AWS, GCP, Azure) introduces:
- Cost (Gemini API is cheap, but VM/compute cost is not zero)
- CI/CD pipeline setup
- Environment variable management
- Security considerations (API key rotation)

None of these add academic value to a university project. Local Docker Compose is sufficient to demonstrate the architecture, and the design is cloud-ready — changing the deployment target requires changing only the Docker Compose file, not the application code.

### 8.3 Production Readiness Checklist

Even without cloud deployment, the architecture supports:
- **Environment-based config** via `pydantic-settings` (`.env` file)
- **CORS middleware** configured for frontend origin
- **Health endpoint** for monitoring
- **Graceful shutdown** (lifespan context manager)
- **Structured logging** (use `loguru` or `structlog`)

---

## 9. Architecture Decisions

### 9.1 Decision: LangChain for Retrieval Only, Not Full Pipeline

**Status:** Accepted

**Rationale:** LangChain is used exclusively for the `VectorStoreRetriever` wrapper (with MMR). The rest of the pipeline (ASR, PDF parsing, embedding, reranking, LLM, TTS) uses direct library calls.

**Why not LangChain for everything?**
- LangChain's abstraction layers add complexity that obscures the actual data flow
- Custom pipeline is easier to debug and test
- The project is small enough that LangChain's "chains" and "agents" provide no benefit
- When something breaks, you debug a 10-line orchestrator, not a 100-line LangChain chain

**Trade-off:** Slightly more code for components that LangChain could provide. However, each component is now independently testable and replaceable. The 50 lines saved by using LangChain chains are not worth the loss of clarity.

### 9.2 Decision: In-Memory Sessions Instead of Database

**Status:** Accepted with caveat

**Rationale:** Sessions are transient, short-lived, and single-user. An in-memory dict is the simplest possible implementation with zero infrastructure.

**Caveat:** If persistence across restarts is required, replace `SessionStore` with SQLite. The interface is already abstracted — this requires changing exactly one file (`store/session_store.py`) and adding `aiosqlite` to requirements.

**Trade-off:** All sessions are lost on server restart. For a university project, this is acceptable. In production, swap to SQLite or Redis.

### 9.3 Decision: FAISS Over Vector Database

**Status:** Accepted

**Rationale:** FAISS is a local, file-based vector index. No server, no API key, no network calls. It is the fastest possible vector search for a single-machine deployment.

**Comparison:**

| Criterion | FAISS | Pinecone / Qdrant |
|---|---|---|
| Setup | pip install | Docker/Kubernetes + API keys |
| Speed | ~1ms per query | ~5-10ms (network) |
| Persistence | Manual (pickle) | Automatic |
| Scaling | Single machine | Distributed |
| Cost | Free | Free tier exists |

For a university assignment, FAISS wins on every relevant criterion. The only downside (non-incremental deletion) is acceptable for this use case.

### 9.4 Decision: Edge-TTS Over Cloud TTS

**Status:** Accepted

**Rationale:** Edge-TTS runs locally, requires no API key, has no usage limits, supports multiple voices, and produces high-quality output comparable to Google Cloud TTS.

**Trade-off:** It depends on Microsoft Edge WebSocket endpoints, which could change. However, the library is actively maintained and this risk is acceptable for a university project. If the endpoint changes, swap to `gTTS` (Google Text-to-Speech, free, no API key) with a one-line change in `pipeline/tts.py`.

### 9.5 Decision: No Streaming (Request-Response Only)

**Status:** Accepted

**Rationale:** The full pipeline (ASR + Retrieval + LLM + TTS) takes 3-10 seconds. Streaming the LLM output token-by-token would save ~1-2 seconds of perceived latency but would require:
- Server-Sent Events (SSE) or WebSocket on the backend
- Streaming TTS (chunked audio synthesis)
- Complex state management on the frontend (partial audio playback)

For a university project, the complexity does not justify the benefit. The user speaks → waits → hears response pattern is familiar (like voice assistants) and acceptable at this latency.

**If streaming were required later:** The `Orchestrator.answer_question()` method is the single place to change. It could yield intermediate results (transcription, retrieval sources, audio chunks) via an async generator.

### 9.6 Decision: Singleton AI Pipeline Components

**Status:** Accepted

**Rationale:** Loading BGE-M3, faster-whisper, and BGE Reranker consumes significant memory (~4-8 GB total). Initializing them at startup and reusing across requests is essential for performance. The lifespan context manager in `main.py` handles this cleanly.

**Trade-off:** These components are stateful and not thread-safe in all cases. For a single-user FastAPI app (one worker, one request at a time), this is safe. For multi-user, use a process pool or async locks.

### 9.7 Decision: Async FastAPI with Sync AI Models

**Status:** Accepted

**Rationale:** FastAPI is async-native. However, most ML libraries (FAISS, PyMuPDF, faster-whisper) are synchronous and CPU-bound. Running them in async handlers would block the event loop.

**Solution:** Use FastAPI's `run_in_executor` to run CPU-bound pipeline operations in a thread pool. The orchestrator's `answer_question()` and `process_document()` methods run blocking operations in `ThreadPoolExecutor`, keeping the HTTP handler responsive.

**Alternatives considered:**
- Pure sync FastAPI: Loses async benefits for I/O-bound operations (file reads, Gemini API calls)
- Sending work to Celery: Overkill for single-user
- Using `asyncio.to_thread()`: Same effect as `run_in_executor`, cleaner in Python 3.9+

The hybrid approach (async HTTP + sync ML via executor) is the standard pattern for ML-serving FastAPI applications.

### 9.8 Decision: One Router Per Domain

**Status:** Accepted

**Rationale:** Separating routers by domain (documents, chats, audio, health) follows the principle of single responsibility. Each router file is small (10-30 lines), focused, and easy to navigate.

**Alternatives:**
- Single monolithic router: Couples all endpoints, harder to test, harder to read
- Router per HTTP method: Unnatural grouping, no cohesion

The per-domain grouping aligns with the service layer structure and makes it easy to find where a given feature is implemented.

### 9.9 Decision: No Authentication

**Status:** Accepted with note

**Rationale:** For a university assignment running locally, authentication adds complexity (JWT, OAuth2, session tokens) with zero security benefit. The app runs on localhost and is not exposed to the internet.

**Note:** If the project specification requires authentication, add FastAPI's `HTTPBearer` dependency. The dependency injection system makes this a cross-cutting concern — add a `get_current_user` dependency and apply it to all routes except `/health`.

---

## Conclusion

This architecture prioritizes:
- **Clarity** over cleverness
- **Testability** over abstraction
- **Modularity** over monolithic design
- **Pragmatism** over over-engineering

Every component can be replaced, tested, or removed independently. The data flow is explicit and traceable. The deployment is simple but the architecture is production-ready.

The project will scale with the developer: start with the core pipeline, add services, then wire up the frontend. Each layer is independently verifiable.
