# Comprehensive Code Flow Guide

This document traces the exact path a request takes through the Python architecture, making it easy to understand how the decoupled components interact.

---

## Flow 1: Data Ingestion (`/ingest`)

When you `POST` a document (like a PDF URL) to the system, here is how it is processed and vectorized.

1. **The Entry Point:** [`src/api/rag_api.py`](../src/api/rag_api.py#L17)
   * The FastAPI `/ingest` route receives an `IngestRequest` containing the document URL and metadata.
   * Instead of making the user wait, it instantly returns a `202 Accepted` response.
   * It quietly passes the job to `BackgroundTasks`, which spins up the `ingestion_worker`.

2. **The Worker Loop:** [`src/ingestion/ingestion_worker.py`](../src/ingestion/ingestion_worker.py#L9)
   * The worker picks up the URL and initiates a database session.
   * It creates a "Document" record in PostgreSQL to track this file permanently.

3. **Parsing the Structure:** [`src/ingestion/parsers.py`](../src/ingestion/parsers.py#L4)
   * The worker passes the URL to `parse_document_structure()`.
   * *In a production setup*, this uses Unstructured.io or LlamaParse to extract the raw text, tables, and headers.
   * *In our blueprint*, it returns mock "structured elements."

4. **Structure-Aware Chunking:** [`src/ingestion/chunking.py`](../src/ingestion/chunking.py#L4)
   * The structured elements are passed to `chunk_structured_doc()`.
   * This logic splits the document into smaller pieces (chunks), ensuring that it doesn't break a paragraph or table exactly in half, maintaining semantic meaning.

5. **LLM Enrichment:** [`src/ingestion/enrichment.py`](../src/ingestion/enrichment.py#L37)
   * Before saving, the chunks are passed to `enrich_chunks()`.
   * This contacts the OpenAI API (or the `MockLLM`) to generate a 1-sentence summary, keywords, and hypothetical questions for *each* chunk. This dramatically improves future retrieval.

6. **Database Persistence:** [`src/db/models.py`](../src/db/models.py#L22)
   * Finally, the original chunks, their metadata, and their 1536-dimensional embeddings (vectors) are saved to the `Chunk` and `ChunkEmbedding` PostgreSQL tables using SQLAlchemy.

---

## Flow 2: Reasoning & Retrieval (`/ask`)

When a user asks a question, the system must securely retrieve the right data, generate an answer, and validate it.

1. **The Entry Point:** [`src/api/rag_api.py`](../src/api/rag_api.py#L36)
   * The `/ask` route receives the user's question, maximum chunk count (`top_k`), and strictness level (`risk_profile`).

2. **Hybrid Retrieval:** [`src/core/retrieval.py`](../src/core/retrieval.py#L21)
   * The API instantiates the `HybridRetriever`.
   * It first translates the user's question into a 1536-dimensional embedding using the LLM Embedding generation.
   * It executes a powerful SQL query (`_semantic_search`) using `pgvector`'s `<=>` operator (Cosine Distance).
   * It filters the exact same chunks based on relational metadata (e.g., `WHERE department = 'HR'`).
   * It returns the top `K` most relevant Chunks.

3. **Generating the Draft Answer:** [`src/api/rag_api.py`](../src/api/rag_api.py#L85)
   * The API takes the text from all the retrieved chunks and glues them into a single string.
   * It passes this massive context block and the user's question to the LLM (Reasoning Engine) to draft an honest answer.

4. **The Validation Pipeline:** [`src/validation/validation.py`](../src/validation/validation.py#L11)
   * *Crucial Step*: AI generated text is inherently untrustworthy. The draft answer is passed into the validation pipeline.
   * **Gatekeeper:** Checks if the draft actually answered the question or if it was evasive.
   * **Auditor:** Checks if the draft makes claims that *aren't* physically present in the retrieved chunks (Hallucination checking).
   * **Strategist:** Looks at the user's `risk_profile` (e.g., "low"). If the risk profile is low and the auditor flagged *any* hallucination, the strategist rewrites the answer to be aggressively safe (e.g., "I don't know the answer with certainty").

5. **Final Output Response:**
   * The API returns the `AskResponse` JSON, containing the safe final answer, the detailed validation reports, and the exact chunks (citations) used to generate the answer.
