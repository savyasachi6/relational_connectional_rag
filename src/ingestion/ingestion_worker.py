# src/ingestion/ingestion_worker.py
from typing import Iterable, Dict, Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from db import models
from db.session import get_session
from .parsers import parse_document_structure
from .chunking import chunk_structured_doc
from .enrichment import enrich_chunks
from core.llm_client import get_embedding_model

def ingest_document(source_uri: str, mime_type: Optional[str] = None) -> str:
    """
    High-level ingestion entrypoint.

    1. Load and parse the raw document into a structured representation.
    2. Apply structure-aware chunking.
    3. Enrich chunks with summaries, keywords, and hypothetical questions.
    4. Compute embeddings and persist everything into Postgres + pgvector.
    """
    with get_session() as session:
        document_id = _create_document_record(session, source_uri, mime_type)
        
        # 1. Structure Parse
        structured = parse_document_structure(source_uri, mime_type=mime_type)
        
        # 2. Chunk
        raw_chunks = chunk_structured_doc(structured)
        
        # 3. Enrich
        enriched_chunks = enrich_chunks(raw_chunks)

        # 4. Save
        _persist_chunks_and_embeddings(
            session=session,
            document_id=document_id,
            enriched_chunks=enriched_chunks,
        )

    return str(document_id)

def _create_document_record(session: Session, source_uri: str, mime_type: Optional[str]) -> str:
    # Basic upsert logic could check for existing source_uri here to handle versioning
    doc = models.Document(
        id=uuid4(),
        source_uri=source_uri,
        version=1,
        mime_type=mime_type,
    )
    session.add(doc)
    session.flush() # Flush to get the ID for chunks without fully committing
    return doc.id

def _persist_chunks_and_embeddings(
    session: Session,
    document_id,
    enriched_chunks: Iterable[Dict[str, Any]],
) -> None:
    embed_model = get_embedding_model()
    
    previous_chunk_id = None

    for idx, chunk in enumerate(enriched_chunks):
        chunk_id = uuid4()
        
        # Create standard text chunk
        db_chunk = models.Chunk(
            id=chunk_id,
            document_id=document_id,
            ordinal=idx,
            heading=chunk.get("heading"),
            content=chunk["content"],
            summary=chunk.get("summary"),
            hypothetical_questions=chunk.get("questions"),
            keywords=chunk.get("keywords"),
            chunk_metadata=chunk.get("metadata", {}),
        )
        session.add(db_chunk)

        # Calculate dense vector and store in separate embeddings table
        vec = embed_model.embed_text(chunk["content"])
        db_emb = models.ChunkEmbedding(
            chunk_id=chunk_id,
            vector=vec,
        )
        # SQLAlchemy relates via Chunk embedding back_populates
        session.add(db_emb)

        # Create sequential structural relations
        if previous_chunk_id:
            # Forward relation: previous -> current
            rel_forward = models.EntityRelation(
                source_chunk_id=previous_chunk_id,
                target_chunk_id=chunk_id,
                relation_type="next_chunk",
                weight=1.0
            )
            # Backward relation: current -> previous
            rel_backward = models.EntityRelation(
                source_chunk_id=chunk_id,
                target_chunk_id=previous_chunk_id,
                relation_type="prev_chunk",
                weight=1.0
            )
            session.add(rel_forward)
            session.add(rel_backward)
            
        previous_chunk_id = chunk_id

    session.commit()
