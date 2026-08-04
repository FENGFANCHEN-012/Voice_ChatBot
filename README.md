# Enterprise Real-Time Voice RAG ChatBot 🎙️🤖

An enterprise-grade, real-time **Voice Retrieval-Augmented Generation (RAG) Assistant** designed for low-latency, high-accuracy document intelligence and conversational speech interaction.

The system integrates **Faster-Whisper ASR**, **BM25 + BGE-M3 Hybrid Search**, **BGE-Reranker-v2-m3 Cross-Encoder Reranking**, **Dual LLM Engines (DeepSeek-V3 & Google Gemini)**, and **Streaming Edge-TTS Audio Output**.

---

## 🌟 Key Features

* ⚡ **Ultra-Low Spoken Latency (< 2.8s)**: Audio streaming begins out-loud while the LLM is still generating subsequent sentences.
* 🎯 **Hybrid Retrieval (RAG)**: Combines dense vector similarity (`BAAI/bge-m3`) and sparse keyword search (`rank-bm25`) using Reciprocal Rank Fusion (RRF).
* 🔬 **Cross-Encoder Reranking**: Re-ranks top candidate chunks using `BAAI/bge-reranker-v2-m3` for maximum precision.
* 🔀 **Sub-Query Decomposition**: Automatically splits multi-entity & comparison queries into sub-queries to achieve high Context Recall across document chapters.
* 🧠 **Dual LLM Provider System (DeepSeek-V3 + Gemini)**:
  * **DeepSeek-V3 (`deepseek-chat`)**: High-throughput streaming via REST API with 128k context window and strict system prompt compliance.
  * **Google Gemini**: Full multi-modal fallback support.
* 🎙️ **Real-Time Voice Pipeline**:
  * **Speech-to-Text (ASR)**: Uses `faster-whisper` (base/medium models) with PyTorch CUDA GPU acceleration.
  * **Text-to-Speech (TTS)**: Streams MP3 audio chunks via WebSocket (`/ws/tts`) using a sequence-locked queue for natural out-loud speech.
  * **TTS Sanitization**: Automatic regex cleaning converts slashes (`/`, `\`) and markdown symbols into natural spoken phrases.
* ☁️ **Dual Execution Architecture**:
  * **Cloud GPU (Google Colab T4)**: Sub-3s voice latency with CUDA acceleration (~35ms rerank time).
  * **Local CPU/GPU**: For offline local development.

---

## 📐 System Architecture

```mermaid
graph TD
    User([User Voice / Text Input]) --> Frontend[React + Vite Frontend\nlocalhost:5173]
    
    subgraph Frontend Layer
        Frontend -->|Audio Blob| ASR_Call[POST /api/v1/audio/transcribe]
        Frontend -->|Stream Token| SSE_Call[POST /api/v1/chats/query/stream]
        Frontend -->|Audio Segment| WS_Call[WebSocket /ws/tts]
    end

    subgraph Backend Orchestration Layer (FastAPI)
        ASR_Call --> FasterWhisper[Faster-Whisper ASR\nbase / medium int8/float16]
        FasterWhisper --> QueryEngine[Pipeline Orchestrator]
        SSE_Call --> QueryEngine
        
        QueryEngine -->|1. Sub-Query Decomposition| MultiQuery[Query Expander]
        MultiQuery -->|Keyword Search| BM25[BM25 Index]
        MultiQuery -->|Dense Vector Search| Chroma[ChromaDB Vector Store]
        
        BM25 --> Hybrid[Hybrid Search RRF Fusion\nTop 35 Candidates]
        Chroma --> Hybrid
        
        Hybrid --> Reranker[CrossEncoder Reranker\nBAAI/bge-reranker-v2-m3\n⚡ 35ms on GPU]
        Reranker --> TopDocs[Top 10 Context Chunks]
        
        TopDocs --> LLMEngine[LLM Provider Engine\nDeepSeek-V3 / Gemini]
        LLMEngine -->|Streaming Tokens| Frontend
    end

    subgraph Audio Output Layer
        WS_Call --> EdgeTTS[Edge-TTS Streamer]
        EdgeTTS -->|MP3 Audio Chunks| Playback[Sequence-Locked Audio Queue]
    end
```

> 📘 **Full Architecture Documentation**: [`docs/Voice_RAG_Architecture_v2.2.pdf`](file:///C:/Users/johny/OneDrive%20-%20Ngee%20Ann%20Polytechnic/Desktop/Voice_ChatBot/docs/Voice_RAG_Architecture_v2.2.pdf)


---

## Prerequisites

- Python **3.11+**
- Node.js **18+**
- API keys (at least one):
  - **DeepSeek** — https://platform.deepseek.com (primary)
  - **Google Gemini** — https://aistudio.google.com/app/apikey (fallback / advanced pipeline)
- (Optional) **NVIDIA GPU + CUDA** for accelerated inference

---

## 1. Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS / Linux

pip install -r requirements.txt
cp .env.example .env           # then fill in your API keys
```

### Frontend

```bash
cd frontend
npm install
```

### Configuration

Edit `backend/.env`:

| Setting                | Default                    | Purpose                                  |
| ---------------------- | -------------------------- | ---------------------------------------- |
| `LLM_PROVIDER`         | `deepseek`                 | `deepseek`, `gemini`, or `auto`          |
| `DEEPSEEK_API_KEY`     | —                          | Primary LLM                              |
| `GEMINI_API_KEY`       | —                          | Fallback LLM + AgentRAG/QueryExpander    |
| `WHISPER_USE_GPU`      | `true`                     | Run faster-whisper on GPU (auto-fallback)|
| `VECTOR_STORE_TYPE`    | `chroma`                   | `chroma` or `faiss`                      |

### Run

```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev     # http://localhost:5173
```

Open `http://localhost:5173`, upload a PDF, and ask a question by voice.

---

## 2. GPU Setup

### 2.1 Requirements

- NVIDIA GPU with CUDA compute capability **7.5+** (RTX 20-series or newer recommended)
- [NVIDIA Driver](https://www.nvidia.com/drivers)
- [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads)
- Install **PyTorch with CUDA** (not the CPU build):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

> `pip install -r requirements.txt` installs a CPU-compatible torch by default. The command above replaces it with the CUDA build.

### 2.2 Verify GPU is detected

```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"
```

Expected output:

```
CUDA available: True
GPU: NVIDIA GeForce RTX 3060
```

If it prints `False`, the CPU fallback is used automatically — no code changes needed.

### 2.3 What runs on the GPU

Everything auto-detects CUDA at startup and falls back to CPU if unavailable:

| Component                  | GPU behavior                                                    |
| -------------------------- | --------------------------------------------------------------- |
| **faster-whisper (ASR)**   | `WHISPER_USE_GPU=true` → CUDA + FP16; falls back to CPU + int8  |
| **Embedder (bge-m3)**      | `torch.cuda.is_available()` → CUDA                              |
| **Reranker (bge-reranker)**| `torch.cuda.is_available()` → CUDA                              |
| **Advanced pipeline**      | AgentRAG + QueryExpander **only enabled when CUDA is available**|

Startup log confirms it:

```
[Pipeline] Advanced retrieval (AgentRAG + QueryExpander): ENABLED
```

### 2.4 Advanced pipeline (AgentRAG + QueryExpander)

When a CUDA GPU is detected, the pipeline classifies each query with **AgentRAG** (simple_fact / complex_reasoning / comparison / summarization / out_of_scope) and rewrites it with **QueryExpander** before retrieval. This significantly improves **comparison** and **multi-hop** questions.

- Auto-enabled when `torch.cuda.is_available()` is `True`
- Disable manually in `backend/.env`:

```
USE_ADVANCED_PIPELINE=false
```

### 2.5 Cloud GPU (Google Colab + ngrok)

You can also run the backend on a free Colab GPU and point the frontend at it:

1. Open the Colab notebook with a **GPU runtime** (Runtime → Change runtime type → GPU)
2. Install dependencies and start uvicorn
3. Start ngrok: `ngrok http 8000` and copy the `https://...ngrok-free.dev` URL
4. In `frontend/.env`:

```
VITE_BACKEND_URL=https://your-ngrok-url.ngrok-free.dev
```

5. Restart `npm run dev` in the frontend.

### 2.6 Troubleshooting GPU

| Problem                          | Fix                                                             |
| -------------------------------- | --------------------------------------------------------------- |
| `CUDA available: False`          | Install the CUDA PyTorch build (2.1) or update your driver      |
| OOM (out of memory)              | Set `WHISPER_USE_GPU=false` or use a smaller Whisper model      |
| Slow first inference              | First run downloads model weights — subsequent runs are cached  |
| Advanced pipeline stays DISABLED  | Confirm `torch.cuda.is_available()` is `True`; check `.env` flag|

---

## 3. Testing & Evaluation

Run from `backend/` with the server up:

```bash
python tests/run_tests.py                                  # unit tests
python tests/test_latency.py                               # latency (voice/TTS)
python tests/test_load.py                                  # load/throughput
python tests/evaluate_rag.py                               # RAG quality (CSV)
python tests/evaluate_ragas.py                             # RAGAS metrics (30 questions)
```

RAGAS metrics: `faithfulness`, `context_recall`, `context_precision`, `answer_correctness`.

---

## 4. Project Structure

```
backend/
  app/
    api/v1/          # REST + WebSocket routers
    pipeline/        # embedding, hybrid search, reranker, LLM, AgentRAG, QueryExpander, HyDE
    services/        # audio (whisper/edge-tts), chat, document, session
    store/           # in-memory sessions, disk file store
  tests/             # evaluation + latency/load suites
  chroma_db/         # vector index (generated at runtime)
frontend/
  src/components/    # AppShell, ChatWindow, ChatInput, RecordButton, uploads, ...
  vite.config.ts     # dev proxy /api + /ws → :8000
docs/                # architecture documentation (PDF)
```

## 5. Security Notes

- API keys live in `backend/.env` and `frontend/.env` (both `.gitignore`d)
- Never commit real keys — use `.env.example` as a template
- Sessions are in-memory and lost on backend restart
