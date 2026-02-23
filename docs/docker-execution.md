# Docker Execution and Build Guide

This document explains how the containerized deployment of the Scalable RAG Architecture is structured, how to build it, and how to execute the services.

## Architecture Overview

The application is deployed using `docker-compose.yml`, which orchestrates three primary services:

1. **`postgres-pgvector`**: The foundational database unifying relational data and vector embeddings. It uses the `ankane/pgvector:latest` image.
2. **`api-service`**: The FastAPI application that handles reasoning, retrieval (hybrid search), and the validation layers. Built from `docker/Dockerfile.api`.
3. **`ingestion-worker`**: The background worker that handles structure-aware chunking and enrichment of new documents. Built from `docker/Dockerfile.ingestion`.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) must be installed and running.
- An OpenAI API Key (or equivalent LLM provider key) set in your environment or a `.env` file.

## Build and Execution Commands

### 1. Build and Start All Services

To build the images and start the entire stack in detached mode (in the background):

```bash
docker-compose up --build -d
```

- `--build`: Forces Docker to rebuild the images using the `Dockerfile.api` and `Dockerfile.ingestion` files in case you made code changes.
- `-d`: Runs the containers in detached mode, returning your terminal prompt.

### 2. Viewing Logs

To see what the services are doing (especially useful for the ingestion worker or debugging API errors):

```bash
# View logs for all services, following the output
docker-compose logs -f

# View logs for just the API service
docker-compose logs -f api-service

# View logs for just the Ingestion Worker
docker-compose logs -f ingestion-worker

# View database logs
docker-compose logs -f postgres-pgvector
```

### 3. Stopping the Services

To stop the running containers without completely removing them:

```bash
docker-compose stop
```

### 4. Tearing Down the Stack

To stop the containers and remove the created networks. Note: Data stored in the Postgres named volume (`pgdata`) will persist across teardowns.

```bash
docker-compose down
```

To completely wipe the database and start fresh, you must remove the volume as well:

```bash
docker-compose down -v
```

## How the Build Works (Under the Hood)

Both custom services (`api-service` and `ingestion-worker`) use a similar build strategy defined in their respective Dockerfiles:

1. **Base Image**: `python:3.11-slim` for a balance of small size and ease of compilation.
2. **System Dependencies**: `apt-get` installs required C-compilers and PostgreSQL development headers (`libpq-dev`), plus poppler/tesseract for the ingestion worker's document parsing capabilities.
3. **Python Dependencies**: Copies the specific requirements file (e.g., `docker/requirements.api.txt`) and runs `pip install`.
4. **Source Code**: The entire `src/` directory is copied into `/app/src`, and the `PYTHONPATH` is updated so Python can correctly resolve module imports (e.g., `from core.llm_client import ...`).
5. **Execution**:
    - The API service uses `CMD ["python", "src/main.py"]` to launch Uvicorn.
    - The Ingestion Worker is currently set to a mock wait loop (`import time; time.sleep(86400)`). In a full production environment, this would be swapped to launch a Celery worker: `CMD ["celery", "-A", "src.worker.tasks", "worker", "--loglevel=info"]`.

## Environment Variables

The `docker-compose.yml` dynamically pulls environment variables from your host machine or a `.env` file in the root directory.

Critical variables include:

- `OPENAI_API_KEY`: Required by both the API and Ingestion services for embeddings and generation.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Passed to both the database container (to initialize the DB) and the application containers (to connect to it). default: `postgres` / `postgres` / `rag_knowledge_base`.
