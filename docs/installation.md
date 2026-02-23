# Installation & Deployment Guide

This guide covers the manual software requirements, manual installation links, and deployment strategies using Docker Compose and Kubernetes for the Scalable RAG System.

## The Database

As defined in the architecture, we use a database capable of both vector search and relational operations. **We use PostgreSQL augmented with the `pgvector` extension.** The architecture specifically references serverless Postgres (like Databricks Neon) for its ability to scale to zero and spin up in milliseconds for bursty agentic workloads, but a standard local Postgres instance with `pgvector` is entirely sufficient for deployment.

---

## Part 1: Manual Software Installations

If you are developing locally without Docker, or managing the host machines directly, you must install the following core software:

### 1. PostgreSQL & pgvector

The unified storage layer.

* **PostgreSQL**: Download the core relational database.
  * [Download PostgreSQL](https://www.postgresql.org/download/)
* **pgvector**: The extension that adds vector similarity search capabilities.
  * [pgvector GitHub / Installation Instructions](https://github.com/pgvector/pgvector#installation)

### 2. Python Environment

The reasoning engine, multi-agent orchestration, and data restructuring logic run on Python.

* **Python 3.10+**:
  * [Download Python](https://www.python.org/downloads/)
* **Package Management**: Ensure `pip` is available. We recommend using internal virtual environments (`python -m venv venv`).

### 3. Containerization & Orchestration Tools

Required if you intend to deploy the predefined architecture configurations rather than running raw Python scripts.

* **Docker Desktop** (Contains Docker Engine and Docker Compose):
  * [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
* **Kubernetes (kubectl)**: The command-line tool for controlling Kubernetes clusters.
  * [Download kubectl](https://kubernetes.io/docs/tasks/tools/)
* **Minikube** (Optional): A local Kubernetes cluster for testing manifests.
  * [Download Minikube](https://minikube.sigs.k8s.io/docs/start/)

---

## Part 2: Containerized Local Deployment (Docker Compose)

The easiest way to stand up the entire architecture—bypassing manual Postgres/pgvector installation—is via Docker Compose. This deployment includes:

1. **PostgreSQL (with pgvector)**: The foundational unified storage database.
2. **Ingestion Worker**: The background processor for structure-aware chunking and question generation.
3. **API Service**: The reasoning engine and validation layer.

### Steps

1. **Clone the Repository**:

    ```bash
    git clone <repository_url>
    cd scalable-rag-architecture
    ```

2. **Environment Variables**:
    Create a `.env` file in the root directory. Refer to `docs/configuration.md` for required API keys.

    ```bash
    cp .env.example .env
    ```

3. **Build and Run**:

    ```bash
    docker-compose up --build -d
    ```

4. **Verify Services**:

    ```bash
    docker-compose ps
    ```

    You should see `postgres-pgvector`, `api-service`, and `ingestion-worker` running.

5. **Tear Down**:

    ```bash
    docker-compose down -v
    ```

---

## Part 3: Production Deployment (Kubernetes)

For scalable production deployments, we use Kubernetes to orchestrate the validation layers, agentic workers, and hybrid retrieval databases.

### Architecture Components in k8s

- `postgres-statefulset.yaml`: Ensures persistent, reliable document and vector storage.
* `ingestion-deployment.yaml`: Manages the background worker queues.
* `api-deployment.yaml`: Exposes the Reasoning and Retrieval API.
* `configmap.yaml`: Centralized configuration.

### Steps

1. **Start your cluster** (e.g., using Minikube locally or connecting to an external cloud provider):

    ```bash
    minikube start
    ```

2. **Apply Configuration**:
    Ensure the environment variables in `kubernetes/configmap.yaml` are correct for your environment.

    ```bash
    kubectl apply -f kubernetes/configmap.yaml
    ```

3. **Deploy the Database**:

    ```bash
    kubectl apply -f kubernetes/postgres-statefulset.yaml
    ```

    Wait for the database pod to reach `Running` state before proceeding.

4. **Deploy the API and Ingestion Services**:

    ```bash
    kubectl apply -f kubernetes/ingestion-deployment.yaml
    kubectl apply -f kubernetes/api-deployment.yaml
    ```

5. **Access the API**:
    If using minikube, get the service URL:

    ```bash
    minikube service rag-api-service
    ```
