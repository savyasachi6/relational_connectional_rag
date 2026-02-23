# src/core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application configuration via environment variables.
    Pydantic automatically reads from the environment or a .env file.
    """
    APP_NAME: str = "Scalable RAG API"
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rag_knowledge_base")
    
    # LLM & Embeddings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4-turbo")
    
    # Retrieval Tuning
    DEFAULT_TOP_K: int = 8
    
    class Config:
        env_file = ".env"

settings = Settings()
