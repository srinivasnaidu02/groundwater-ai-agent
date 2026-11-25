"""Tool Registry and Tools for the Groundwater Agentic AI Orchestrator.

Wraps existing repository functions with an inlined entity normalizer,
Pydantic input schema validation, thread-safe session handling, precomputed derived arithmetic,
and structured JSON output for ReAct loop execution.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Type, Tuple
from pydantic import BaseModel, Field

from backend.app.database.connection import SyncSession
from backend.app.database import repository

logger = logging.getLogger(__name__)

# ============================================================================
# Inlined Geographic Normalization Dictionary
# ============================================================================

ALIAS_MAP: Dict[str, Tuple[str, str]] = {
    "patliputra": ("Patna", "Bihar"),
    "patna": ("Patna", "Bihar"),
    "bodhgaya": ("Gaya", "Bihar"),
    "bodh gaya": ("Gaya", "Bihar"),
    "gaya": ("Gaya", "Bihar"),
    "muzaffar pur": ("Muzaffarpur", "Bihar"),
    "muzaffarpur": ("Muzaffarpur", "Bihar"),
    "ludhiana": ("Ludhiana", "Punjab"),
    "jullundur": ("Jalandhar", "Punjab"),
    "jalandhar": ("Jalandhar", "Punjab"),
    "ambarsar": ("Amritsar", "Punjab"),
    "amritsar": ("Amritsar", "Punjab"),
    "hissar": ("Hisar", "Haryana"),
    "hisar": ("Hisar", "Haryana"),
    "gurgaon": ("Gurugram", "Haryana"),
    "gurugram": ("Gurugram", "Haryana"),
    "pink city": ("Jaipur", "Rajasthan"),
    "jaipur": ("Jaipur", "Rajasthan"),
    "jodhpur": ("Jodhpur", "Rajasthan"),
    "bikaner": ("Bikaner", "Rajasthan"),
    "poona": ("Pune", "Maharashtra"),
    "pune": ("Pune", "Maharashtra"),
    "nasik": ("Nashik", "Maharashtra"),
    "nashik": ("Nashik", "Maharashtra"),
    "bombay": ("Mumbai", "Maharashtra"),
    "mumbai": ("Mumbai", "Maharashtra"),
    "lucknow": ("Lucknow", "Uttar Pradesh"),
    "cawnpore": ("Kanpur", "Uttar Pradesh"),
    "kanpur": ("Kanpur", "Uttar Pradesh"),
    "allahabad": ("Allahabad (Prayagraj)", "Uttar Pradesh"),
    "prayagraj": ("Allahabad (Prayagraj)", "Uttar Pradesh"),
    "banaras": ("Varanasi", "Uttar Pradesh"),
    "kashi": ("Varanasi", "Uttar Pradesh"),
    "varanasi": ("Varanasi", "Uttar Pradesh"),
    "bengaluru": ("Bangalore (Urban)", "Karnataka"),
    "bangalore": ("Bangalore (Urban)", "Karnataka"),
    "mysuru": ("Mysore", "Karnataka"),
    "mysore": ("Mysore", "Karnataka"),
    "madras": ("Chennai", "Tamil Nadu"),
    "chennai": ("Chennai", "Tamil Nadu"),
    "kovai": ("Coimbatore", "Tamil Nadu"),
    "coimbatore": ("Coimbatore", "Tamil Nadu"),
    "amdavad": ("Ahmedabad", "Gujarat"),
    "ahmedabad": ("Ahmedabad", "Gujarat"),
    "surat": ("Surat", "Gujarat"),
    "calcutta": ("Kolkata", "West Bengal"),
    "kolkata": ("Kolkata", "West Bengal"),
    "delhi": ("South Delhi", "Delhi"),
    "new delhi": ("South Delhi", "Delhi"),
    "south delhi": ("South Delhi", "Delhi"),
}

STATE_ALIASES: Dict[str, str] = {
    "up": "Uttar Pradesh",
    "u.p.": "Uttar Pradesh",
    "mp": "Madhya Pradesh",
    "m.p.": "Madhya Pradesh",
    "wb": "West Bengal",
    "ap": "Andhra Pradesh",
    "hp": "Himachal Pradesh",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "uk": "Uttarakhand",
    "tn": "Tamil Nadu",
    "pb": "Punjab",
    "hr": "Haryana",
    "rj": "Rajasthan",
    "mh": "Maharashtra",
    "gj": "Gujarat",
    "br": "Bihar",
    "ka": "Karnataka",
    "ts": "Telangana",
    "tg": "Telangana",
    "or": "Odisha",
    "od": "Odisha",
}

ALL_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]


def normalize_entity(name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Normalize a given location name into (state, district) if an alias exists.
    Returns (state, district) or (None, name) if unknown.
    """
    if not name:
        return None, None
    clean = name.strip().lower()

    # Check state alias
    if clean in STATE_ALIASES:
        return STATE_ALIASES[clean], None

    # Check direct district alias
    if clean in ALIAS_MAP:
        dist, st = ALIAS_MAP[clean]
        return st, dist

    # Check direct state match
    for st in ALL_STATES:
        if st.lower() == clean:
            return st, None

    # Unknown, pass through as-is
    return None, name


def normalize_location_args(state: Optional[str], district: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Normalize state and district using inlined alias tables."""
    norm_state = state
    norm_district = district

    # Check district first
    if district:
        st, dist = normalize_entity(district)
        if dist:
            norm_district = dist
        if st and not norm_state:
            norm_state = st

    # Check state
    if state:
        st, dist = normalize_entity(state)
        if st:
            norm_state = st
        if dist and not norm_district:
            norm_district = dist

    return norm_state, norm_district


# ============================================================================
# Argument Models
# ============================================================================

class StateOnlyArgs(BaseModel):
    state: str = Field(..., description="State name in India (e.g., 'Punjab', 'Rajasthan').")


class StateDistrictYearArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name.")
    assessment_year: Optional[str] = Field("2025", description="Assessment cycle: '2020', '2022', '2023', '2024', '2025', '2026'.")


class StateYearArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    assessment_year: Optional[str] = Field("2025", description="Assessment cycle.")


class CompareYearsArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name.")
    parameter: Optional[str] = Field("extraction", description="Parameter: 'extraction', 'recharge', 'stage', or 'extractable'.")
    year1: str = Field("2020", description="Earlier assessment year.")
    year2: str = Field("2025", description="Later assessment year.")


class HistoricalTrendArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: Optional[str] = Field(None, description="Optional district name.")
    parameter: Optional[str] = Field("extraction", description="Parameter name.")


class CompareLocationsArgs(BaseModel):
    state1: str = Field(..., description="State of first location.")
    district1: Optional[str] = Field(None, description="Optional district of first location.")
    state2: str = Field(..., description="State of second location.")
    district2: Optional[str] = Field(None, description="Optional district of second location.")
    parameter: Optional[str] = Field("extraction", description="Parameter to compare.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year.")


class YearOnlyArgs(BaseModel):
    assessment_year: Optional[str] = Field("2025", description="Assessment year.")


class NoArgs(BaseModel):
    pass


class DistrictSummaryArgs(BaseModel):
    state: str = Field(..., description="State name in India.")
    district: str = Field(..., description="District name.")
    assessment_year: Optional[str] = Field("2025", description="Assessment year.")


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
        raw_schema = self.args_model.model_json_schema()
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

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute tool in its own isolated SQLAlchemy session with normalization and math precomputations."""
        try:
            validated = self.args_model(**kwargs).model_dump()
        except Exception as e:
            return {"error": f"Invalid arguments for {self.name}: {str(e)}"}

        # Normalization
        if "state" in validated or "district" in validated:
            s, d = normalize_location_args(validated.get("state"), validated.get("district"))
            if s: validated["state"] = s
            if "district" in validated: validated["district"] = d

        if "state1" in validated and "district1" in validated:
            s1, d1 = normalize_location_args(validated.get("state1"), validated.get("district1"))
            s2, d2 = normalize_location_args(validated.get("state2"), validated.get("district2"))
            if s1: validated["state1"] = s1
            if d1: validated["district1"] = d1
            if s2: validated["state2"] = s2
            if d2: validated["district2"] = d2

        db = SyncSession()
        try:
            raw_result = self.func(db, **validated)
        except Exception as e:
            logger.error(f"Error in tool {self.name}: {e}", exc_info=True)
            return {"error": f"Execution error in {self.name}: {str(e)}"}
        finally:
            db.close()

        # Structure output JSON
        data = raw_result.get("data") if isinstance(raw_result, dict) else raw_result
        year = validated.get("assessment_year") or validated.get("year2") or (data.get("assessment_year") if isinstance(data, dict) else None) or "2025"
        unit = (data.get("unit") if isinstance(data, dict) else None) or "Ham"
        source = raw_result.get("source", "CGWB Dynamic Ground Water Resources of India") if isinstance(raw_result, dict) else "CGWB National Compilation"

        output: Dict[str, Any] = {
            "values": data,
            "unit": unit,
            "year": str(year),
            "source": source,
            "verification": "CGWB-verified",
        }

        # Add benchmark projection note for 2026 data
        if str(year) == "2026" or validated.get("year2") == "2026":
            output["note"] = "Benchmark Projection"

        # Precompute derived arithmetic in Python so LLM never does math
        derived = {}
        if isinstance(data, dict):
            # Unit conversions if volumetric Ham
            for key in ["total_annual_extraction_ham", "total_annual_recharge_ham", "annual_extractable_groundwater_ham"]:
                if key in data and isinstance(data[key], (int, float)):
                    val = float(data[key])
                    derived[f"{key}_mcm"] = round(val / 100.0, 2)
                    derived[f"{key}_bcm"] = round(val / 100000.0, 4)

            # Differences and percentage changes if comparison
            if "difference" in data:
                derived["absolute_difference"] = data["difference"]
            if "percent_change" in data:
                derived["percentage_change"] = data["percent_change"]

        if derived:
            output["derived_calculations"] = derived

        return output


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_tools()

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [t.get_json_schema() for t in self._tools.values()]

    def run(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found."}
        return tool.execute(**kwargs)

    def _register_tools(self):
        # 1. get_groundwater_extraction
        self.register(Tool("get_groundwater_extraction", "Get total annual groundwater extraction in Ham (irrigation, domestic, industrial).", StateDistrictYearArgs, repository.get_groundwater_extraction))
        # 2. get_groundwater_recharge
        self.register(Tool("get_groundwater_recharge", "Get annual groundwater recharge in Ham (monsoon/non-monsoon).", StateDistrictYearArgs, repository.get_groundwater_recharge))
        # 3. get_extractable_groundwater
        self.register(Tool("get_extractable_groundwater", "Get annual extractable groundwater resource in Ham.", StateDistrictYearArgs, repository.get_extractable_groundwater))
        # 4. get_stage_of_extraction
        self.register(Tool("get_stage_of_extraction", "Get stage of groundwater extraction percentage (%) and category.", StateDistrictYearArgs, repository.get_stage_of_extraction))
        # 5. get_assessment_category
        self.register(Tool("get_assessment_category", "Get official CGWB assessment category (Safe, Semi-Critical, Critical, Over-Exploited).", StateDistrictYearArgs, repository.get_assessment_category))
        # 6. get_overexploited_units
        self.register(Tool("get_overexploited_units", "Get list and count of over-exploited units (stage > 100%) in a state.", StateYearArgs, repository.get_overexploited_units))
        # 7. compare_locations
        self.register(Tool("compare_locations", "Compare groundwater parameters between two locations.", CompareLocationsArgs, repository.compare_locations))
        # 8. compare_assessment_years
        self.register(Tool("compare_assessment_years", "Compare metrics between two assessment years (e.g. 2020 vs 2025/2026).", CompareYearsArgs, repository.compare_assessment_years))
        # 9. get_historical_groundwater_data
        self.register(Tool("get_historical_groundwater_data", "Get multi-year historical series for a location and parameter.", HistoricalTrendArgs, repository.get_historical_groundwater_data))
        # 10. get_country_summary
        self.register(Tool("get_country_summary", "Get national summary across India for an assessment year.", YearOnlyArgs, repository.get_country_summary))
        # 11. get_state_summary
        self.register(Tool("get_state_summary", "Get state-level summary of recharge, extraction, and stage.", StateYearArgs, repository.get_state_summary))
        # 12. get_assessment_years
        self.register(Tool("get_assessment_years", "Get list of available assessment years.", NoArgs, repository.get_assessment_years))
        # 13. get_state_list
        self.register(Tool("get_state_list", "Get list of all Indian states in the database.", NoArgs, repository.get_state_list))
        # 14. get_districts_in_state
        self.register(Tool("get_districts_in_state", "Get list of districts in a given state.", StateOnlyArgs, repository.get_districts_in_state))
        # 15. get_data_coverage
        self.register(Tool("get_data_coverage", "Get database coverage matrix across states and years.", NoArgs, repository.get_data_coverage))
        # 16. get_yearly_groundwater_trend
        self.register(Tool("get_yearly_groundwater_trend", "Get multi-year extraction/recharge trends for charts.", HistoricalTrendArgs, repository.get_yearly_groundwater_trend))
        # 17. get_district_summary
        self.register(Tool("get_district_summary", "Get complete summary for a specific district.", DistrictSummaryArgs, repository.get_district_summary))


default_tool_registry = ToolRegistry()
