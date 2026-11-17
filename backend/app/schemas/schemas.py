"""Pydantic schemas for FastAPI request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language question")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    session_id: Optional[str] = None
    mode: Optional[str] = "hybrid"  # "hybrid", "rule_based", "ml", "gemini"


class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    question: str
    session_id: str
    answer: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    selected_function: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    active_context: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    execution_trace: Optional[List[Dict]] = None
    execution_time_ms: float = 0.0
    source: Optional[str] = None


class StructuredQueryRequest(BaseModel):
    intent: str
    state: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    assessment_year: Optional[str] = None
    parameter: Optional[str] = None


class TraceStep(BaseModel):
    step: int
    name: str
    status: str
    detail: str
    duration_ms: float = 0.0


class QueryResponse(BaseModel):
    status: str
    question: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    selected_function: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None
    execution_trace: Optional[List[Dict]] = None
    execution_time_ms: float = 0.0
    source: Optional[str] = None
    clarification_question: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database_connected: bool
    total_records: int
    assessment_years: List[str]


class MetadataResponse(BaseModel):
    app_name: str
    version: str
    description: str
    total_records: int
    states: int
    districts: int
    assessment_years: List[str]
    data_source: str
    llm_provider: str


class EvaluationSummary(BaseModel):
    total_test_cases: int
    intent_accuracy_pct: float
    entity_accuracy_pct: float
    function_accuracy_pct: float
    db_success_rate_pct: float
    end_to_end_accuracy_pct: float
    unsupported_handling_pct: float
    avg_response_time_ms: float
    passed: int
    failed: int

