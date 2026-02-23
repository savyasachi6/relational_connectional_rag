# src/db/session.py
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Expects connection string from environment, falling back to a default for local testing
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag_knowledge_base")

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_session():
    """
    Context manager to provide a transactional scope around a series of operations.
    Usage:
        with get_session() as session:
            session.add(some_model)
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_db():
    """
    FastAPI dependency to inject database sessions into routes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
