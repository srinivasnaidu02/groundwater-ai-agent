"""Pydantic V2 schemas for Agentic AI with LLM function-calling."""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    """User query request for the Agentic AI layer."""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language question")
    mode: Optional[Literal["auto", "agentic", "template"]] = Field(
        default="auto",
        description="Execution mode: auto (default) | agentic | template"
    )
    year: Optional[int] = Field(default=None, description="Optional assessment year filter hint")
    state: Optional[str] = Field(default=None, description="Optional state filter hint")
    district: Optional[str] = Field(default=None, description="Optional district filter hint")


class AgentStep(BaseModel):
    """A discrete step recorded in the ReAct planning trace."""
    step_number: int
    thought: str = Field(..., description="Agent reasoning before taking action")
    tool_called: Optional[str] = Field(default=None, description="Tool called in this step")
    arguments: Optional[Dict[str, Any]] = Field(default=None, description="Arguments passed to tool")
    result_summary: str = Field(..., description="Observation summary from tool")
    latency_ms: float = Field(default=0.0, description="Execution time of tool in ms")


class EvidenceItem(BaseModel):
    """Structured evidence item captured from tool execution."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    unit: str = "Ham"
    year: Optional[Any] = None
    source: str = "CGWB National Compilation"
    verification: str = "CGWB-verified"


class NumericVerification(BaseModel):
    """Anti-hallucination verification summary."""
    passed: bool = True
    checked_numbers: List[float] = Field(default_factory=list)
    regenerated: bool = False
    fallback_used: bool = False


class CompletenessReport(BaseModel):
    """Report on whether all requested entities and metrics are present in evidence."""
    complete: bool = True
    missing_locations: List[str] = Field(default_factory=list)
    missing_metrics: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class AgentQueryResponse(BaseModel):
    """Unified response payload from the Agentic AI layer."""
    answer: Dict[str, Any] = Field(..., description="Structured answer dictionary")
    mode_used: str = Field(..., description="Execution mode used: agentic | template | template_fallback")
    steps: List[AgentStep] = Field(default_factory=list, description="Reasoning trace steps")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Evidence items with provenance")
    citations: List[str] = Field(default_factory=list, description="List of source citations")
    verification: NumericVerification = Field(default_factory=NumericVerification)
    completeness: Optional[CompletenessReport] = None
    comparison_data: Optional[Dict[str, Any]] = None
    override_note: Optional[str] = None
    latency_ms: float = 0.0
    model: str = "gemini-2.5-flash"


class AgentStatusResponse(BaseModel):
    """Status endpoint reporting active provider and capabilities."""
    provider: str
    model: str
    key_configured: bool
    agentic_enabled: bool
