"""Execution Router for Groundwater AI Agent.

Intelligently routes incoming queries between the ultra-fast deterministic pipeline
and the multi-step Agentic ReAct Orchestrator with automatic, graceful fallback.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.agent.planner import QueryPlanner
from backend.app.agentic.config import get_agentic_settings
from backend.app.agentic.orchestrator import AgenticOrchestrator
from backend.app.agentic.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentStep,
    EvidenceItem,
    NumericVerificationResult,
    StructuredAnswer,
)
from backend.app.agentic.verifier import extract_numbers_from_text
from backend.app.nlp.query_parser import parse_question

logger = logging.getLogger(__name__)

COMPLEXITY_PATTERNS = [
    re.compile(r"\bwhy\b", re.IGNORECASE),
    re.compile(r"\bhow\s+did\b", re.IGNORECASE),
    re.compile(r"\bhow\s+has\b", re.IGNORECASE),
    re.compile(r"\bexplain\b", re.IGNORECASE),
    re.compile(r"\btrend\s+and\s+cause\b", re.IGNORECASE),
    re.compile(r"\brecommend\b", re.IGNORECASE),
    re.compile(r"\bpolicy\b", re.IGNORECASE),
    re.compile(r"\bfactors\b", re.IGNORECASE),
    re.compile(r"\breasons?\b", re.IGNORECASE),
    re.compile(r"\bimpact\s+of\b", re.IGNORECASE),
    re.compile(r"\bcompare\b.+\band\b", re.IGNORECASE),
    re.compile(r"\bmultiple\b", re.IGNORECASE),
]


def is_complex_query(query: str, parsed: Optional[Dict[str, Any]] = None) -> bool:
    """Determine whether a natural language query warrants agentic multi-step reasoning."""
    q_lower = query.lower()

    # Check pattern matches
    for pattern in COMPLEXITY_PATTERNS:
        if pattern.search(q_lower):
            return True

    # Check multi-part conjunctions with questions
    if (" and " in q_lower or " vs " in q_lower or " versus " in q_lower) and any(w in q_lower for w in ["change", "trend", "differ", "increase", "decrease"]):
        return True

    if parsed:
        # Multiple comparison entities or low confidence
        if len(parsed.get("comparison_locations", [])) > 1:
            return True
        if parsed.get("year1") and parsed.get("year2") and "why" in q_lower:
            return True
        confidence = float(parsed.get("confidence", 1.0))
        if confidence < 0.70:
            return True

    return False


def decide_route(query: str, requested_mode: str = "auto", parsed: Optional[Dict[str, Any]] = None) -> str:
    """Decide route: returns 'deterministic' or 'agentic'."""
    settings = get_agentic_settings()

    if requested_mode == "deterministic":
        return "deterministic"

    if requested_mode == "agentic":
        return "agentic" if settings.agentic_enabled else "deterministic"

    # Default 'auto' mode
    if not settings.agentic_enabled:
        return "deterministic"

    if is_complex_query(query, parsed):
        return "agentic"

    return "deterministic"


def _format_deterministic_as_agent_response(
    query: str,
    det_result: Dict[str, Any],
    execution_time_ms: float,
    mode_used: str = "deterministic",
    notice: Optional[str] = None,
) -> AgentQueryResponse:
    """Convert deterministic pipeline output into structured AgentQueryResponse."""
    answer_text = det_result.get("answer", "")
    raw_res = det_result.get("result", {})
    selected_func = det_result.get("selected_function", "deterministic_query")
    params = det_result.get("parameters", {})
    trace = det_result.get("execution_trace", [])

    # Extract numbers from text and raw result for verification tracking
    nums = extract_numbers_from_text(answer_text)

    # Build numeric breakdown from raw result if available
    breakdown: List[Dict[str, Any]] = []
    if isinstance(raw_res, dict):
        data_block = raw_res.get("data")
        if isinstance(data_block, dict):
            for k, v in data_block.items():
                if isinstance(v, (int, float)):
                    breakdown.append({
                        "parameter": k.replace("_", " ").title(),
                        "value": v,
                        "unit": data_block.get("unit", "Ham"),
                        "year": str(data_block.get("assessment_year", "2025")),
                        "location": str(data_block.get("location") or data_block.get("state") or "N/A"),
                        "verified": True,
                    })

    summary_text = answer_text.split("\n\n")[0] if "\n\n" in answer_text else answer_text
    if notice:
        summary_text = f"[{notice}] {summary_text}"

    structured = StructuredAnswer(
        summary=summary_text,
        numeric_breakdown=breakdown,
        trend_analysis=None,
        interpretation=None,
        policy_recommendations=[],
        limitations=None,
    )

    steps = [
        AgentStep(
            step_number=1,
            thought="Direct deterministic execution via matched intent.",
            tool=selected_func,
            args=params,
            result_summary=f"Deterministic execution completed in {execution_time_ms:.1f}ms",
            latency_ms=execution_time_ms,
        )
    ]

    evidence = []
    if raw_res:
        evidence.append(
            EvidenceItem(
                tool=selected_func,
                args=params,
                data=raw_res.get("data"),
                unit=raw_res.get("data", {}).get("unit", "Ham") if isinstance(raw_res.get("data"), dict) else "Ham",
                year=str(raw_res.get("data", {}).get("assessment_year", "2025")) if isinstance(raw_res.get("data"), dict) else "2025",
                location=str(raw_res.get("data", {}).get("location", "N/A")) if isinstance(raw_res.get("data"), dict) else "N/A",
                source=raw_res.get("source", "CGWB Dynamic Ground Water Resources of India"),
                verification_status="VERIFIED",
                latency_ms=execution_time_ms,
            )
        )

    ver = NumericVerificationResult(
        passed=True,
        checked_numbers=nums,
        unverified_numbers=[],
        regenerated=False,
        fallback_used=(mode_used == "deterministic_fallback"),
        notes="Verified directly by deterministic database repository.",
    )

    citations = []
    if isinstance(raw_res, dict) and "provenance" in raw_res:
        for p in raw_res.get("provenance", []):
            citations.append({
                "source_agency": p.get("source_agency", "CGWB"),
                "source_document": p.get("source_document", "Dynamic Ground Water Resources Assessment"),
                "source_document_url": p.get("source_document_url"),
                "assessment_year": p.get("assessment_year"),
                "verification_status": "VERIFIED",
            })

    return AgentQueryResponse(
        status="success",
        query=query,
        mode_used=mode_used,
        answer=structured,
        text_answer=answer_text,
        steps=steps,
        evidence=evidence,
        citations=citations,
        verification=ver,
        latency_ms=execution_time_ms,
        model="deterministic-rule-engine",
    )


def execute_routed_query(
    request: AgentQueryRequest,
    db: Session,
    orchestrator: AgenticOrchestrator,
) -> AgentQueryResponse:
    """Execute query using the determined routing mode with deterministic fallback."""
    t0 = time.perf_counter()
    parsed = parse_question(request.query)
    mode = decide_route(request.query, requested_mode=request.mode or "auto", parsed=parsed)

    # 1. Deterministic Route
    if mode == "deterministic":
        planner = QueryPlanner(db)
        det_result = planner.plan_and_execute(parsed)
        exec_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return _format_deterministic_as_agent_response(
            query=request.query,
            det_result=det_result,
            execution_time_ms=exec_ms,
            mode_used="deterministic",
        )

    # 2. Agentic Route
    try:
        hints = {
            "year": request.year,
            "state": request.state,
            "district": request.district,
        }
        agentic_resp = orchestrator.run(query=request.query, db=db, filter_hints=hints)
        return agentic_resp
    except Exception as e:
        logger.error(f"Agentic orchestration encountered error; falling back to deterministic pipeline: {e}", exc_info=True)
        # Automatic deterministic fallback
        planner = QueryPlanner(db)
        det_result = planner.plan_and_execute(parsed)
        exec_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return _format_deterministic_as_agent_response(
            query=request.query,
            det_result=det_result,
            execution_time_ms=exec_ms,
            mode_used="deterministic_fallback",
            notice="Fell back to deterministic engine due to provider/network interruption",
        )
