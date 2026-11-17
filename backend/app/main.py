"""FastAPI main application."""
import time
import json
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import settings
from .database.connection import get_db, init_db, get_sync_db
from .database import repository as repo
from .agent.session_manager import SessionManager
from .database.models import (
    State, District, AssessmentYear, GroundwaterResource,
    SourceDataset, QueryLog, EvaluationResult, ConversationSession, ConversationMessage
)
from .database.functions import get_registry_metadata, execute_function
from .nlp.query_parser import parse_question
from .agent.planner import QueryPlanner
from .schemas.schemas import (
    QueryRequest, QueryResponse, HealthResponse, MetadataResponse,
    StructuredQueryRequest, EvaluationSummary, ChatRequest, ChatResponse
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup
    init_db()
    yield


app = FastAPI(
    title="Groundwater AI Agent API",
    description="Natural Language Groundwater Database Query Agent powered by IN-GRES/CGWB data",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────── Health ─────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        total = db.query(func.count(GroundwaterResource.id)).filter(
            GroundwaterResource.is_verified.is_(True)
        ).scalar() or 0
        years = repo.get_assessment_years(db).get("data") or []
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            database_connected=True,
            total_records=total,
            assessment_years=years,
        )
    except Exception as e:
        return HealthResponse(
            status="degraded",
            version=settings.APP_VERSION,
            database_connected=False,
            total_records=0,
            assessment_years=[],
        )


@app.get("/api/metadata", response_model=MetadataResponse, tags=["System"])
def get_metadata(db: Session = Depends(get_db)):
    total = db.query(func.count(GroundwaterResource.id)).filter(
        GroundwaterResource.is_verified.is_(True)
    ).scalar() or 0
    states = len(repo.get_state_list(db)["data"])
    districts = repo.get_data_coverage(db)["data"]["total_districts"]
    years = repo.get_assessment_years(db)["data"]
    return MetadataResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered natural language interface to CGWB groundwater resource assessment data.",
        total_records=total,
        states=states,
        districts=districts,
        assessment_years=years,
        data_source="Individually verified CGWB assessment records",
        llm_provider=settings.LLM_PROVIDER,
    )


# ──────────────────────────── Geography ──────────────────────────────────────

@app.get("/api/states", tags=["Geography"])
def list_states(db: Session = Depends(get_db)):
    states = [s.name for s in db.query(State).order_by(State.name).all()]
    return {"states": states}


@app.get("/api/districts/{state}", tags=["Geography"])
def list_districts(state: str, db: Session = Depends(get_db)):
    st = db.query(State).filter(State.name.ilike(f"%{state}%")).first()
    if not st:
        raise HTTPException(status_code=404, detail=f"State '{state}' not found.")
    districts = (
        db.query(District.name)
        .filter(District.state_id == st.id)
        .distinct()
        .order_by(District.name)
        .all()
    )
    return {"state": st.name, "districts": [d[0] for d in districts]}


@app.get("/api/assessment-years", tags=["Geography"])
def list_assessment_years(db: Session = Depends(get_db)):
    years = [y.year for y in db.query(AssessmentYear).order_by(AssessmentYear.year).all()]
    return {"assessment_years": years}


# ──────────────────────────── Query ──────────────────────────────────────────

@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
def natural_language_query(request: QueryRequest, db: Session = Depends(get_db)):
    parsed = parse_question(request.question)
    planner = QueryPlanner(db)
    result = planner.plan_and_execute(parsed)

    try:
        log = QueryLog(
            question=request.question,
            intent=result.get("intent"),
            entities=json.dumps(result.get("entities", {})),
            function_called=result.get("selected_function"),
            parameters=json.dumps(result.get("parameters", {})),
            status=result.get("status"),
            response_text=result.get("answer", "")[:2000],
            execution_time_ms=result.get("execution_time_ms"),
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()

    return QueryResponse(**result)


# ──────────────────────────── Chat & Sessions ────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    t0 = time.time()
    session_mgr = SessionManager(db)
    session = session_mgr.get_or_create_session(request.session_id)

    # 1. Check conversational / domain questions first
    conv_res = session_mgr.resolve_conversational_query(request.question, session)
    if conv_res:
        exec_ms = round((time.time() - t0) * 1000, 2)
        session_mgr.record_turn(
            session=session,
            question=request.question,
            answer=conv_res["answer"],
            intent=conv_res["intent"],
            execution_time_ms=exec_ms,
        )
        return ChatResponse(
            status="success",
            question=request.question,
            session_id=session.session_id,
            answer=conv_res["answer"],
            intent=conv_res["intent"],
            active_context=session_mgr.get_context(session),
            model_used="Groundwater Knowledge Base",
            execution_time_ms=exec_ms,
            source="CGWB IN-GRES Domain Knowledge",
        )

    # 2. Parse question with selected mode
    mode = request.mode or "hybrid"
    parsed = parse_question(request.question, mode=mode)

    # 3. Apply conversational context (e.g. "What about 2020?", "Compare both")
    parsed = session_mgr.apply_context_to_query(parsed, session)

    # 4. Plan and execute
    planner = QueryPlanner(db)
    plan_res = planner.plan_and_execute(parsed)
    exec_ms = round((time.time() - t0) * 1000, 2)

    # 5. Update session context
    context_updates = {}
    if parsed.get("state"):
        context_updates["last_state"] = parsed.get("state")
    if parsed.get("district"):
        context_updates["last_district"] = parsed.get("district")
    elif parsed.get("state") and not parsed.get("district"):
        # Explicit state-only query (e.g. "What about Punjab?") - clear district
        context_updates["last_district"] = None

    if parsed.get("assessment_year") and plan_res.get("status") == "success":
        context_updates["last_year"] = parsed.get("assessment_year")

    if parsed.get("parameter"):
        context_updates["last_parameter"] = parsed.get("parameter")
    if parsed.get("intent") and parsed.get("intent") not in ["ambiguous", "greeting", "general_conversation"]:
        context_updates["last_intent"] = parsed.get("intent")

    if plan_res.get("answer"):
        context_updates["last_result_summary"] = plan_res.get("answer")
    if plan_res.get("selected_function"):
        context_updates["last_function"] = plan_res.get("selected_function")

    session_mgr.update_context(session, context_updates)

    # 6. Record turn
    session_mgr.record_turn(
        session=session,
        question=request.question,
        answer=plan_res.get("answer", ""),
        intent=plan_res.get("intent"),
        entities=plan_res.get("entities"),
        function_name=plan_res.get("selected_function"),
        parameters=plan_res.get("parameters"),
        result_data=plan_res.get("result"),
        trace=plan_res.get("execution_trace"),
        execution_time_ms=exec_ms,
    )

    return ChatResponse(
        status=plan_res.get("status", "success"),
        question=request.question,
        session_id=session.session_id,
        answer=plan_res.get("answer", ""),
        intent=plan_res.get("intent"),
        entities=plan_res.get("entities"),
        selected_function=plan_res.get("selected_function"),
        parameters=plan_res.get("parameters"),
        result=plan_res.get("result"),
        active_context=session_mgr.get_context(session),
        model_used=parsed.get("model_used"),
        execution_trace=plan_res.get("execution_trace"),
        execution_time_ms=exec_ms,
        source=plan_res.get("source"),
    )


@app.get("/api/chat/history/{session_id}", tags=["Chat"])
def get_chat_history(session_id: str, db: Session = Depends(get_db)):
    msgs = db.query(ConversationMessage).filter(
        ConversationMessage.session_id == session_id
    ).order_by(ConversationMessage.created_at.asc()).all()
    session = db.query(ConversationSession).filter(
        ConversationSession.session_id == session_id
    ).first()
    ctx = json.loads(session.active_context) if (session and session.active_context) else {}
    return {
        "session_id": session_id,
        "active_context": ctx,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "intent": m.intent,
                "function_executed": m.function_called,
                "execution_trace": json.loads(m.execution_trace_json) if m.execution_trace_json else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@app.post("/api/query/structured", tags=["Query"])
def structured_query(request: StructuredQueryRequest, db: Session = Depends(get_db)):
    func_name = request.intent
    params = {k: v for k, v in {
        "state": request.state,
        "district": request.district,
        "assessment_year": request.assessment_year,
    }.items() if v}
    result = execute_function(func_name, db, **params)
    return {"status": result.get("status"), "function": func_name, "result": result}


# ──────────────────────────── Functions ──────────────────────────────────────

@app.get("/api/functions", tags=["Registry"])
def get_functions():
    return {"functions": get_registry_metadata()}


# ──────────────────────────── History ────────────────────────────────────────

@app.get("/api/query-history", tags=["Analytics"])
def query_history(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit).all()
    return {
        "history": [
            {
                "id": r.id,
                "question": r.question,
                "intent": r.intent,
                "function_called": r.function_called,
                "status": r.status,
                "execution_time_ms": r.execution_time_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


# ──────────────────────────── Evaluation ─────────────────────────────────────

@app.get("/api/evaluation/summary", tags=["Evaluation"])
def evaluation_summary(db: Session = Depends(get_db)):
    rows = db.query(EvaluationResult).all()
    if not rows:
        return {
            "message": "No evaluation results yet. Run: python scripts/evaluate_agent.py",
            "total_test_cases": 0,
        }
    total = len(rows)
    intent_correct = sum(1 for r in rows if r.intent_correct)
    func_correct = sum(1 for r in rows if r.function_correct)
    status_correct = sum(1 for r in rows if r.status_correct)
    e2e_correct = sum(1 for r in rows if r.end_to_end_correct)
    unsupported = [r for r in rows if r.error_category == "unsupported"]
    unsupported_ok = sum(1 for r in unsupported if r.status_correct)
    avg_time = sum(r.execution_time_ms or 0 for r in rows) / total if total else 0

    entity_scores = [r.entity_extraction_score for r in rows if r.entity_extraction_score is not None]
    entity_acc = sum(entity_scores) / len(entity_scores) * 100 if entity_scores else 0

    return {
        "total_test_cases": total,
        "passed": e2e_correct,
        "failed": total - e2e_correct,
        "intent_accuracy_pct": round(intent_correct / total * 100, 2) if total else 0,
        "entity_accuracy_pct": round(entity_acc, 2),
        "function_accuracy_pct": round(func_correct / total * 100, 2) if total else 0,
        "db_success_rate_pct": round(status_correct / total * 100, 2) if total else 0,
        "end_to_end_accuracy_pct": round(e2e_correct / total * 100, 2) if total else 0,
        "unsupported_handling_pct": round(unsupported_ok / len(unsupported) * 100, 2) if unsupported else 0,
        "avg_response_time_ms": round(avg_time, 2),
    }


@app.get("/api/evaluation/details", tags=["Evaluation"])
def evaluation_details(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(EvaluationResult).order_by(EvaluationResult.created_at.desc()).limit(limit).all()
    return {
        "results": [
            {
                "test_case_id": r.test_case_id,
                "question": r.input_question,
                "expected_intent": r.expected_intent,
                "actual_intent": r.actual_intent,
                "intent_correct": r.intent_correct,
                "expected_function": r.expected_function,
                "actual_function": r.actual_function,
                "function_correct": r.function_correct,
                "end_to_end_correct": r.end_to_end_correct,
                "execution_time_ms": r.execution_time_ms,
                "error_category": r.error_category,
                "notes": r.notes,
            }
            for r in rows
        ]
    }


# ──────────────────────────── Sources ────────────────────────────────────────

@app.get("/api/sources", tags=["Data"])
def data_sources(db: Session = Depends(get_db)):
    rows = db.query(SourceDataset).order_by(SourceDataset.id).all()
    sources = []
    for row in rows:
        verified_count = db.query(GroundwaterResource).filter(
            GroundwaterResource.source_dataset_id == row.id,
            GroundwaterResource.is_verified.is_(True),
        ).count()
        sources.append({
            "id": row.id,
            "name": row.name,
            "source_url": row.source_url,
            "assessment_period": row.assessment_period,
            "publication_year": row.publication_year,
            "data_year": row.data_year,
            "source_agency": row.source_agency,
            "data_format": row.data_format,
            "unit": row.unit,
            "geographic_coverage": row.geographic_coverage,
            "num_records": row.num_records,
            "verified_record_count": verified_count,
            "is_verified": bool(row.is_verified and verified_count >= row.num_records),
            "download_date": row.download_date.isoformat() if row.download_date else None,
            "notes": row.notes,
        })
    return {
        "sources": sources
    }


# ──────────────────────────── Analytics ──────────────────────────────────────

def _source_provenance(db: Session, year: str):
    return repo.get_source_provenance(db, year)


@app.get("/api/analytics/state-comparison", tags=["Analytics"])
def state_comparison(year: str = "2025", db: Session = Depends(get_db)):
    yr = db.query(AssessmentYear).filter(AssessmentYear.year == year).first()
    if not yr:
        raise HTTPException(status_code=404, detail=f"Year {year} not available.")

    rows = (
        db.query(
            State.name,
            func.sum(GroundwaterResource.total_annual_recharge).label("total_recharge"),
            func.sum(GroundwaterResource.total_annual_extraction).label("total_extraction"),
            func.sum(GroundwaterResource.annual_extractable_groundwater).label("total_extractable"),
            func.count(GroundwaterResource.id).label("district_count"),
        )
        .join(GroundwaterResource, GroundwaterResource.state_id == State.id)
        .filter(
            GroundwaterResource.assessment_year_id == yr.id,
        )
        .group_by(State.name)
        .order_by(State.name)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No groundwater records are available for assessment year {year}.",
        )
    return {
        "assessment_year": year,
        "provenance": [_source_provenance(db, year)],
        "states": [
            {
                "state": row[0],
                "total_recharge_ham": round(row[1], 2) if row[1] is not None else None,
                "total_extraction_ham": round(row[2], 2) if row[2] is not None else None,
                "total_extractable_ham": round(row[3], 2) if row[3] is not None else None,
                "district_count": row[4],
            }
            for row in rows
        ],
    }


@app.get("/api/analytics/category-distribution", tags=["Analytics"])
def category_distribution(year: str = "2025", state: str = None, db: Session = Depends(get_db)):
    yr = db.query(AssessmentYear).filter(AssessmentYear.year == year).first()
    if not yr:
        raise HTTPException(status_code=404, detail=f"Year {year} not available.")

    q = (
        db.query(
            GroundwaterResource.assessment_category,
            func.count(GroundwaterResource.id).label("count"),
        )
        .filter(
            GroundwaterResource.assessment_year_id == yr.id,
            GroundwaterResource.assessment_category.is_not(None),
        )
    )
    if state:
        st = db.query(State).filter(State.name.ilike(f"%{state}%")).first()
        if st:
            q = q.filter(GroundwaterResource.state_id == st.id)

    rows = q.group_by(GroundwaterResource.assessment_category).all()
    return {
        "assessment_year": year,
        "provenance": [_source_provenance(db, year)],
        "data_available": bool(rows),
        "state_filter": state,
        "distribution": [{"category": row[0], "count": row[1]} for row in rows],
    }


@app.get("/api/analytics/district-data/{state}", tags=["Analytics"])
def district_data(state: str, year: str = "2025", district: Optional[str] = None, db: Session = Depends(get_db)):
    yr = db.query(AssessmentYear).filter(AssessmentYear.year == year).first()
    if not yr:
        raise HTTPException(status_code=404, detail=f"Year {year} not available.")

    st = db.query(State).filter(State.name.ilike(f"%{state}%")).first()
    if not st:
        raise HTTPException(status_code=404, detail=f"State '{state}' not found.")

    q = (
        db.query(
            District.name,
            GroundwaterResource.total_annual_recharge,
            GroundwaterResource.annual_extractable_groundwater,
            GroundwaterResource.total_annual_extraction,
            GroundwaterResource.stage_of_extraction_pct,
            GroundwaterResource.assessment_category,
            GroundwaterResource.annual_extraction_irrigation,
            GroundwaterResource.annual_extraction_domestic,
            GroundwaterResource.annual_extraction_industrial,
            GroundwaterResource.is_verified,
            GroundwaterResource.verification_status,
        )
        .join(GroundwaterResource, GroundwaterResource.district_id == District.id)
        .filter(
            GroundwaterResource.state_id == st.id,
            GroundwaterResource.assessment_year_id == yr.id,
        )
    )
    if district:
        q = q.filter(District.name.ilike(f"%{district.strip()}%"))
    rows = q.order_by(District.name).all()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No groundwater records are available for {st.name} in {year}.",
        )
    return {
        "state": st.name,
        "assessment_year": year,
        "provenance": [_source_provenance(db, year)],
        "districts": [
            {
                "district": row[0],
                "total_annual_recharge_ham": row[1],
                "annual_extractable_groundwater_ham": row[2],
                "total_annual_extraction_ham": row[3],
                "stage_of_extraction_pct": row[4],
                "assessment_category": row[5],
                "irrigation_extraction_ham": row[6],
                "domestic_extraction_ham": row[7],
                "industrial_extraction_ham": row[8],
                "is_verified": bool(row[9]),
                "verification_status": row[10] or ("VERIFIED" if row[9] else "UNVERIFIED"),
            }
            for row in rows
        ],
    }


@app.get("/api/analytics/district-multiyear/{state}/{district}", tags=["Analytics"])
def district_multiyear_profile(state: str, district: str, db: Session = Depends(get_db)):
    st = db.query(State).filter(State.name.ilike(f"%{state}%")).first()
    if not st:
        raise HTTPException(status_code=404, detail=f"State '{state}' not found.")
    dist = db.query(District).filter(District.name.ilike(f"%{district}%"), District.state_id == st.id).first()
    if not dist:
        dist = db.query(District).filter(District.name.ilike(f"%{district}%")).first()
    if not dist:
        raise HTTPException(status_code=404, detail=f"District '{district}' not found.")

    records = (
        db.query(
            AssessmentYear.year,
            GroundwaterResource.total_annual_extraction,
            GroundwaterResource.total_annual_recharge,
            GroundwaterResource.annual_extractable_groundwater,
            GroundwaterResource.stage_of_extraction_pct,
            GroundwaterResource.assessment_category,
            GroundwaterResource.annual_extraction_irrigation,
            GroundwaterResource.annual_extraction_domestic,
            GroundwaterResource.annual_extraction_industrial,
            GroundwaterResource.is_verified,
            GroundwaterResource.verification_status,
        )
        .join(AssessmentYear, GroundwaterResource.assessment_year_id == AssessmentYear.id)
        .filter(GroundwaterResource.district_id == dist.id)
        .order_by(AssessmentYear.year.asc())
        .all()
    )
    return {
        "state": st.name,
        "district": dist.name,
        "years": [
            {
                "year": r[0],
                "total_extraction_ham": r[1],
                "total_recharge_ham": r[2],
                "extractable_ham": r[3],
                "stage_pct": r[4],
                "category": r[5],
                "irrigation_ham": r[6],
                "domestic_ham": r[7],
                "industrial_ham": r[8],
                "is_verified": bool(r[9]),
                "verification_status": r[10],
            }
            for r in records
        ]
    }


# ──────────────────────────── National Coverage & Multi-Year ─────────────────

@app.get("/api/coverage", tags=["Data"])
def get_national_coverage(db: Session = Depends(get_db)):
    """Return national data coverage across all states, districts, and assessment years."""
    return repo.get_data_coverage(db)


@app.get("/api/analytics/yearly-coverage", tags=["Data"])
def get_yearly_coverage_endpoint(db: Session = Depends(get_db)):
    """Return authentic dynamic assessment year coverage matrix across target cycles."""
    return repo.get_yearly_coverage_matrix(db)


@app.get("/api/analytics/historical-trend", tags=["Analytics"])
def get_historical_trend(
    state: str,
    district: Optional[str] = None,
    parameter: Optional[str] = "extraction",
    db: Session = Depends(get_db),
):
    """Return multi-year historical trend records for chart visualization."""
    return repo.get_yearly_groundwater_trend(db, state=state, district=district, parameter=parameter)


@app.get("/api/analytics/compare-years", tags=["Analytics"])
def compare_assessment_years_endpoint(
    state: str,
    year1: str = "2020",
    year2: str = "2022",
    district: Optional[str] = None,
    parameter: Optional[str] = "extraction",
    db: Session = Depends(get_db),
):
    """Compare groundwater parameters between two assessment cycles."""
    return repo.compare_assessment_years(
        db, state=state, district=district, parameter=parameter, year1=year1, year2=year2
    )


@app.get("/api/evaluation/model-comparison", tags=["Evaluation"])
def get_model_comparison():
    """Return latest benchmark evaluation results across all models."""
    report_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "evaluation", "model_comparison.json"
    )
    if os.path.exists(report_file):
        with open(report_file, "r", encoding="utf-8") as f:
            return {"status": "success", "data": json.load(f)}
    return {"status": "not_found", "message": "Model comparison file not generated yet."}


# ============================================================================
# Agentic & Generative AI Endpoints
# ============================================================================
from fastapi.responses import StreamingResponse
from backend.app.agentic.config import get_agentic_settings
from backend.app.agentic.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentStatusResponse,
)
from backend.app.agentic.orchestrator import AgenticOrchestrator
from backend.app.agentic.router import execute_routed_query

# Global agentic orchestrator instance
_agent_orchestrator = AgenticOrchestrator()


@app.get("/api/agent/status", response_model=AgentStatusResponse, tags=["Agentic AI"])
def get_agent_status():
    """Return current agent status, active provider, model, and key configuration."""
    cfg = get_agentic_settings()
    return AgentStatusResponse(
        provider=cfg.llm_provider,
        model=cfg.llm_model,
        api_key_configured=cfg.has_api_key(),
        agentic_enabled=cfg.agentic_enabled,
        max_steps=cfg.agent_max_steps,
        timeout_seconds=cfg.agent_timeout_seconds,
    )


@app.post("/api/agent/query", response_model=AgentQueryResponse, tags=["Agentic AI"])
def agent_query_endpoint(
    request: AgentQueryRequest,
    db: Session = Depends(get_db),
):
    """Execute natural language query via intelligent router (deterministic or ReAct agentic loop)."""
    return execute_routed_query(request=request, db=db, orchestrator=_agent_orchestrator)


@app.post("/api/agent/stream", tags=["Agentic AI"])
def agent_stream_endpoint(
    request: AgentQueryRequest,
    db: Session = Depends(get_db),
):
    """Stream reasoning steps and final grounded answer using Server-Sent Events (SSE)."""
    def event_generator():
        try:
            # Yield initial thinking notice
            yield f"data: {json.dumps({'event': 'start', 'query': request.query})}\n\n"

            # Execute query with router
            res = execute_routed_query(request=request, db=db, orchestrator=_agent_orchestrator)

            # Stream steps
            for step in res.steps:
                step_data = {
                    "event": "step",
                    "step": step.model_dump(),
                }
                yield f"data: {json.dumps(step_data)}\n\n"

            # Stream final payload
            final_data = {
                "event": "final",
                "response": res.model_dump(),
            }
            yield f"data: {json.dumps(final_data)}\n\n"
        except Exception as e:
            err_data = {
                "event": "error",
                "message": str(e),
            }
            yield f"data: {json.dumps(err_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

