# Scalable RAG System Architecture

Welcome to the Scalable RAG (Retrieval-Augmented Generation) System Architecture repository. This project provides a production-grade blueprint for deploying AI applications that bridge Large Language Models (LLMs) with private organizational data.

Based on the ByteMonk architecture overview, this repository moves beyond naive "toy demo" RAG pipelines. It implements a robust, 6-layer architecture designed for scalability, accuracy, and reliability in real-world environments.

## Core Design Philosophy

Naive RAG often fails in production because "bad retrieval is worse than no retrieval." When document structure is lost, tables are corrupted, or the wrong semantic chunks are retrieved, the LLM hallucinates with high confidence.

This architecture solves these problems through:

1. **Structure-Aware Ingestion**: Preserving headings, lists, tables, and document hierarchies.
2. **Relational & Vector Unification**: Using Postgres with `pgvector` to store embeddings alongside rich metadata, enabling hybrid SQL/Semantic search.
3. **Agentic Reasoning**: Going beyond "embed -> stuff prompt", using multi-agent planners to interpret complex queries.
4. **Validation Engineering**: Dedicated Gatekeeper, Auditor, and Strategist roles to screen responses before they reach the user.

## The Codebase & Modular Architecture

The Python backend implementation (`src/`) explicitly realizes this architectural philosophy.

* **[`src/db/models.py`](src/db/models.py)**: The single source of truth for database schema. Houses normalized tables for `Document` versions, `Chunk` metadata, and `ChunkEmbedding` (using `pgvector`).
* **[`src/ingestion/ingestion_worker.py`](src/ingestion/ingestion_worker.py)**: The ingestion pipeline. Handles [Parsing](src/ingestion/parsers.py), [Structure-Aware Chunking](src/ingestion/chunking.py), and [LLM Enrichment](src/ingestion/enrichment.py).
* **[`src/core/retrieval.py`](src/core/retrieval.py)**: The `HybridRetriever` cleanly abstracts Postgres `<=>` vector distance querying and keyword filtering away from the Language Model.
* **[`src/validation/validation.py`](src/validation/validation.py)**: The explicit safety layer. Implements the Gatekeeper, Auditor, and Strategist validators before returning the final user payload.
* **[`src/api/rag_api.py`](src/api/rag_api.py)**: The primary FastAPI reasoning orchestration module that ties retrieval, LLM generation, and validation together.

## Quick Start

For local development and testing, you can spin up the entire cluster using Docker Compose:

```bash
docker-compose up --build -d
```

This will launch:

* **PostgreSQL (pgvector)**: The foundational database unifying relational data and vector embeddings.
* **Reasoning API**: The component handling user queries, hybrid search, and multi-agent coordination.
* **Ingestion Worker**: The background processor that restructures incoming documents and generates metadata.

## 📚 Documentation

For complete details on configuring, deploying, and understanding the system, refer to the `docs/` folder:

* **[Architecture Deep Dive](docs/architecture.md)**
* **[Unified Database Guide](docs/database.md)**
* **[Docker Execution & Build](docs/docker-execution.md)**
* **[Installation Guide](docs/installation.md)**
* **[Configuration Options](docs/configuration.md)**
