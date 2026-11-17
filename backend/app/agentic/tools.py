"""Tool Registry and Tools for the Groundwater Agentic AI Orchestrator.

Wraps existing repository functions with entity normalization (via geo_resolver),
Pydantic input schema validation, and structured JSON output for ReAct loop execution.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import repository
from backend.app.nlp.geo_resolver import resolve_geography

logger = logging.getLogger(__name__)


# ============================================================================
# Argument Models for Function Calling
# ============================================================================

class StageOfExtractionArgs(BaseModel):
    state: str = Field(..., description="State name in India (e.g., 'Punjab', 'Uttar Pradesh').")
    district: Optional[str] = Field(None, description="Optional district name within the state.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class OverexploitedUnitsArgs(BaseModel):
    state: str = Field(..., description="State name in India (e.g., 'Punjab', 'Rajasthan', 'Haryana').")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class CompareAssessmentYearsArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name within the state.")
    parameter: Optional[str] = Field("extraction", description="Parameter to compare: 'extraction', 'recharge', 'stage', or 'extractable'. Default is 'extraction'.")
    year1: str = Field("2020", description="Earlier assessment year (e.g. '2020', '2022').")
    year2: str = Field("2025", description="Later assessment year (e.g. '2025', '2026').")


class GroundwaterExtractionArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name within the state.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class GroundwaterRechargeArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name within the state.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class ExtractableGroundwaterArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name within the state.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class AssessmentCategoryArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class HistoricalDataArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name.")
    parameter: Optional[str] = Field("extraction", description="Parameter name: 'extraction', 'recharge', 'stage', or 'extractable'.")


class StateSummaryArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class CompareLocationsArgs(BaseModel):
    state1: str = Field(..., description="State of first location.")
    district1: str = Field(..., description="District of first location.")
    state2: str = Field(..., description="State of second location.")
    district2: str = Field(..., description="District of second location.")
    parameter: Optional[str] = Field("extraction", description="Parameter to compare ('extraction', 'recharge', 'stage', 'extractable').")
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class CountrySummaryArgs(BaseModel):
    assessment_year: Optional[str] = Field("2025", description="Assessment year (e.g. '2020', '2022', '2023', '2024', '2025', '2026'). Default is '2025'.")


class DistrictsInStateArgs(BaseModel):
    state: str = Field(..., description="State name in India.")


# ============================================================================
# Geographic Normalization Helper
# ============================================================================

def _normalize_geo_args(state: Optional[str], district: Optional[str], db: Session) -> tuple[Optional[str], Optional[str]]:
    """Normalize state and district names using the database-backed geo_resolver."""
    if not state and not district:
        return state, district

    # Check if district was supplied or if state might actually be a district
    query_str = f"{district}, {state}" if district and state else (district or state or "")
    resolved = resolve_geography(query_str, db)

    norm_state = resolved.get("state") or state
    norm_district = resolved.get("district") or district

    # If user provided a district explicitly, also try resolving just the district
    if district and not resolved.get("district"):
        dist_res = resolve_geography(district, db)
        if dist_res.get("district"):
            norm_district = dist_res.get("district")
        if not norm_state and dist_res.get("state"):
            norm_state = dist_res.get("state")

    # If state was resolved and matched, use it
    if state and not resolved.get("state"):
        st_res = resolve_geography(state, db)
        if st_res.get("state"):
            norm_state = st_res.get("state")

    return norm_state, norm_district


# ============================================================================
# Tool Wrapper Class
# ============================================================================

class Tool:
    def __init__(
        self,
        name: str,
        description: str,
        args_model: Type[BaseModel],
        func: Callable,
    ):
        self.name = name
        self.description = description
        self.args_model = args_model
        self.func = func

    def get_json_schema(self) -> Dict[str, Any]:
        """Return OpenAI / universal function calling schema."""
        raw_schema = self.args_model.model_json_schema()
        # Clean schema for strict LLM tool call compatibility
        clean_schema = {
            "type": "object",
            "properties": raw_schema.get("properties", {}),
            "required": raw_schema.get("required", []),
        }
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": clean_schema,
            },
        }

    def execute(self, db: Session, **kwargs) -> Dict[str, Any]:
        """Execute tool safely with argument parsing, geo-normalization, and exception catching."""
        try:
            # Validate args against Pydantic model
            validated_args = self.args_model(**kwargs).model_dump()
        except Exception as e:
            logger.warning(f"Argument validation failed for tool '{self.name}': {e}")
            return {
                "status": "error",
                "tool": self.name,
                "error_type": "invalid_arguments",
                "message": f"Invalid arguments for {self.name}: {str(e)}",
                "data": None,
            }

        try:
            # Perform geo normalization if state or district are in arguments
            if "state" in validated_args or "district" in validated_args:
                norm_state, norm_district = _normalize_geo_args(
                    validated_args.get("state"),
                    validated_args.get("district"),
                    db,
                )
                if norm_state:
                    validated_args["state"] = norm_state
                if "district" in validated_args:
                    validated_args["district"] = norm_district

            # Handle compare_locations with dual geo normalization
            if "state1" in validated_args and "district1" in validated_args:
                s1, d1 = _normalize_geo_args(validated_args.get("state1"), validated_args.get("district1"), db)
                s2, d2 = _normalize_geo_args(validated_args.get("state2"), validated_args.get("district2"), db)
                if s1: validated_args["state1"] = s1
                if d1: validated_args["district1"] = d1
                if s2: validated_args["state2"] = s2
                if d2: validated_args["district2"] = d2

            # Execute underlying repository function
            result = self.func(db, **validated_args)

            # Ensure output is a dict and has tool execution metadata
            if isinstance(result, dict):
                result["tool_called"] = self.name
                result["resolved_args"] = validated_args
                return result
            return {
                "status": "success",
                "tool_called": self.name,
                "data": result,
                "resolved_args": validated_args,
            }
        except Exception as e:
            logger.error(f"Error executing tool '{self.name}': {e}", exc_info=True)
            return {
                "status": "error",
                "tool": self.name,
                "error_type": "execution_error",
                "message": f"Execution failed for {self.name}: {str(e)}",
                "data": None,
            }


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_json_schema() for tool in self._tools.values()]

    def execute(self, name: str, db: Session, **kwargs) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {
                "status": "error",
                "tool": name,
                "error_type": "unknown_tool",
                "message": f"Tool '{name}' is not recognized. Available tools: {list(self._tools.keys())}",
                "data": None,
            }
        return tool.execute(db, **kwargs)

    def _register_default_tools(self) -> None:
        """Register all groundwater analysis tools wrapping repository functions."""

        # 1. get_stage_of_extraction
        self.register(Tool(
            name="get_stage_of_extraction",
            description="Get the stage of groundwater extraction (percentage) and category for a state or district. Essential for evaluating over-exploitation status.",
            args_model=StageOfExtractionArgs,
            func=repository.get_stage_of_extraction,
        ))

        # 2. get_overexploited_units
        self.register(Tool(
            name="get_overexploited_units",
            description="Get the list and count of over-exploited assessment units/districts (stage > 100%) in a specified state.",
            args_model=OverexploitedUnitsArgs,
            func=repository.get_overexploited_units,
        ))

        # 3. compare_assessment_years
        self.register(Tool(
            name="compare_assessment_years",
            description="Compare groundwater metrics (extraction, recharge, stage, or extractable) between two assessment years (e.g. 2020 vs 2025 or 2026) for a state or district.",
            args_model=CompareAssessmentYearsArgs,
            func=repository.compare_assessment_years,
        ))

        # 4. get_groundwater_extraction
        self.register(Tool(
            name="get_groundwater_extraction",
            description="Get total groundwater extraction in Ham, with sectoral breakdown (irrigation, domestic, industrial) for a state or district.",
            args_model=GroundwaterExtractionArgs,
            func=repository.get_groundwater_extraction,
        ))

        # 5. get_groundwater_recharge
        self.register(Tool(
            name="get_groundwater_recharge",
            description="Get total annual groundwater recharge in Ham (monsoon/non-monsoon, rainfall/other sources) for a state or district.",
            args_model=GroundwaterRechargeArgs,
            func=repository.get_groundwater_recharge,
        ))

        # 6. get_extractable_groundwater
        self.register(Tool(
            name="get_extractable_groundwater",
            description="Get annual extractable groundwater resource (Ham) accounting for natural discharge.",
            args_model=ExtractableGroundwaterArgs,
            func=repository.get_extractable_groundwater,
        ))

        # 7. get_assessment_category
        self.register(Tool(
            name="get_assessment_category",
            description="Get the official CGWB classification (Safe, Semi-Critical, Critical, Over-Exploited) for a state or district.",
            args_model=AssessmentCategoryArgs,
            func=repository.get_assessment_category,
        ))

        # 8. get_historical_groundwater_data
        self.register(Tool(
            name="get_historical_groundwater_data",
            description="Get multi-year historical time series data (2020, 2022, 2023, 2024, 2025, 2026) for a location and parameter.",
            args_model=HistoricalDataArgs,
            func=repository.get_historical_groundwater_data,
        ))

        # 9. get_state_summary
        self.register(Tool(
            name="get_state_summary",
            description="Get a comprehensive state-level groundwater summary including recharge, extraction, extractable resource, and stage.",
            args_model=StateSummaryArgs,
            func=repository.get_state_summary,
        ))

        # 10. compare_locations
        self.register(Tool(
            name="compare_locations",
            description="Compare groundwater parameters between two different locations (e.g. two districts or two states).",
            args_model=CompareLocationsArgs,
            func=repository.compare_locations,
        ))

        # 11. get_country_summary
        self.register(Tool(
            name="get_country_summary",
            description="Get national-level summary metrics across India for a given assessment year.",
            args_model=CountrySummaryArgs,
            func=repository.get_country_summary,
        ))

        # 12. get_districts_in_state
        self.register(Tool(
            name="get_districts_in_state",
            description="Get list of available assessment districts in a state.",
            args_model=DistrictsInStateArgs,
            func=repository.get_districts_in_state,
        ))


# Global default registry instance
default_tool_registry = ToolRegistry()
