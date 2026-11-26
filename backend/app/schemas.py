"""Pydantic response models for standard FastAPI metadata, health, and evaluation endpoints."""
from pydantic import BaseModel
from typing import List


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
