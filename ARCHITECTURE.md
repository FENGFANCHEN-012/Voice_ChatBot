# Voice RAG Assistant — Architecture Document

**Author:** Senior AI Solution Architect  
**Date:** August 2026  
**Status:** Production System Architecture v1.2  

---

## Table of Contents

1. [Overall System Architecture](#1-overall-system-architecture)
2. [Frontend Architecture](#2-frontend-architecture)
3. [Backend Architecture](#3-backend-architecture)
4. [AI & RAG Pipeline](#4-ai--rag-pipeline)
5. [API Design & Streaming Transports](#5-api-design--streaming-transports)
6. [Database & Storage Design](#6-database--storage-design)
7. [Testing & RAGAS Evaluation Architecture](#7-testing--ragas-evaluation-architecture)
8. [Deployment & Cloud Architecture (Google Colab / Docker)](#8-deployment--cloud-architecture-google-colab--docker)
9. [Architecture Decisions (ADRs)](#9-architecture-decisions-adrs)

---

## 1. Overall System Architecture

### 1.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                FRONTEND (React / Vite :5173)                             │
│                                                                                          │
│   App.tsx ─── SessionList ─── ChatWindow / MessageBubble ─── ChatInput ─── FileDropzone │
│      │             │                      │                      │              │        │
│      │ REST        │ REST                 │ SSE Token Stream     │ WebSocket    │ REST   │
│      ▼             ▼                      ▼                      ▼              ▼        │
└──────┼─────────────┼──────────────────────┼──────────────────────┼──────────────┼────────┘
       │             │                      │                      │              │
       │ REST        │ REST                 │ SSE                  │ WebSocket    │ REST
       ▼             ▼                      ▼                      ▼              ▼
┌──────┴─────────────┴──────────────────────┴──────────────────────┴──────────────┴────────┐
│                                BACKEND (FastAPI :8000)                                   │
│                                                                                          │
│  /api/v1/sessions  /api/v1/documents  /chats/query/stream  /ws/tts  /audio/transcribe    │
│        │                 │                    │               │             │            │
│  SessionService    DocumentService      ChatService      AudioService  AudioService  │
│        │                 │                    │               │             │            │
│  SessionStore      PdfParser           Orchestrator    edge-tts       faster-whisper │
│  (in-memory)   ──► Embedder        ┌──────┴──────────┐   (WebSocket)    (Whisper Base)│
│                    FileStore       │ HybridSearch    │                                   │
│                    VectorStore     │ + Reranker      │                                   │
│                    (ChromaDB/FAISS)│ + Gemini 3.5    │                                   │
│                                    └─────────────────┘                                   │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Core Technology Stack

| Layer | Component / Library | Purpose & Details |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Single-page UI with SSE streaming, WebSocket audio handling, live waveform visualizer |
| **Backend Framework** | Python 3.12/3.13, FastAPI, Uvicorn | Async ASGI server providing REST, SSE, and WebSocket endpoints |
| **Vector Storage** | **ChromaDB** (default) / **FAISS** (fallback) | Persistent vector store with metadata filtering (`chromadb>=0.5.0`, `faiss-cpu>=1.10.0`) |
| **Embedder** | BAAI/bge-m3 (`sentence-transformers`) | Dense text embeddings (1024 dims, multi-lingual) |
| **Reranker** | BAAI/bge-reranker-v2-m3 (`CrossEncoder`) | Deep cross-encoder re-scoring of top candidates on CUDA / CPU |
| **Sparse Search** | rank-bm25 | BM25 lexical keyword search combined with dense retrieval via Reciprocal Rank Fusion (RRF) |
| **LLM Engine** | Google Gemini 3.5 Flash Lite / Flash | Generative response synthesis (`google-genai` / `google-generativeai`) |
| **Speech-to-Text (ASR)** | faster-whisper (Whisper `base` model) | CTranslate2-accelerated local transcription with auto-GPU/CPU fallback |
| **Text-to-Speech (TTS)** | edge-tts (`en-US-AndrewMultilingualNeural`) | High-quality neural speech synthesis with sentence-boundary flushing & MD5 caching |
| **Evaluation Suite** | RAGAS Framework (`ragas>=0.2.0`) | Automated evaluation of Faithfulness, Context Recall, Context Precision, and Answer Correctness |

---

## 2. Frontend Architecture

### 2.1 Folder Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── AppShell.tsx
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── SessionList.tsx
│   │   │   └── TypingIndicator.tsx
│   │   ├── upload/
│   │   │   ├── FileDropzone.tsx
│   │   │   ├── FileList.tsx
│   │   │   └── UploadProgress.tsx
│   │   ├── audio/
│   │   │   ├── RecordButton.tsx
│   │   │   ├── AudioPlayer.tsx
│   │   │   └── AudioVisualizer.tsx
│   │   └── common/
│   ├── hooks/
│   │   ├── useAudioRecorder.ts
│   │   ├── useAudioPlayer.ts
│   │   ├── useTtsSocket.ts           # WebSocket lifecycle, audio queue, sequential playback
│   │   └── useSessions.ts
│   ├── services/
│   │   └── api.ts                     # Axios REST client + SSE stream wrappers
│   ├── App.tsx                        # Master layout & sentence-boundary TTS flushing
│   └── main.tsx
├── vite.config.ts                     # Configured for local & Google Colab ngrok proxying
└── package.json
```

### 2.2 Streaming UX & Sentence-Boundary TTS Flushing

1. **Token Streaming**: Text streams from `POST /api/v1/chats/query/stream` via Server-Sent Events (SSE). The UI re-renders tokens instantly.
2. **Sentence-Boundary Flushing**: As tokens stream into `App.tsx`, text is accumulated. Once a sentence boundary (`.`, `!`, `?`, `\n`, `。`, `！`, `？`) is detected, the complete sentence is immediately sent over the WebSocket (`/ws/tts`).
3. **Sequential Audio Playback**: The `useTtsSocket` hook receives binary MP3 frames from the backend, queues them, and plays them seamlessly in sequence. Speech starts within milliseconds—long before the LLM finishes generating the full response.

---

## 3. Backend Architecture

### 3.1 Directory Structure

```
backend/
├── app/
│   ├── main.py                   # FastAPI app, lifespan setup, CORS, route registration
│   ├── config.py                 # Pydantic Settings (loads from .env / env vars)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py         # Main API v1 router aggregator
│   │       ├── documents.py      # Upload PDF, delete document, GET /documents/{id}/progress
│   │       ├── chats.py          # Session query, SSE stream (/chats/query/stream), clear-cache
│   │       ├── audio.py          # ASR transcribe, REST TTS synthesize
│   │       └── health.py         # Liveness check endpoint
│   ├── services/
│   │   ├── document_service.py   # PDF upload, async background indexing, progress streaming
│   │   ├── chat_service.py       # Manages chat history, invokes Orchestrator
│   │   ├── audio_service.py      # faster-whisper ASR & edge-tts synthesis wrapper
│   │   └── session_service.py    # Session CRUD operations
│   ├── pipeline/
│   │   ├── orchestrator.py       # Main pipeline orchestrator (hybrid search -> rerank -> LLM)
│   │   ├── hybrid_search.py      # BM25 + BGE-M3 RRF hybrid retriever
│   │   ├── query_normalizer.py   # Noise cleaning, abbreviation expansion, metadata extraction
│   │   ├── reranker.py           # BAAI/bge-reranker-v2-m3 CrossEncoder
│   │   ├── llm.py                # Gemini 3.5 Flash Lite client with streaming
│   │   ├── vector_store.py       # ChromaDB / FAISS vector store abstraction
│   │   ├── pdf_parser.py         # PyMuPDF parser (Semantic & Recursive chunking)
│   │   ├── embedder.py           # BGE-M3 embedding generator
│   │   ├── asr.py / tts.py       # Audio pipeline stubs
│   │   ├── agent_rag.py          # Query classifier (simple, reasoning, comparison, out_of_scope)
│   │   ├── hyde.py               # Hypothetical Document Embeddings generator
│   │   ├── query_expander.py     # Multi-query expansion wrapper
│   │   └── self_rag.py           # Answer relevance verifier
│   └── store/
│       ├── session_store.py      # In-memory session store
│       └── file_store.py         # Disk file manager (uploads/ & documents.json)
└── tests/
    ├── run_tests.py              # CLI test harness for ASR, Latency, Load & RAGAS
    ├── evaluate_ragas.py         # RAGAS evaluation runner with Google GenAI
    ├── test_asr.py               # ASR accuracy tests
    ├── test_latency.py           # End-to-end latency benchmarks
    └── test_load.py              # Concurrent user load testing
```

---

## 4. AI & RAG Pipeline

### 4.1 Hybrid Retrieval & Reranking Flow

```
User Query (Voice / Text)
  │
  ▼
[Query Normalizer] ──► Strip filler words (um, uh, like), expand abbreviations (SSO → single sign-on),
  │                    extract metadata hints (Error Codes, Form Codes, Chapters)
  ▼
[Hybrid Search (RRF)]
  ├──► 1. Dense Vector Search (BGE-M3 in ChromaDB/FAISS) ──► Top-10 Chunks
  └──► 2. Sparse Lexical Search (BM25 Index)            ──► Top-10 Chunks
  │
  ▼
[Reciprocal Rank Fusion (RRF)] ──► RRF Score = 1 / (60 + rank_dense) + 1 / (60 + rank_bm25)
  │
  ▼
[CrossEncoder Reranker (bge-reranker-v2-m3)] ──► Re-scores candidates (Top-10 → Top-5)
  │
  ▼
[Gemini 3.5 Flash Lite (Stream)] ──► Generates response tokens with rate-limiting backoff
```

### 4.2 Document Processing & Chunking

1. **Extraction**: `PyMuPDF` extracts plain text page-by-page from uploaded PDFs.
2. **Chapter Tagging**: Regex (`Chapter \d+`) and keyword mapping detect and tag each chunk with `doc_id`, `page`, `chunk_index`, and `chapter`.
3. **Chunking Strategies**:
   - **Semantic Chunking (Default)**: `LlamaIndex` `SemanticSplitterNodeParser` splits document content on semantic shifts based on embedding distance.
   - **Recursive Character Chunking**: `LangChain` `RecursiveCharacterTextSplitter` (chunk size 512, overlap 64) as configurable option.
4. **Vector Storage**: Chunks are embedded in batches of 32 using BGE-M3 and persisted in **ChromaDB** (`chroma_db/`) or **FAISS** (`faiss_index/`).

---

## 5. API Design & Streaming Transports

### 5.1 Endpoint Specification

| Method | Endpoint | Request Body / Params | Response | Description |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | — | `{ status: "ok" }` | Health check endpoint |
| `POST` | `/api/v1/sessions` | — | `{ session_id, created_at }` | Create new chat session |
| `GET` | `/api/v1/sessions` | — | `[{ session_id, title, created_at }]` | List active sessions |
| `DELETE`| `/api/v1/sessions/{id}` | — | `{ status: "success" }` | Delete session |
| `POST` | `/api/v1/documents/upload` | `multipart/form-data: file` | `{ id, filename, status }` | Upload PDF and start background processing |
| `GET` | `/api/v1/documents/` | — | `[{ id, filename, uploaded_at, chunks }]` | List indexed documents |
| `GET` | `/api/v1/documents/{id}/progress` | — | `text/event-stream` (SSE) | Stream document embedding progress |
| `DELETE`| `/api/v1/documents/{id}` | — | `{ status: "deleted" }` | Remove document from storage and vector store |
| `POST` | `/api/v1/chats/query` | `form: session_id, text` | `{ answer_text, chunks[] }` | Non-streaming query response |
| `POST` | `/api/v1/chats/query/stream` | `form: session_id, text` | `text/event-stream` (SSE) | SSE streaming answer tokens + final citations |
| `POST` | `/api/v1/chats/clear-cache` | — | `{ status: "cleared" }` | Clear query result cache |
| `POST` | `/api/v1/audio/transcribe` | `multipart/form-data: file` | `{ text, language, duration }` | Transcribe voice clip with faster-whisper |
| `POST` | `/api/v1/audio/synthesize` | `{ text }` | `audio/mpeg` binary blob | REST endpoint for TTS synthesis |
| `WS` | `/ws/tts` | WebSocket frames | Binary MP3 frames + `{ status: "done" }` | Real-time sentence-by-sentence TTS streaming |

---

## 6. Database & Storage Design

1. **ChromaDB Vector Store (`chroma_db/`)**:
   - Primary vector database storing 1024-dimensional BGE-M3 embeddings.
   - Preserves chunk text, document ID, page numbers, and detected chapter metadata.
2. **FAISS Index (`faiss_index/`)**:
   - Secondary lightweight vector storage option (`index.faiss` + `metadata.pkl`).
3. **File Store (`uploads/` & `documents.json`)**:
   - Persists uploaded PDF documents on disk with metadata tracking.
4. **Session Store (`SessionStore`)**:
   - In-memory thread-safe dictionary maintaining conversation histories per `session_id`.
5. **TTS Cache (`TTSCache`)**:
   - In-memory LRU cache storing synthesized sentence MP3 audio indexed by MD5 hash.

---

## 7. Testing & RAGAS Evaluation Architecture

The backend includes a comprehensive test suite executed via `python backend/tests/run_tests.py`:

```
Select test to run:
1. ASR Accuracy Test (Whisper transcription WER evaluation)
2. Latency Test (End-to-end response & TTS timing benchmarks)
3. Load Test (Concurrent user stress testing)
4. RAG Evaluation (RAGAS framework answer quality assessment)
5. Run All Tests
```

### 7.1 RAGAS Metric Suite (`evaluate_ragas.py`)
Utilizes the official `ragas` library (`from google import genai` via `google-genai` SDK) to evaluate 30 benchmark queries:
- **Faithfulness**: Verifies whether the generated answer is grounded strictly in retrieved context.
- **Context Recall**: Measures if all ground-truth information was retrieved from documents.
- **Context Precision**: Evaluates the signal-to-noise ratio in retrieved context chunks.
- **Answer Correctness**: Assesses factual accuracy against reference ground-truth answers.

---

## 8. Deployment & Cloud Architecture (Google Colab / Docker)

### 8.1 Google Colab Cloud GPU Deployment

The backend can run seamlessly in Google Colab to leverage free T4/A100 GPUs for faster-whisper ASR and BGE-Reranker-v2:

```python
# 1. Set Google Gemini API key in Colab
import os
from google.colab import userdata
os.environ["GEMINI_API_KEY"] = userdata.get("GEMINI_API_KEY")

# 2. Start Uvicorn with ngrok tunnel
from pyngrok import ngrok
public_url = ngrok.connect(8000).public_url
print("Public Cloud Backend URL:", public_url)
```

### 8.2 Frontend Vite Proxy Configuration
The frontend automatically proxies `/api` and `/ws` to the Cloud Backend or local server via [frontend/vite.config.ts](file:///C:/Users/johny/OneDrive%20-%20Ngee%20Ann%20Polytechnic/Desktop/Voice_ChatBot/frontend/vite.config.ts):

```typescript
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_URL || "https://your-ngrok-url.ngrok-free.dev",
        changeOrigin: true,
        secure: false,
        headers: { "ngrok-skip-browser-warning": "true" },
      },
      "/ws": {
        target: (process.env.VITE_BACKEND_URL || "https://your-ngrok-url.ngrok-free.dev").replace(/^http/, "ws"),
        ws: true,
        secure: false,
      },
    },
  },
});
```

---

## 9. Architecture Decisions (ADRs)

### ADR-01: ChromaDB as Primary Vector Store with FAISS Fallback
- **Decision**: Use ChromaDB as default vector store; retain FAISS adapter for lightweight fallback.
- **Rationale**: ChromaDB provides native metadata filtering and persistent storage, eliminating manual pickle serialization issues.

### ADR-02: Dense + Sparse Hybrid Search with Reciprocal Rank Fusion (RRF)
- **Decision**: Combine BGE-M3 dense embeddings with BM25 sparse keyword search via RRF scoring ($RRF\_Score = \sum \frac{1}{60 + rank}$).
- **Rationale**: Pure dense vector search can miss exact keyword matches (e.g. error codes like `ERR-SSO-4039` or form numbers `HR-PAY-102`). BM25 ensures exact code matches while BGE-M3 captures semantic intent.

### ADR-03: Sentence-Boundary Streaming TTS over WebSocket
- **Decision**: Stream text via SSE while sending complete sentences over WebSocket `/ws/tts` for real-time audio playback.
- **Rationale**: Reduces perceived voice response latency from ~8 seconds to <1 second, as audio synthesis starts on the first completed sentence.

### ADR-04: CrossEncoder Reranking (BAAI/bge-reranker-v2-m3)
- **Decision**: Re-rank top 10 hybrid candidates down to top 5 using a dedicated CrossEncoder model.
- **Rationale**: Cross-attention scoring significantly boosts context precision and eliminates irrelevant document chunks before sending context to Gemini.

### ADR-05: Adoption of `google-genai` SDK for RAGAS Evaluation
- **Decision**: Integrate `google-genai` alongside `google-generativeai`.
- **Rationale**: Enables seamless evaluation of Gemini models via the latest `ragas` `llm_factory` while maintaining legacy compatibility.
