# src/ingestion/enrichment.py
import json
import asyncio
from typing import List, Dict, Any
from core.llm_client import get_llm_client
from pydantic import BaseModel, Field

class EnrichmentOutput(BaseModel):
    summary: str = Field(description="A 1-sentence summary of the chunk.")
    keywords: List[str] = Field(description="A list of 3-5 keywords.")
    questions: List[str] = Field(description="2 hypothetical questions this chunk answers perfectly.")

async def async_enrich_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    llm = get_llm_client()
    
    prompt = f"""
    Analyze the following document chunk and extract the requested metadata.
    
    Chunk Content:
    {chunk['content']}
    """
    
    try:
        # If using OpenAI, we leverage structured outputs
        if hasattr(llm, 'client') and llm.client is not None:
             response = llm.client.beta.chat.completions.parse(
                 model=llm.model_name,
                 messages=[{"role": "user", "content": prompt}],
                 response_format=EnrichmentOutput,
                 temperature=0.0
             )
             enrichment_data = response.choices[0].message.parsed
             chunk["summary"] = enrichment_data.summary
             chunk["keywords"] = enrichment_data.keywords
             chunk["questions"] = enrichment_data.questions
        else:
             # Fallback for mock client
             response_str = await llm.complete(prompt)
             chunk["summary"] = "Mock Summary"
             chunk["keywords"] = ["mock", "keywords"]
             chunk["questions"] = ["mock question 1?"]
             
    except Exception as e:
        print(f"Enrichment failed: {e}")
        chunk["summary"] = f"Extraction failed: {str(e)}"
        chunk["keywords"] = []
        chunk["questions"] = []
        
    return chunk

def enrich_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enriches chunks with LLM metadata (summaries, keywords, hypothetical questions).
    In production, this should be massively batched or run asynchronously.
    """
    # Standard asyncio run for the blueprint
    loop = asyncio.get_event_loop()
    tasks = [async_enrich_chunk(chunk) for chunk in chunks]
    enriched_chunks = loop.run_until_complete(asyncio.gather(*tasks))
    return enriched_chunks
