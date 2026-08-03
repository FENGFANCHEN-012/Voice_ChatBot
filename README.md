# Enterprise Real-Time Voice RAG ChatBot 🎙️🤖

An enterprise-grade, real-time **Voice Retrieval-Augmented Generation (RAG) Assistant** designed for low-latency, high-accuracy document intelligence and conversational speech interaction.

The system integrates **Faster-Whisper ASR**, **BM25 + BGE-M3 Hybrid Search**, **BGE-Reranker-v2-m3 Cross-Encoder Reranking**, **Dual LLM Engines (DeepSeek-V3 & Google Gemini)**, and **Streaming Edge-TTS Audio Output**.

---

## 🌟 Key Features

* ⚡ **Ultra-Low Spoken Latency (< 2.8s)**: Audio streaming begins out-loud while the LLM is still generating subsequent sentences.
* 🎯 **Hybrid Retrieval (RAG)**: Combines dense vector similarity (`BAAI/bge-m3`) and sparse keyword search (`rank-bm25`) using Reciprocal Rank Fusion (RRF).
* 🔬 **Cross-Encoder Reranking**: Re-ranks top document chunks using `BAAI/bge-reranker-v2-m3` to eliminate hallucinations and maximize precision.
* 🧠 **Dual LLM Provider System (DeepSeek-V3 + Gemini)**:
  * **DeepSeek-V3 (`deepseek-chat`)**: High-throughput streaming via REST API with 128k context window and strict system prompt compliance.
  * **Google Gemini 2.0 / 1.5**: Full multi-modal support.
  * **Zero-Downtime Auto-Failover**: Automatically fails over from Gemini to DeepSeek-V3 if a 429 quota limit occurs.
* 🎙️ **Real-Time Voice Pipeline**:
  * **Speech-to-Text (ASR)**: Uses `faster-whisper` (base/medium models) with PyTorch CUDA GPU acceleration.
  * **Text-to-Speech (TTS)**: Streams MP3 audio chunks via WebSocket (`/ws/tts`) using a strict sequence-locked queue for natural out-loud speech.
  * **TTS Sanitization**: Automatic regex cleaning converts slashes (`/`, `\`) and markdown symbols into natural spoken phrases (e.g. `CI/CD` is spoken as *"C I C D"*).
* ☁️ **Dual Execution Architecture**:
  * **Option 1: Google Colab Cloud GPU Server**: NVIDIA T4 GPU acceleration (~35ms rerank latency).
  * **Option 2: Local CPU Server**: For offline local development.

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
        
        QueryEngine -->|1. Keyword Search| BM25[BM25 Index]
        QueryEngine -->|2. Dense Search| Chroma[ChromaDB Vector Store]
        
        BM25 --> Hybrid[Hybrid Search RRF Fusion\nTop 30 Candidates]
        Chroma --> Hybrid
        
        Hybrid --> Reranker[CrossEncoder Reranker\nBAAI/bge-reranker-v2-m3\n⚡ 35ms on GPU]
        Reranker --> TopDocs[Top 8 Context Chunks]
        
        TopDocs --> LLMEngine[LLM Provider Engine\nDeepSeek-V3 / Gemini 2.0]
        LLMEngine -->|Streaming Tokens| Frontend
    end

    subgraph Audio Output Layer
        WS_Call --> EdgeTTS[Edge-TTS Streamer]
        EdgeTTS -->|MP3 Audio Chunks| Playback[Sequence-Locked Audio Queue]
        Playback -->|Spoken Voice| User
    end
```

---

## 📁 Directory Structure

```text
Voice_ChatBot/
├── backend/
│   ├── app/
│   │   ├── api/v1/            # REST API endpoints (chats, documents, sessions, audio)
│   │   ├── core/              # Custom exceptions & logging
│   │   ├── models/            # Pydantic schemas & domain data models
│   │   ├── pipeline/          # RAG engine (hybrid search, reranker, LLM client, rate limiter)
│   │   ├── services/          # Audio service (ASR, TTS, text cleaning)
│   │   ├── config.py          # Pydantic environment configuration settings
│   │   └── main.py            # FastAPI entry point & lifespan management
│   ├── tests/                 # Benchmark suite (ASR, latency, load test, RAGAS eval)
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/        # React UI components (ChatWindow, Sidebar, AudioVisualizer)
│   │   ├── hooks/             # Custom hooks (useAudioRecorder, useTtsSocket)
│   │   ├── services/          # Axios API & SSE streaming clients
│   │   └── App.tsx            # Main application shell
│   ├── vite.config.ts         # Vite dev server & backend proxy configuration
│   └── package.json           # Frontend dependencies
├── docs/                      # Architecture documentation & diagrams
└── README.md                  # Project documentation
```

---

## ⚙️ Configuration Reference (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` and update your keys:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:5173

# LLM Provider Configuration ("gemini", "deepseek", or "auto")
LLM_PROVIDER=auto

# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL_NAME=deepseek-chat

# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Models & Hardware Acceleration
WHISPER_MODEL_SIZE=base
WHISPER_USE_GPU=True
EMBEDDING_MODEL_NAME=BAAI/bge-m3
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3

# RAG Search Settings
VECTOR_STORE_TYPE=chroma
RETRIEVAL_TOP_K=30
RERANKER_TOP_K=8
```

---

## 🚀 Quick Start Guide

### Prerequisites
* **Python**: `3.10` or higher
* **Node.js**: `18.0` or higher
* **Git**

---

### Step 1: Backend Setup (Local Machine)

```bash
# Navigate to backend directory
cd backend

# Create & activate Python virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI Uvicorn server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will start at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

---

### Step 2: Frontend Setup (Local Machine)

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

Frontend will run at `http://localhost:5173`.

---

## ☁️ Deploying Backend on Google Colab Cloud GPU

To achieve **35ms reranking latency** and **sub-3s voice responses**, deploy the backend on Google Colab T4 GPU:

1. Open [Google Colab](https://colab.research.google.com) and select **Runtime ➔ Change runtime type ➔ T4 GPU**.
2. Run **Cell 1: Environment Setup**:
   ```python
   import os
   %cd /content
   if not os.path.exists('/content/Voice_ChatBot'):
       !git clone https://github.com/FENGFANCHEN-012/Voice_ChatBot.git

   %cd /content/Voice_ChatBot
   !git pull

   !pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 -q
   !pip install -r backend/requirements.txt -q
   !pip install pyngrok rank-bm25 llama-index-embeddings-huggingface -q
   ```
3. Run **Cell 2: Launch Backend Server & Tunnel**:
   ```python
   import os
   from pyngrok import ngrok

   !pkill ngrok
   !pkill uvicorn
   ngrok.kill()

   ngrok.set_auth_token("YOUR_NGROK_TOKEN")
   public_url = ngrok.connect(8000)
   print("🚀 CLOUD GPU BACKEND IS LIVE:", public_url)

   %cd /content/Voice_ChatBot/backend
   !python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. Copy the generated HTTPS ngrok URL and set it in `frontend/.env`:
   ```env
   VITE_BACKEND_URL=https://your-ngrok-url.ngrok-free.dev
   ```
   Or paste it into `frontend/vite.config.ts` under Option 1 proxy target.

---

## 🔀 Strategy & Configuration Switching

### 1. Cloud vs Local Server Switch (`frontend/.env` & `vite.config.ts`)
- **Cloud Backend (Google Colab)**: Set `VITE_BACKEND_URL=https://your-ngrok-url.ngrok-free.dev` in `frontend/.env`.
- **Local Backend**: Set `VITE_BACKEND_URL=http://localhost:8000` in `frontend/.env` (or uncomment Option 2 in `vite.config.ts`).

### 2. Chunking & Vector Store Strategy Switch (`backend/.env`)
- **Vector Store (`VECTOR_STORE_TYPE`)**:
  - `VECTOR_STORE_TYPE=chroma` (Default persistent vector store)
  - `VECTOR_STORE_TYPE=faiss` (Lightweight FAISS fallback)
- **Document Chunking Strategy**:
  - `strategy="semantic"` (Default `LlamaIndex` `SemanticSplitterNodeParser` based on embedding distance)
  - `strategy="recursive"` (`LangChain` `RecursiveCharacterTextSplitter` with chunk size 512, overlap 64)
- **LLM Provider (`LLM_PROVIDER`)**:
  - `LLM_PROVIDER=auto` (Auto failover between Gemini and DeepSeek)
  - `LLM_PROVIDER=gemini` (Google Gemini 3.5 Flash Lite)
  - `LLM_PROVIDER=deepseek` (DeepSeek-V3)

---

## 🧪 Benchmark & Testing Suite

The repository includes automated testing scripts under `backend/tests/`:

| Test Script | Description | Execution Command |
| :--- | :--- | :--- |
| **`test_asr.py`** | Evaluates Whisper Word Error Rate (WER) and Character Error Rate (CER). | `python backend/tests/test_asr.py` |
| **`test_latency.py`** | Measures end-to-end voice query latency and processing breakdown. | `python backend/tests/test_latency.py` |
| **`test_load.py`** | Simulates 1, 5, and 10 concurrent user queries. | `python backend/tests/test_load.py` |
| **`evaluate_ragas.py`** | Runs RAGAS evaluation (Faithfulness, Answer Correctness, Context Recall). | `python backend/tests/evaluate_ragas.py` |
| **`run_tests.py`** | Interactive menu to launch all benchmark suites. | `python backend/tests/run_tests.py` |

---

## 📊 Performance Metrics

| Metric | Target | Cloud GPU (NVIDIA T4) | Local CPU | Status |
| :--- | :--- | :--- | :--- | :--- |
| **BGE-Reranker v2-m3** | - | **35 ms** | 10,200 ms | ⚡ **300x Faster on GPU** |
| **Whisper ASR** | - | **150 ms** | 900 ms | ⚡ **6x Faster on GPU** |
| **End-to-End Voice Latency** | **< 8.0s** | **2.65 seconds** | 14.50 seconds | 🏆 **`[PASS]` on GPU** |
| **TTS Audio Latency** | **< 2.0s** | **1.45 seconds** | 1.52 seconds | 🏆 **`[PASS]`** |

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
