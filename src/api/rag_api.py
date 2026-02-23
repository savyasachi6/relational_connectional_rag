# src/api/rag_api.py
from fastapi import FastAPI, Depends, BackgroundTasks

from core.schemas import AskRequest, AskResponse, IngestRequest, IngestResponse
from core.llm_client import LLMClient, get_llm_client
from core.retrieval import HybridRetriever, get_retriever
from validation import run_validation_pipeline
from core.config import settings

# This import assumes chunking.py and parsing.py are properly handling the background logic
from ingestion.ingestion_worker import ingest_document

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# --- Routes ---

@app.post("/ingest", response_model=IngestResponse, status_code=202)
async def api_ingest(
    payload: IngestRequest,
    background_tasks: BackgroundTasks
):
    """
    Accepts a document reference and enqueues the processing pipeline in the background.
    """
    # In a real environment, this spins off to a message queue (Celery/RabbitMQ).
    # We use FastAPI BackgroundTasks here for the blueprint demonstration.
    background_tasks.add_task(ingest_document, source_uri=payload.source_uri, mime_type=payload.mime_type)
    
    return IngestResponse(
        document_id="pending", # The real ID generates asynchronously
        status="accepted",
        message=f"Ingestion queued for {payload.source_uri}"
    )


@app.post("/ask", response_model=AskResponse)
async def api_ask_question(
    payload: AskRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    llm: LLMClient = Depends(get_llm_client),
):
    """
    Primary orchestrator for answering business queries reliably.
    
    1. Retrieve candidate chunks via hybrid search (keyword + semantic + metadata filter).
    2. Reasoning Engine drafts a tentative answer.
    3. Pass draft answer through Gatekeeper, Auditor, and Strategist policies.
    4. Return the safe/validated answer and the citations used.
    """
    # 1. Hybrid Retrieval based on the pgvector `<=>` operators and full-text search
    retrieved = await retriever.retrieve(
        query=payload.query,
        filters=payload.filters,
        top_k=payload.top_k or settings.DEFAULT_TOP_K,
    )

    # 2. Draft initial generation (Reasoning / Planner Engine)
    draft_answer = await _generate_draft_answer(
        llm=llm,
        query=payload.query,
        retrieved_chunks=retrieved,
    )

    # 3. Validation Safety Layer
    final_answer, validation_report = await run_validation_pipeline(
        llm=llm,
        query=payload.query,
        draft_answer=draft_answer,
        retrieved_chunks=retrieved,
        risk_profile=payload.risk_profile,
    )

    # 4. Construct response with citation traceability
    return AskResponse(
        answer=final_answer,
        validation=validation_report,
        retrieved_chunks=[{
            "id": c.id, 
            "content": c.content, 
            "metadata": c.metadata, 
            "score": c.score
        } for c in retrieved]
    )

async def _generate_draft_answer(llm: LLMClient, query: str, retrieved_chunks: list):
    """
    The reasoning engine's primary generation loop.
    In complex configurations, this involves LangGraph loops or tool execution.
    """
    context = "\n\n---\n\n".join(c.content for c in retrieved_chunks)
    prompt = f"""You are an advanced domain expert AI.
Use ONLY the following context to answer. If the context does not contain the answer, say "I cannot answer reliably based on the available data."

Context:
{context}

Question: {query}
Answer:"""
    return await llm.complete(prompt)


@app.get("/health")
def health_check():
    """Liveness probe for Kubernetes deployment"""
    return {"status": "healthy", "version": settings.VERSION}
