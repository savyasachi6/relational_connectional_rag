# Scalable RAG Architecture Deep Dive

This document details the complete end-to-end architecture of our production-grade RAG pipeline, based heavily on the philosophies outlined in the ByteMonk "Scalable RAG System" architecture.

The core idea is that RAG is the crucial bridge between Large Language Models (LLMs) and internal company documents. While naive RAG systems often fail in production—because poor retrieval can actually make hallucinations worse than providing no context at all—a production-ready architecture ensures systems scale, stay accurate, and work reliably under messy, real-world data.

The architecture is broadly divided into three sides: **Data Ingestion** on the left, **Retrieval and Reasoning** in the middle, and **Evaluation and Stress-Testing** on the right.

---

## 1. Data Restructuring and Structure-Aware Chunking (Ingestion)

*Implemented in: [`src/ingestion/`](../src/ingestion/)*

The ingestion phase is the foundation of retrieval quality. Direct chunking and embedding of raw files leads to failure modes like chunks cut mid-sentence and corrupted tables.

* **[Restructuring Layer](../src/ingestion/parsers.py)**: The first non-trivial step. Raw documents are passed through a parser that explicitly identifies structure. Extracted headings, paragraphs, tables, and code blocks preserve semantic meaning.
* **[Structure-Aware Chunking](../src/ingestion/chunking.py)**: Chunking is performed in a structure-aware way. The system strictly respects natural boundaries—keeping tables intact and headings grouped with their content is prioritized over exact token limits.

## 2. Metadata, Summaries, and Question Generation

*Implemented in: [`src/ingestion/enrichment.py`](../src/ingestion/enrichment.py)*

After chunking, simply storing raw text plus embeddings is insufficient for production.

* **Enrichment**: The system enriches each chunk with additional metadata. This involves running an LLM over the chunk to generate a brief summary and extract core keywords.
* **Hypothetical Question Generation**: Crucially, the system creates hypothetical questions that the chunk could plausibly answer. At retrieval time, matching user questions against pre-generated questions attached to chunks often works significantly better than matching questions directly against arbitrary paragraphs.

## 3. Database and Storage Layer Design

*Implemented in: [`src/db/models.py`](../src/db/models.py)*

In contrast to tutorials that treat a dedicated "vector database" as the only persistent layer, this architecture unifies storage using a database capable of vectors and relational data.

* **PostgreSQL + pgvector**: This architecture utilizes PostgreSQL extended with `pgvector`. This enables combined queries that perform semantic search alongside rich relational filtering (e.g., filtering by date or department) in the exact same SQL call.

## 4. Hybrid Retrieval: Semantic plus Keyword

*Implemented in: [`src/core/retrieval.py`](../src/core/retrieval.py)*

On the query side, production systems rely on hybrid search.

* **The Hybrid Approach**: The system combines semantic (embedding-based) search with traditional keyword or lexical search.
* **Rationale**: Vectors are strong at capturing overall meaning, whereas keyword search excels at exact matches for product names, error codes, or very specific terms that embeddings might otherwise smooth over.
* **Reranking**: Typical implementations retrieve results via both modes and then rerank the combined set to algorithmically choose the absolute most relevant chunks.

## 5. Reasoning Engine and Multi-Agent Orchestration

*Implemented in: [`src/api/rag_api.py`](../src/api/rag_api.py)*

For complex queries, the classic "embed query → retrieve chunks → stuff into prompt → generate answer" flow is handled by a dedicated orchestrator.

* **The Orchestrator**: An API endpoint component interprets what information the query actually needs, executes the `HybridRetriever`, and sequences the draft generation.

## 6. Validation Layer to Reduce Hallucinations

*Implemented in: [`src/validation/validation.py`](../src/validation/validation.py)*

Because more agents and steps increase the chance of failure, a dedicated validation layer acts as a strict firewall before the user payload is returned.

* **The Gatekeeper**: Checks whether the response actually answers the user's specific question.
* **The Auditor**: Verifies that the claims made in the response are strictly grounded in the retrieved context, preventing hallucinated additions.
* **The Strategist**: Evaluates whether the answer makes sense relative to broader constraints and tone (e.g., assessing "risk_profile").

## 7. Evaluation: Qualitative, Quantitative, and Performance

Evaluation runs continuously on the right side of the architecture.

* **Qualitative**: Relies on LLMs acting as judges to score responses for faithfulness to the retrieved context, relevance to the query, and overall thoroughness.
* **Quantitative (Retrieval Metrics)**: Focuses on Precision (of the retrieved chunks, how many were relevant?) and Recall (of all relevant chunks in the corpus, how many did we successfully retrieve?).
* **Performance Monitoring**: Tracks latency, cost, and token usage—crucial considerations at scale.

## 8. Stress Testing and Red Teaming

The architecture actively defends against real-world deployment realities before and during production.

* **Red Teaming**: The system is deliberately attacked with adversarial prompts to probe failure modes. Threat categories include biased outputs, information evasion, and prompt injections that try to override instructions or exfiltrate sensitive data. Understanding how a RAG system breaks is positioned as a mandatory component of responsible deployment.
