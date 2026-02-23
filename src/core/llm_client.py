# src/core/llm_client.py
from abc import ABC, abstractmethod
from typing import List
from .config import settings

# In a real app, this would use the official openai python library or LiteLLM
import openai

class LLMClient(ABC):
    """
    Abstract wrapper interface for LLM completions.
    Allows easy swapping between OpenAI, Anthropic, or local Ollama instances.
    """
    @abstractmethod
    async def complete(self, prompt: str) -> str:
        pass

class OpenAIClient(LLMClient):
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        # Using synchronous client for simplicity in this skeleton; 
        # ideally use openai.AsyncClient() in production
        self.client = openai.Client(api_key=api_key) if api_key else None

    async def complete(self, prompt: str) -> str:
        if not self.client:
            # Placeholder for testing without keys
            return "MOCK_LLM_RESPONSE: Completed prompt successfully."
            
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0 # Deterministic for reasoning/validation
        )
        return response.choices[0].message.content


class EmbeddingModel(ABC):
    """Wrapper for computing vector embeddings."""
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

class OpenAIEmbedding(EmbeddingModel):
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.client = openai.Client(api_key=api_key) if api_key else None

    def embed_text(self, text: str) -> List[float]:
        if not self.client:
            return [0.0] * 1536 # Mock vector
            
        res = self.client.embeddings.create(
            model=self.model_name,
            input=[text]
        )
        return res.data[0].embedding


# Dependency Factories
def get_llm_client() -> LLMClient:
    return OpenAIClient(model_name=settings.LLM_MODEL_NAME, api_key=settings.OPENAI_API_KEY)

def get_embedding_model() -> EmbeddingModel:
    return OpenAIEmbedding(model_name=settings.EMBEDDING_MODEL_NAME, api_key=settings.OPENAI_API_KEY)
