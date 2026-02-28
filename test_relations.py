import sys
import asyncio
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "src"))

from db.session import get_session, engine
from db.models import Base
from core.retrieval import HybridRetriever
from ingestion.ingestion_worker import ingest_document

# Mock the embedding model for local tests without keys
class MockEmbeddingModel:
    def embed_text(self, text: str):
        return [0.1] * 1536  # Mock 1536-dim vector

async def test_relational_retrieval():
    # 1. Initialize fresh DB schema
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

    # 2. Mock Ingestion
    print("Ingesting mock document...")
    # NOTE: Assuming there's a small mock file we can ingest or we can just mock the chunks
    # For now, let's just create raw chunks in the DB manually to test relations
    
    with get_session() as session:
        from db.models import Document, Chunk, ChunkEmbedding, EntityRelation
        import uuid
        
        doc_id = uuid.uuid4()
        session.add(Document(id=doc_id, source_uri="mock://test"))
        
        c1_id, c2_id, c3_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        
        for i, c_id in enumerate([c1_id, c2_id, c3_id]):
            session.add(Chunk(id=c_id, document_id=doc_id, ordinal=i, content=f"Chunk {i+1} content"))
            session.add(ChunkEmbedding(chunk_id=c_id, vector=[0.1]*1536))
            
        # Create relations: c1 -> c2 and c2 -> c3
        session.add(EntityRelation(source_chunk_id=c1_id, target_chunk_id=c2_id, relation_type="next_chunk"))
        session.add(EntityRelation(source_chunk_id=c2_id, target_chunk_id=c3_id, relation_type="next_chunk"))
        session.commit()
        print("Mock data and edges inserted.")

    # 3. Test Retrieval
    print("Testing relational retrieval...")
    retriever = HybridRetriever(embed_model=MockEmbeddingModel(), session_factory=get_session, top_k=2)
    
    # Run the retrieval. Because all vectors are identical [0.1]*1536, it will just return 2 chunks.
    results = await retriever.retrieve(query="test query")
    
    print(f"Retrieved {len(results)} chunks.")
    for res in results:
        print(f"\nChunk ID: {res.id}")
        print(f"Content: {res.content}")
        print(f"Relations: {res.relations}")

if __name__ == "__main__":
    asyncio.run(test_relational_retrieval())
