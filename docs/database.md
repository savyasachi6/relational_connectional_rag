# Unified Relational & Vector Database Architecture

This project strictly avoids the anti-pattern of maintaining a separate "Vector Database" (like Pinecone or Milvus) alongside a traditional relational database. Instead, **PostgreSQL with the `pgvector` extension** serves as the single source of truth for all data.

This means we store standard business metadata (dates, authors, departments) side-by-side with 1536-dimensional AI vector embeddings in the exact same database engine.

## Where is the Logic in the Code?

### 1. The Database Schema (`src/db/models.py`)

In our SQLAlchemy ORM definitions, we define the relational tables `Document` and `Chunk`. Attached directly to `Chunk` is the `ChunkEmbedding` table which utilizes the `pgvector` `Vector` column type.

```python
# From src/db/models.py
class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), primary_key=True)
    
    # This single line is what turns Postgres into an AI database
    vector = Column(Vector(dim=1536), nullable=False) 
```

By storing the vector as just another column tied by a foreign key, the vector is strongly consistent with the actual text. If a document is deleted, the cascade effortlessly deletes the vector.

### 2. The Hybrid Search Query (`src/core/retrieval.py`)

Because the text, metadata, and vectors live in the same database, the Reasoning API doesn't have to query a vector database, pull IDs, and then query a SQL database to hydrate the results. It does it all in a single query.

```python
# From src/core/retrieval.py
stmt = (
    select(Chunk, ChunkEmbedding.vector.cosine_distance(query_vector).label('distance'))
    .join(ChunkEmbedding)
    .join(Document)
    .order_by('distance')
    .limit(top_k)
)
```

* `.cosine_distance()` is the pgvector `<=>` operator calculated natively inside Postgres.
* `.join(Document)` allows us to instantaneously filter by relational metadata (e.g. `WHERE Document.version > 2`).

### 3. The Docker Engine (`docker-compose.yml`)

To support this locally, we use the `ankane/pgvector:latest` Docker image. This is a standard PostgreSQL instance compiled with the pgvector C-extension, instantly giving us relational and semantic capabilities.

## Why is this important?

In production AI systems:

1. **Consistency**: You never run into sync issues where a document is deleted from Postgres but its ghost embedding remains in your Vector DB.
2. **Performance**: Returning the top semantic hits while simultaneously validating relational access controls (e.g. "Does this user have permission to see this department's files?") happens in one database round-trip.
3. **Agentic Architecture**: As highlighted in the ByteMonk architecture, serverless Postgres variants (like Databricks Neon) allow AI agents to spin up temporary database branches, test new embedding models, and tear them down, treating the database as agile compute.
