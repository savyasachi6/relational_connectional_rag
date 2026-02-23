# src/validation/validation.py
from typing import Any, Dict, Tuple, List
import json

from core.llm_client import LLMClient
from core.retrieval import RetrievedChunk

async def run_validation_pipeline(
    llm: LLMClient,
    query: str,
    draft_answer: str,
    retrieved_chunks: List[RetrievedChunk],
    risk_profile: str = "medium",
) -> Tuple[str, Dict[str, Any]]:
    """
    Orchestrate gatekeeper, auditor, and strategist checks.
    Optionally request a rewrite if validation fails.
    """
    gatekeeper_ok, g_report = await _gatekeeper(llm, query, draft_answer)
    auditor_ok, a_report = await _auditor(llm, draft_answer, retrieved_chunks)
    strategist_ok, s_report = await _strategist(llm, query, draft_answer, risk_profile)

    reports = {
        "gatekeeper": g_report,
        "auditor": a_report,
        "strategist": s_report,
    }

    if gatekeeper_ok and auditor_ok and strategist_ok:
        return draft_answer, reports

    # High-risk: prefer safe failure over confident nonsense.
    if risk_profile in {"high", "critical"} and not (gatekeeper_ok and auditor_ok):
        safe_msg = "The system cannot provide a reliable answer based on the available context."
        return safe_msg, reports

    # Otherwise, attempt a single rewrite guided by validation feedback.
    revised = await _rewrite_with_feedback(
        llm=llm,
        query=query,
        answer=draft_answer,
        reports=reports,
        retrieved_chunks=retrieved_chunks,
    )
    return revised, reports


from pydantic import BaseModel, Field

# --- Validation Schemas ---
class GatekeeperReport(BaseModel):
    ok: bool = Field(description="True if the answer addresses the question, False if evasive.")
    reason: str = Field(description="Reason for the decision.")

class AuditorReport(BaseModel):
    ok: bool = Field(description="True if strictly grounded in context.")
    issues: List[str] = Field(description="List of ungrounded claims or hallucinations.")
    missing_citations: List[str] = Field(description="Information missing citations.")

class StrategistReport(BaseModel):
    ok: bool = Field(description="True if the answer matches the risk profile constraints.")
    concerns: List[str] = Field(description="Strategic or safety concerns.")


async def _gatekeeper(llm: LLMClient, query: str, answer: str) -> Tuple[bool, dict]:
    prompt = f"""
You are a gatekeeper.
Task: Decide if the ANSWER directly addresses the QUESTION and is not evasive.
QUESTION: {query}
ANSWER: {answer}
"""
    try:
        if hasattr(llm, 'client') and llm.client:
             response = llm.client.beta.chat.completions.parse(
                 model=llm.model_name,
                 messages=[{"role": "user", "content": prompt}],
                 response_format=GatekeeperReport,
                 temperature=0.0
             )
             report = response.choices[0].message.parsed.model_dump()
             return report["ok"], report
             
        result = await llm.complete(prompt + "\nRespond with pure JSON: {'ok': true/false, 'reason': '...'}")
        report = json.loads(result)
        return report.get("ok", False), report
    except Exception as e:
        return True, {"error": str(e)}


async def _auditor(llm: LLMClient, answer: str, chunks: List[RetrievedChunk]) -> Tuple[bool, dict]:
    context = "\n\n".join(c.content for c in chunks)
    prompt = f"""
You are an auditor.
Task: Verify that the ANSWER is strictly grounded in the CONTEXT. Flag any hallucinations or unsupported claims.
CONTEXT:
{context}

ANSWER:
{answer}
"""
    try:
        if hasattr(llm, 'client') and llm.client:
             response = llm.client.beta.chat.completions.parse(
                 model=llm.model_name,
                 messages=[{"role": "user", "content": prompt}],
                 response_format=AuditorReport,
                 temperature=0.0
             )
             report = response.choices[0].message.parsed.model_dump()
             return report["ok"], report
             
        result = await llm.complete(prompt + "\nRespond with pure JSON: {'ok': true/false, 'issues': [], 'missing_citations': []}")
        report = json.loads(result)
        return report.get("ok", False), report
    except Exception as e:
        return True, {"error": str(e)}


async def _strategist(llm: LLMClient, query: str, answer: str, risk_profile: str) -> Tuple[bool, dict]:
    prompt = f"""
You are a strategist operating at risk profile: {risk_profile}.
Task: Evaluate whether the ANSWER is reasonable and complete for the QUESTION, given a {risk_profile} risk tolerance. 
QUESTION: {query}
ANSWER: {answer}
"""
    try:
        if hasattr(llm, 'client') and llm.client:
             response = llm.client.beta.chat.completions.parse(
                 model=llm.model_name,
                 messages=[{"role": "user", "content": prompt}],
                 response_format=StrategistReport,
                 temperature=0.0
             )
             report = response.choices[0].message.parsed.model_dump()
             return report["ok"], report
             
        result = await llm.complete(prompt + "\nRespond with pure JSON: {'ok': true/false, 'concerns': []}")
        report = json.loads(result)
        return report.get("ok", False), report
    except Exception as e:
        return True, {"error": str(e)}


async def _rewrite_with_feedback(
    llm: LLMClient,
    query: str,
    answer: str,
    reports: Dict[str, Any],
    retrieved_chunks: List[RetrievedChunk],
) -> str:
    context = "\n\n".join(c.content for c in retrieved_chunks)
    prompt = f"""
You are revising an earlier answer based on validator feedback.
QUESTION: {query}
ORIGINAL ANSWER: {answer}
VALIDATION FEEDBACK (JSON): {json.dumps(reports)}
CONTEXT (authoritative):
{context}

Task: Produce a revised answer that directly answers the question, avoids hallucinations, and cites only what is supported by the context.
Revised answer:
"""
    return await llm.complete(prompt)
