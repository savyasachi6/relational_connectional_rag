# src/core/retrieval.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from db.session import get_session
from db.models import Chunk, ChunkEmbedding, Document

class RetrievedChunk:
    """Standardized DTO for items coming out of hybrid search regardless of method."""
    def __init__(self, id: str, content: str, score: float, metadata: Dict[str, Any]):
        self.id = id
        self.content = content
        self.score = score
        self.metadata = metadata


class HybridRetriever:
    """
    Abstracts dual semantic/lexical queries away from the reasoning engine.
    Ensures LLMs never write RAW sql logic.
    """
    def __init__(self, embed_model, session_factory=get_session, top_k: int = 8):
        self._session_factory = session_factory
        self._embed_model = embed_model
        self._top_k = top_k

    async def retrieve(self, query: str, filters: Optional[dict] = None, top_k: Optional[int] = None) -> List[RetrievedChunk]:
        k = top_k or self._top_k
        query_vector = self._embed_model.embed_text(query)

        with self._session_factory() as session:
            semantic = self._semantic_search(session, query, query_vector, filters, k)
            lexical = self._keyword_search(session, query, filters, k)
            final_set = self._merge_and_rerank(semantic, lexical, k)
            
            return final_set

    def _semantic_search(self, session: Session, query: str, query_vector: List[float], filters: Optional[dict], top_k: int) -> List[RetrievedChunk]:
        # Using pgvector's cosine distance operator `<=>`
        stmt = (
            select(Chunk, ChunkEmbedding.vector.cosine_distance(query_vector).label('distance'))
            .join(ChunkEmbedding)
            .join(Document)
            .order_by('distance')
            .limit(top_k)
        )
        
        # Apply standard relational filtering (e.g., department, file versions) if provided
        if filters:
            pass # Expandable to check `Chunk.metadata` using `->>` JSONB operators
            
        results = session.execute(stmt).all()
        # Convert distances back to similarity scores (1 - distance)
        return [RetrievedChunk(
            id=str(row.Chunk.id),
            content=row.Chunk.content,
            score=1.0 - float(row.distance),
            metadata={"type": "semantic", "heading": row.Chunk.heading, "source": row.Chunk.document.source_uri}
        ) for row in results]

    def _keyword_search(self, session: Session, query: str, filters: Optional[dict], top_k: int) -> List[RetrievedChunk]:
        # Placeholder for Postgres Full-Text Search (tsvector/tsquery)
        # Using simple pattern matching for the structural blueprint
        stmt = select(Chunk).join(Document).where(Chunk.content.ilike(f"%{query}%")).limit(top_k)
        results = session.execute(stmt).all()
        
        return [RetrievedChunk(
            id=str(chunk[0].id),
            content=chunk[0].content,
            score=0.8, # Mock lexical score
            metadata={"type": "keyword", "heading": chunk[0].heading, "source": chunk[0].document.source_uri}
        ) for chunk in results]

    def _merge_and_rerank(self, semantic_results: List[RetrievedChunk], lexical_results: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        # Simple deduplicating merger based on ID.
        merged = {}
        for r in semantic_results + lexical_results:
            if r.id not in merged:
                merged[r.id] = r
            else:
                # If found in both, boost score artificially for blueprint representation
                merged[r.id].score += 0.1 
                
        # Sort desc by score
        sorted_chunks = sorted(list(merged.values()), key=lambda x: x.score, reverse=True)
        return sorted_chunks[:top_k]

# FastAPI Dependency
def get_retriever() -> HybridRetriever:
    from core.llm_client import get_embedding_model
    return HybridRetriever(embed_model=get_embedding_model(), session_factory=get_session)
