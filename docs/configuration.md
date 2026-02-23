# Configuration & Tuning

To ensure the Scalable RAG pipeline operates reliably, various environment variables and configuration parameters must be set. This document outlines the key configurations for the database connection, API authentication, and retrieval constraints.

## Environment Variables

These variables are defined in the `docker-compose.yml` or the `kubernetes/configmap.yaml` and injected into the containers.

### Database Configuration

We use PostgreSQL combined with `pgvector` to unify relational entity data and semantic embeddings.

* `POSTGRES_USER`: The administrative user (e.g., `postgres` or `rag_admin`).
* `POSTGRES_PASSWORD`: The secure password for the database.
* `POSTGRES_DB`: The name of the database (e.g., `rag_knowledge_base`).
* `DB_HOST`: The hostname of the Postgres server (e.g., `postgres` in Docker Compose).
* `DB_PORT`: Standard Postgres port (e.g., `5432`).

*(Note: If utilizing Databricks Neon Serverless Postgres, provide the connection string instead of host/port combinations).*

### External LLM Providers

The Reasoning Engine, Validation Layer, and Ingestion (Summarization & Hypothetical Questions) require LLM API access.

* `OPENAI_API_KEY` (or equivalent provider key): Required for the planner and LLM-as-a-judge nodes.
* `EMBEDDING_MODEL_NAME`: The specific model to use for vectorizing chunks (e.g., `text-embedding-3-small`).

### Core System Tuning (Advanced)

These parameters govern how the system chunks documents and retrieves information.

* **`CHUNK_MIN_TOKENS`**: The minimum allowable size for a structure-aware chunk (e.g., `128`).
* **`CHUNK_MAX_TOKENS`**: The maximum upper limit (e.g., `512`). The pipeline prioritizes structural boundaries (headings, tables) over these exact limits.
* **`CHUNK_OVERLAP`**: The token overlap between adjacent parsed sections (e.g., `50`).
* **`RETRIEVAL_TOP_K`**: The number of semantic vector matches to return (e.g., `10`).
* **`KEYWORD_TOP_K`**: The number of exact lexical matches (BM25) to return (e.g., `10`).
* **`RERANK_FINAL_K`**: The final number of chunks delivered to the reasoning engine after the Cross-Encoder reranks the combined hybrid pool (e.g., `5`).

## Modifying the Configuration

* **Docker Compose**: Directly edit the `.env` file in the root directory alongside your `docker-compose.yml`.
* **Kubernetes**: Modify the `data` section of `kubernetes/configmap.yaml` and reapply:

    ```bash
    kubectl apply -f kubernetes/configmap.yaml
    ```
