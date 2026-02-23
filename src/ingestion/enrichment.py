# src/ingestion/enrichment.py
import json
import asyncio
from typing import List, Dict, Any
from core.llm_client import get_llm_client

async def async_enrich_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    llm = get_llm_client()
    
    prompt = f"""
    Analyze the following document chunk.
    Provide a pure JSON response with:
    1. "summary": A 1-sentence summary.
    2. "keywords": A list of 3-5 keywords.
    3. "questions": A list of 2 hypothetical user questions this chunk could answer perfectly.
    
    Chunk Content:
    {chunk['content']}
    """
    
    try:
        response = await llm.complete(prompt)
        enrichment_data = json.loads(response) # Standard risk of JSON parse failure here in prod
        chunk["summary"] = enrichment_data.get("summary")
        chunk["keywords"] = enrichment_data.get("keywords", [])
        chunk["questions"] = enrichment_data.get("questions", [])
    except Exception as e:
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
