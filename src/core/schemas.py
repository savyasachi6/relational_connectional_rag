# src/core/schemas.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# --- Ingestion API IO ---

class IngestRequest(BaseModel):
    source_uri: str = Field(..., description="Path, S3 URL, or HTTP endpoint to ingest")
    mime_type: Optional[str] = Field(None, description="Optional mime type hint (e.g. application/pdf)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom document metadata")

class IngestResponse(BaseModel):
    document_id: str
    status: str
    message: str


# --- Asking API IO ---

class AskRequest(BaseModel):
    query: str = Field(..., description="The user's question")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Relational filters (e.g., department, date range)")
    top_k: Optional[int] = Field(None, description="Number of results to retrieve")
    risk_profile: Optional[str] = Field("medium", description="Risk tolerance: low, medium, high, critical")

class AskResponse(BaseModel):
    answer: str
    validation: Dict[str, Any] = Field(..., description="Reports from Gatekeeper, Auditor, Strategist validators")
    retrieved_chunks: List[Dict[str, Any]] = Field(..., description="The context used to generate the answer")
