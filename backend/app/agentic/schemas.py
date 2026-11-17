"""Pydantic V2 schemas for Agentic & Generative AI workflows."""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    """Incoming query request for the Agentic pipeline."""
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language question or complex reasoning prompt")
    mode: Optional[Literal["auto", "deterministic", "agentic"]] = Field(default="auto", description="Execution routing mode")
    year: Optional[str] = Field(default=None, description="Optional assessment year filter hint")
    state: Optional[str] = Field(default=None, description="Optional state filter hint")
    district: Optional[str] = Field(default=None, description="Optional district filter hint")


class AgentStep(BaseModel):
    """A discrete reasoning step recorded in the ReAct planning trace."""
    step_number: int
    thought: str = Field(..., description="Agent reasoning before taking action")
    tool: str = Field(..., description="Tool name called")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to tool")
    result_summary: str = Field(..., description="Short summary of tool observation")
    latency_ms: float = 0.0


class EvidenceItem(BaseModel):
    """A verified data record retrieved by a tool execution and stored in the Evidence Ledger."""
    tool: str
    args: Dict[str, Any]
    data: Any
    unit: str = "Ham"
    year: Optional[str] = None
    location: str = "N/A"
    source: str = "CGWB National Compilation"
    source_url: Optional[str] = None
    verification_status: str = "VERIFIED"
    latency_ms: float = 0.0


class NumericVerificationResult(BaseModel):
    """Result of the anti-hallucination numeric guard."""
    passed: bool = True
    checked_numbers: List[float] = Field(default_factory=list)
    unverified_numbers: List[float] = Field(default_factory=list)
    regenerated: bool = False
    fallback_used: bool = False
    notes: Optional[str] = None


class StructuredAnswer(BaseModel):
    """Structured, verified response payload synthesized by the generative layer."""
    summary: str = Field(..., description="Concise executive summary grounded in verified data")
    numeric_breakdown: List[Dict[str, Any]] = Field(default_factory=list, description="Tabular verified metrics")
    trend_analysis: Optional[str] = Field(default=None, description="Trajectory and temporal change across assessment cycles")
    interpretation: Optional[str] = Field(default=None, description="General hydrogeological context (explicitly non-factual)")
    policy_recommendations: List[str] = Field(default_factory=list, description="AI-generated conservation recommendations (explicitly labeled)")
    limitations: Optional[str] = Field(default=None, description="Data availability boundaries or missing cycle caveats")


class AgentQueryResponse(BaseModel):
    """Complete response returned by the Agentic endpoint."""
    status: str = "success"
    query: str
    mode_used: str = "agentic"  # "agentic", "deterministic", "deterministic_fallback"
    answer: StructuredAnswer
    text_answer: str = Field(..., description="Formatted markdown string for simple display")
    steps: List[AgentStep] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    verification: NumericVerificationResult
    latency_ms: float = 0.0
    model: str = "gemini-2.5-flash"


class AgentStatusResponse(BaseModel):
    """Status endpoint reporting provider, model, and capabilities."""
    provider: str
    model: str
    api_key_configured: bool
    agentic_enabled: bool
    max_steps: int
    timeout_seconds: int
