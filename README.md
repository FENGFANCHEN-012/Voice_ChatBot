# Voice RAG ChatBot

Upload a PDF, then ask questions about it by voice. The app transcribes your question, finds the
relevant parts of the document, has an LLM answer from those parts only, and speaks the answer back
while it is still being written.

I built this in about a week (28 Jul – 4 Aug 2026) as a take-home assessment for an AI Builder
internship. The test document was an enterprise IT troubleshooting and policy manual full of error codes,
thresholds and procedures — the kind of thing staff would rather ask than search.

## What it does

- **Document upload** — drag in a PDF; it is parsed, split into chunks, embedded and indexed.
  Progress is streamed to the UI while embedding runs in the background.
- **Voice or text questions** — record with the mic or type. Answers stream in token by token.
- **Spoken answers with low delay** — the frontend cuts the streamed answer into sentences and sends
  each one for speech as soon as it's complete, so audio starts before the full answer is finished.
- **Answers grounded in the document** — each answer comes with the chunks and page numbers it used.
- **Chat sessions** — create, rename and delete conversations; follow-up questions use the history.
- **Runs on CPU or GPU** — everything detects CUDA and falls back to CPU. On a GPU it also turns on
  extra query analysis (see below). I ran the GPU version on Google Colab and exposed it with ngrok.

## How a question is answered

```
mic (webm) ──► POST /audio/transcribe ──► faster-whisper (VAD on, beam 1)
                                               │ text
                                               ▼
                         POST /chats/query/stream (Server-Sent Events)
                                               │
                     query cache hit? ── yes ──► return cached answer
                                               │ no
               ┌───────────── GPU only ────────┴──────── CPU ─────────────┐
               │ AgentRAG: classify query                                  │
               │   (fact / reasoning / comparison / summary / off-topic)   │
               │ QueryExpander: rewrite into sub-queries                   │
               └───────────────────────────┬──────────────────────────────┘
                                           ▼
             Hybrid search per query:  BGE-M3 vectors (ChromaDB)  +  BM25 keywords
                                       merged with Reciprocal Rank Fusion
                                           ▼
                        BGE-reranker-v2-m3 cross-encoder → top 15 chunks
                                           ▼
                  DeepSeek-V3 (primary) or Gemini (fallback) streams the answer
                                           ▼
  frontend splits into sentences ──► WebSocket /ws/tts ──► Kokoro (GPU) or Edge TTS (CPU)
                                           ▼
                         ordered playback queue in the browser
```

Before searching, the query is normalised (abbreviations expanded, error codes and chapter hints
pulled out) so that exact strings like `ERR-SSO-4039` still match.

## Tech stack

| Layer | Tools |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Axios, MediaRecorder + Web Audio API |
| Backend | Python, FastAPI, Uvicorn, Pydantic Settings, Loguru, SSE and WebSockets |
| PDF parsing | PyMuPDF, LangChain `RecursiveCharacterTextSplitter` (800 chars, 150 overlap), optional LlamaIndex semantic splitter |
| Embeddings | `BAAI/bge-m3` via sentence-transformers |
| Vector store | ChromaDB (FAISS also supported) |
| Keyword search | `rank-bm25` |
| Reranker | `BAAI/bge-reranker-v2-m3` cross-encoder |
| LLM | DeepSeek-V3 (`deepseek-chat`) over its REST API; Google Gemini with model fallback on quota errors |
| Speech to text | faster-whisper (`base`), CUDA float16 or CPU int8 |
| Text to speech | Kokoro on GPU, Edge TTS on CPU, with an in-memory audio cache |
| Evaluation | RAGAS, custom latency / load / ASR test scripts |
| Deployment | Docker Compose for local, Google Colab + ngrok for GPU |

## Results

All numbers come from my own test runs, saved as JSON in this repo.

**Answer quality — RAGAS, 30 test questions** (`ragas_results_20260804_203612.json`)

| Metric | Score |
| --- | --- |
| Faithfulness | 0.90 |
| Context precision | 0.55 |
| Context recall | 0.41 |
| Answer correctness | 0.27 |

Faithfulness is high: the model rarely makes things up and sticks to what it's given. The weak point
is retrieval. Recall of 0.41 means the right chunk often isn't in the context at all, and it's worst
on comparison and multi-hop questions, where the answer is spread across chapters.

**Latency** (`backend/tests/latency_results(*).json`)

| | Voice question → answer (median) | p95 | TTS per sentence (avg) |
| --- | --- | --- | --- |
| GPU (Colab) | 2.7 s | 7.4 s | 1.8 s |
| CPU (laptop) | 4.0 s | 4.2 s | 1.4 s |

Targets were p95 under 8 s for voice and under 2 s average for TTS, and both runs met them.
The GPU run has a longer tail, most likely from the extra classification and expansion LLM calls it makes.

**Speech recognition — 30 test clips** (`backend/tests/asr_results_*.json`)

Keyword accuracy 90%, character error rate 9.5%, word error rate 38%, about 2.3 s per clip.

## Running it

Needs Python 3.11+, Node 18+, and a DeepSeek or Gemini API key.

```bash
# backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp; then add your API key
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

A `docker-compose.yml` is included too, but I haven't re-tested it since the GPU/Colab changes.

The first start downloads the embedding, reranker and Whisper models, so give it a few minutes.
For a GPU, install the CUDA build of PyTorch
(`pip install torch --index-url https://download.pytorch.org/whl/cu121`); the app picks it up by itself.

Main settings in `backend/.env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `LLM_PROVIDER` | `deepseek` | `deepseek`, `gemini` or `auto` |
| `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` | — | at least one is needed |
| `VECTOR_STORE_TYPE` | `chroma` | `chroma` or `faiss` |
| `WHISPER_MODEL_SIZE` | `base` | any faster-whisper size |
| `TTS_PROVIDER` | `auto` | `auto` (Kokoro if CUDA), `kokoro` or `edge` |
| `USE_ADVANCED_PIPELINE` | `true` | query classification + expansion, GPU only |

To use a Colab backend, set `VITE_BACKEND_URL` in `frontend/.env` to your ngrok URL.

Tests and evaluation, from `backend/` with the server running:

```bash
python tests/run_tests.py
python tests/test_latency.py
python tests/test_load.py
python tests/test_asr.py
python tests/evaluate_ragas.py
```

## Project layout

```
backend/app/
  api/v1/      REST routes: documents, chats (incl. streaming), sessions, audio, health
  pipeline/    pdf_parser, embedder, vector_store, hybrid_search, reranker, llm,
               agent_rag, query_expander, query_normalizer, hyde, query_cache, tts_engine
  services/    document, chat, session and audio services
  store/       session and file storage
backend/tests/ latency, load, ASR and RAGAS evaluation + datasets and results
frontend/src/  React components, hooks (recorder, TTS socket, sessions), API client
docs/          architecture, design flow and development workflow write-ups (PDF)
colab_backend.ipynb, GPU_testing_Final.ipynb   running and testing on Colab GPU
```

More detail is in [ARCHITECTURE.md](ARCHITECTURE.md) and [docs/Voice_RAG_Architecture_v2.2.pdf](docs/Voice_RAG_Architecture_v2.2.pdf).

## What I learned

- **Measure retrieval and generation separately.** A single "is the answer right" score hides where
  things go wrong. RAGAS showed faithfulness at 0.90 but context recall at 0.41, which told me to work
  on search and chunking, not on the prompt.
- **Vector search alone misses exact terms.** Embeddings are good at meaning but blur strings like
  error codes and temperature thresholds. Adding BM25 and merging the two lists with Reciprocal Rank
  Fusion covers both, without having to tune weights between two different score scales.
- **A reranker is worth its cost, but it is the slow step on CPU.** Scoring each query–chunk pair with
  a cross-encoder is much more precise than vector distance, and it's the main reason the GPU version
  is faster.
- **Every extra LLM call adds latency.** Query classification and expansion help with comparison
  questions, but they add round trips, so I only switch them on when there's a GPU to make up the time.
- **Perceived speed is about when audio starts.** If the bot waits for the whole answer before
  speaking, the user sits in silence for the full generation time. Streaming tokens, cutting sentences on the frontend and
  synthesising each one right away gets audio playing early, but sentences can finish synthesising out
  of order, so playback needs a sequence queue.
- **Free API tiers shape the design.** Gemini's free tier allows 15 requests a minute, so there's a
  rate limiter, automatic fallback to other Gemini models on quota errors, a query cache, and DeepSeek
  as the main provider.
- **Pick metrics that match the use.** Word error rate for ASR looked bad at 38%, but WER punishes every
  small wording difference. What matters here is whether the important terms survive, and keyword
  accuracy (90%) says more about whether the search will still find the right section.
- **You don't need to own a GPU to test on one.** Colab plus ngrok let me run the full backend on a GPU
  and point my local frontend at it.

## Limitations

- Sessions and the query cache live in memory and reset when the backend restarts.
- Retrieval on multi-part and comparison questions is still weak (see recall above).
- Built and tested around one document; large multi-document collections weren't tested.
