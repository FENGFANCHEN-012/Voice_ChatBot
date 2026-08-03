# Latency Test Strategy

## Purpose

Measure end-to-end latency of the Voice RAG Assistant across text queries, voice queries, and TTS. Identify bottlenecks and verify performance targets.

## Performance Targets

- Text query P95: < 5s
- Voice query P95: < 8s
- TTS average: < 2s

## Test Environment

| Item | Value |
|------|-------|
| Server | localhost:8000 |
| LLM | gemini-3.5-flash-lite (15 RPM free tier) |
| Vector store | ChromaDB |
| Reranker | BGE Reranker v2 (CPU) |
| ASR | faster-whisper base (CPU) |
| TTS | edge-tts (network) |
| Document | V9 "Global Enterprise Operations & Troubleshooting Policy" |

---

## Test Questions (10)

All questions are verified against the actual V9 document content. They cover the 8 test categories (simple fact, procedure, form, cross-chapter, error code, technical jargon, out-of-scope, follow-up).

### 1. Simple Fact Queries

**Query 1**
- Question: What is the mandatory procedure when an employee experiences an SSO lockout error (Error Code ERR-SSO-4039)?
- Expected source: Chapter 1 (Q1.1)
- Answer should contain: "ERR-SSO-4039", "time sync", "15 minutes", "P3-IDENTITY"
- Testing goal: Baseline latency for a factual lookup with a specific error code.

**Query 2**
- Question: What is the server room temperature alert threshold?
- Expected source: Chapter 4 (Q4.2)
- Answer should contain: "ALARM-TEMP-28C", "28 degrees", "CRAC"
- Testing goal: Latency for numeric data extraction.

### 2. Procedure Queries

**Query 3**
- Question: My VPN keeps disconnecting every 10 minutes while working remotely. What should I do?
- Expected source: Chapter 2 (Q2.1)
- Answer should contain: "IPsec", "SSL/TLS", "MTU", "1360", "Port 443"
- Testing goal: Latency for step-by-step procedural answers.

**Query 4**
- Question: What is the troubleshooting workflow when a CI/CD pipeline fails during database migration with Error LARAVEL-MIGRATE-FAIL?
- Expected source: Chapter 6 (Q6.1)
- Answer should contain: "LARAVEL-MIGRATE-FAIL", "migrate:rollback", "staging", "ON DELETE CASCADE"
- Testing goal: Latency for complex procedural explanations with an error code (longest expected output).

### 3. Form Queries

**Query 5**
- Question: How should project leads handle vendor shipments delivered with damaged packaging or missing Certificates of Analysis (CoA)?
- Expected source: Chapter 5 (Q5.2)
- Answer should contain: "PROC-REJ-88", "Goods Rejection Notice", "48 hours", "CoA"
- Testing goal: Latency for code + form lookup.

**Query 6**
- Question: What happens if an employee submits a corporate travel expense claim without itemized receipts?
- Expected source: Chapter 8 (Q8.1)
- Answer should contain: "EXP-NO-RECEIPT", "FIN-EXP-05", "$25", "Affidavit"
- Testing goal: Latency for form-purpose identification with flags.

### 4. Cross-Chapter Query

**Query 7**
- Question: If an SSO lockout is linked to a cross-border data access violation, which secondary chapter policy applies?
- Expected source: Chapter 1 + 7 (Q1.5)
- Answer should contain: "Chapter 7", "BREACH-DATA-XBORDER-01", "cross-border"
- Testing goal: Latency when retrieval must span multiple chapters (identity + privacy).

### 5. Technical Jargon Query

**Query 8**
- Question: What is the IPSec MTU issue and how is it fixed?
- Expected source: Chapter 2 (Q2.1)
- Answer should contain: "IPsec", "MTU", "1500", "1360", "Keep-Alive"
- Testing goal: Latency for technical abbreviations requiring expansion.

### 6. Out-of-Scope Query

**Query 9**
- Question: What is the meaning of life?
- Expected source: N/A (out of scope)
- Answer should contain: "cannot find"
- Testing goal: Latency for graceful out-of-scope handling; should be fast, no retrieval.

### 7. Follow-Up Query (Multi-turn)

**Query 10**
- Question: (after Query 1) What happens if the SSO lockout is unresolved after 15 minutes?
- Expected source: Chapter 1 (from history)
- Answer should contain: "P3-IDENTITY", "ticket", "15 minutes"
- Testing goal: Latency for follow-up using session history context.

---

## Execution Plan

### Phase 1: Baseline (Text Queries)
- Run queries 1-10 as text.
- 30s delay between queries (avoid Gemini 15 RPM limit).
- Record: latency, TTS latency, chunks returned, error status.

### Phase 2: Voice Queries
- Run queries 1-10 as voice (transcribe then query).
- 30s delay between queries.
- Record: ASR time, query latency, TTS latency.

### Phase 3: Multi-turn
- Run query 10 as a follow-up in the same session (after Query 1).
- Verify history is used (compare against a fresh session).

### Phase 4: Cross-Chapter Focus
- Run query 7 multiple times.
- Verify both chapters appear in the retrieved chunks.

---

## Metrics to Capture

For each query:
1. Total latency (end-to-end)
2. TTS latency (speech synthesis)
3. Chunks returned (retrieval recall indicator)
4. Error status (timeout, rate limit, HTTP error)
5. Answer length (output tokens)

## Success Criteria

- P95 text latency < 5s (excluding first query cold start)
- P95 voice latency < 8s (excluding first query cold start)
- TTS avg < 2s
- 100% success rate (no timeouts)
- 100% of queries return relevant chunks (chunks > 0)
- Out-of-scope queries return gracefully without retrieval delay

---

## Expected Bottlenecks

| Stage | Expected Time | Bottleneck |
|-------|---------------|------------|
| Retrieval (BM25 + vector) | 0.5-1s | CPU-bound BM25 on 500+ chunks |
| Reranking (CrossEncoder) | 1-2s | CPU-bound BGE Reranker v2 |
| LLM generation (Gemini) | 2-5s | Network + Gemini 15 RPM free tier |
| ASR (Whisper base) | 1-2s | CPU-bound int8 inference |
| TTS (edge-tts) | 1.5-2.5s | Network to Microsoft servers |

## Notes

- First query after startup is slow (cold start: BM25 rebuild + model loading) — exclude from stats.
- Gemini free tier caps at 15 RPM — use 30s delay between queries in tests.
- Cross-chapter queries (7-9) test whether the reranker correctly surfaces chunks from multiple chapters.
- Error code/form queries (10-14) are the hardest for retrieval — they test exact-match precision.
- All questions verified against V9 document. Follow-ups (19-20) depend on prior answers in the same session.
