# src/db/models.py
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector  # pgvector extension wrapper

Base = declarative_base()

class Document(Base):
    """
    Normalized schema representing a single logical document version.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    source_uri = Column(String, nullable=False)  # file path, S3 URL, HTTP endpoint
    version = Column(Integer, nullable=False, default=1)
    mime_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata_json = Column(JSON, nullable=True) # Renamed to avoid conflicts

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """
    Structure-aware chunks tied to the parent document.
    """
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    ordinal = Column(Integer, nullable=False)  # sequential chunk order in document
    heading = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    
    # Enrichment fields
    summary = Column(Text, nullable=True)
    hypothetical_questions = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    chunk_metadata = Column(JSON, nullable=True) # E.g., access control tags, source URL

    document = relationship("Document", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", uselist=False, back_populates="chunk", cascade="all, delete-orphan")


class ChunkEmbedding(Base):
    """
    pgvector columns for similarity search. 
    Kept separate to allow the main Chunk table to scale independently of the dense vectors.
    """
    __tablename__ = "chunk_embeddings"

    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), primary_key=True)
    vector = Column(Vector(dim=1536), nullable=False)  # dimension depends on the model (e.g. OpenAI text-embedding-3 is 1536)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunk = relationship("Chunk", back_populates="embedding")
