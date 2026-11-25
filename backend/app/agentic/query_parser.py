"""Multi-entity, multi-metric, multi-year query parser for Groundwater Agentic AI.

Pure, unit-testable module extracting canonical locations, metrics, years,
and intent from natural-language hydrologic queries.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from backend.app.agentic.tools import ALL_STATES, STATE_ALIASES, ALIAS_MAP
from backend.app.database.connection import SyncSession
from backend.app.database.models import State, District, AssessmentYear


# Canonical supported metrics
VALID_METRICS = {
    "extraction",
    "recharge",
    "extractable_resource",
    "stage_of_extraction",
    "category",
}

AVAILABLE_YEARS = {"2020", "2022", "2023", "2024", "2025", "2026"}

# Common ambiguous district names in India and their candidate states
AMBIGUOUS_DISTRICTS: Dict[str, List[str]] = {
    "aurangabad": ["Bihar", "Maharashtra"],
    "bilaspur": ["Chhattisgarh", "Himachal Pradesh"],
    "pratapgarh": ["Rajasthan", "Uttar Pradesh"],
    "hamirpur": ["Himachal Pradesh", "Uttar Pradesh"],
    "balrampur": ["Chhattisgarh", "Uttar Pradesh"],
}


class LocationEntity(BaseModel):
    state: str
    district: Optional[str] = None
    raw_name: str = ""

    def canonical_str(self) -> str:
        if self.district:
            return f"{self.district}, {self.state}"
        return self.state


class ParsedQuery(BaseModel):
    locations: List[LocationEntity] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    years: List[str] = Field(default_factory=list)
    intent: str = "single_lookup"
    override_note: Optional[str] = None


_DB_LOCATION_CACHE: Optional[Dict[str, Any]] = None


def _get_location_catalog() -> Dict[str, Any]:
    """Load and cache canonical states and districts from SQLite DB once."""
    global _DB_LOCATION_CACHE
    if _DB_LOCATION_CACHE is not None:
        return _DB_LOCATION_CACHE

    catalog = {
        "districts_by_lower": {},  # lower_name -> list of (canonical_district, canonical_state)
        "states_by_lower": {},     # lower_name -> canonical_state
    }

    # Seed with static tools lists
    for st in ALL_STATES:
        catalog["states_by_lower"][st.lower()] = st

    for alias, st in STATE_ALIASES.items():
        catalog["states_by_lower"][alias.lower()] = st

    for alias, (dist, st) in ALIAS_MAP.items():
        catalog["districts_by_lower"].setdefault(alias.lower(), []).append((dist, st))

    try:
        db = SyncSession()
        try:
            db_states = db.query(State).all()
            for s in db_states:
                catalog["states_by_lower"][s.name.lower()] = s.name

            db_dists = db.query(District, State).join(State, District.state_id == State.id).all()
            for d, s in db_dists:
                # Store full name
                d_low = d.name.lower()
                catalog["districts_by_lower"].setdefault(d_low, []).append((d.name, s.name))

                # Handle parenthetical aliases like "Tirupati (Chittoor)"
                m = re.match(r"^(.*?)\s*\((.*?)\)$", d.name)
                if m:
                    main_p = m.group(1).strip().lower()
                    sub_p = m.group(2).strip().lower()
                    if main_p:
                        catalog["districts_by_lower"].setdefault(main_p, []).append((d.name, s.name))
                    if sub_p:
                        catalog["districts_by_lower"].setdefault(sub_p, []).append((d.name, s.name))
        finally:
            db.close()
    except Exception:
        # Fall back gracefully to inlined ALIAS_MAP and ALL_STATES
        pass

    _DB_LOCATION_CACHE = catalog
    return _DB_LOCATION_CACHE


def extract_locations(question: str, selected_state: Optional[str] = None) -> List[LocationEntity]:
    """Extract an ordered, de-duplicated list of canonical locations mentioned in the query.

    Longest-match-first with strict word boundaries so 'Delhi' does not swallow 'South Delhi'.
    Preserves order of appearance in the question.
    """
    if not question:
        return []

    # Strip any appended selected context instructions before parsing query entities
    if "Selected context ->" in question:
        question = question.split("Selected context ->")[0].strip()

    catalog = _get_location_catalog()
    q_text = question
    q_lower = question.lower()

    # Build candidates list sorted by length descending
    # Tuples of (pattern_str, is_district, target_tuple)
    candidates = []

    # 1. District patterns
    for name_low, pairs in catalog["districts_by_lower"].items():
        if len(name_low) >= 3:
            candidates.append((name_low, True, pairs))

    # 2. State patterns
    for name_low, canonical_st in catalog["states_by_lower"].items():
        if len(name_low) >= 2:
            candidates.append((name_low, False, canonical_st))

    # Sort longest first
    candidates.sort(key=lambda x: len(x[0]), reverse=True)

    # Find all matches with character start positions
    # (start_idx, end_idx, LocationEntity)
    matches: List[Tuple[int, int, LocationEntity]] = []

    for name_low, is_district, target in candidates:
        # Strict word boundary pattern, escaping any special regex chars
        pattern = r"\b" + re.escape(name_low) + r"\b"
        for m in re.finditer(pattern, q_lower):
            start, end = m.span()

            # Disambiguate if district
            if is_district:
                pairs = target  # list of (dist, state)
                chosen_dist, chosen_st = pairs[0]
                if len(pairs) > 1 and selected_state:
                    for d_cand, s_cand in pairs:
                        if s_cand.lower() == selected_state.lower():
                            chosen_dist, chosen_st = d_cand, s_cand
                            break
                loc = LocationEntity(state=chosen_st, district=chosen_dist, raw_name=m.group(0))
            else:
                loc = LocationEntity(state=target, district=None, raw_name=m.group(0))

            matches.append((start, end, loc))

    # Remove overlapping matches preferring the longer match
    matches.sort(key=lambda m: (m[0], -(m[1] - m[0])))

    filtered_matches: List[Tuple[int, int, LocationEntity]] = []
    occupied_spans: List[Tuple[int, int]] = []

    for start, end, loc in matches:
        overlaps = False
        for o_start, o_end in occupied_spans:
            if not (end <= o_start or start >= o_end):
                overlaps = True
                break
        if not overlaps:
            occupied_spans.append((start, end))
            filtered_matches.append((start, end, loc))

    # Sort strictly by order of appearance in question
    filtered_matches.sort(key=lambda m: m[0])

    # De-duplicate while preserving appearance order
    seen_keys: Set[str] = set()
    result: List[LocationEntity] = []

    for _, _, loc in filtered_matches:
        key = f"{loc.state}::{loc.district or ''}"
        if key not in seen_keys:
            seen_keys.add(key)
            result.append(loc)

    # If a district was matched, remove standalone parent state entries (e.g., Pune and Maharashtra -> Pune, Maharashtra)
    district_states = {loc.state.lower() for loc in result if loc.district}
    if district_states:
        result = [
            loc for loc in result
            if loc.district or loc.state.lower() not in district_states
        ]

    return result


def extract_metrics(question: str) -> List[str]:
    """Extract list of requested groundwater metrics from {extraction, recharge, extractable_resource, stage_of_extraction, category}."""
    if not question:
        return []

    if "Selected context ->" in question:
        question = question.split("Selected context ->")[0].strip()

    q_lower = question.lower()
    metrics: List[str] = []

    # Composite synonyms
    if re.search(r"\b(water\s+balance|balance)\b", q_lower):
        return ["extraction", "recharge", "stage_of_extraction"]

    # Extraction synonyms
    if re.search(r"\b(extraction|extracted|pumping|draft|withdrawal|withdrawals)\b", q_lower):
        metrics.append("extraction")

    # Recharge synonyms
    if re.search(r"\b(recharge|recharging|replenishment|monsoon\s+recharge)\b", q_lower):
        metrics.append("recharge")

    # Extractable resource synonyms
    if re.search(r"\b(extractable|extractable\s+resource|availability|available\s+groundwater)\b", q_lower):
        metrics.append("extractable_resource")

    # Stage synonyms
    if re.search(r"\b(stage|stage\s+of\s+extraction|extraction\s+stage|percentage|percent\s+extraction)\b", q_lower):
        metrics.append("stage_of_extraction")

    # Category synonyms
    if re.search(r"\b(category|categorization|classification|over-exploited|critical|semi-critical|safe)\b", q_lower):
        metrics.append("category")

    return list(dict.fromkeys(metrics))


def extract_years(question: str) -> List[str]:
    """Extract and validate assessment cycles mentioned in query."""
    if not question:
        return []

    if "Selected context ->" in question:
        question = question.split("Selected context ->")[0].strip()

    matches = re.findall(r"\b(2020|2022|2023|2024|2025|2026)\b", question)
    return sorted(list(dict.fromkeys(matches)))


def detect_intent(
    question: str,
    locations_count: int = 0,
    years_count: int = 0,
) -> str:
    """Detect high-level execution intent."""
    q_lower = (question or "").lower()

    is_compare_phrasing = bool(
        re.search(r"\b(compare|comparison|versus|vs|vs\.|between|difference|differ|higher\s+than|lower\s+than|exceeds?)\b", q_lower)
    )

    # 1. Multi-location comparison
    if locations_count >= 2 and (is_compare_phrasing or " and " in q_lower or " vs " in q_lower):
        return "compare_locations"

    # 2. Multi-year comparison
    if (years_count >= 2 or re.search(r"\bchange\s+from\b|\bfrom\s+\d{4}\s+to\s+\d{4}\b", q_lower)) and (is_compare_phrasing or "change" in q_lower):
        return "compare_years"

    # 3. Trend analysis
    if re.search(r"\b(trend|historical|trajectory|over\s+time|over\s+the\s+years|timeline)\b", q_lower):
        return "trend"

    # 4. Explanatory / Causal query
    if re.search(r"\b(why|reason|reasons|cause|causes|factors|explain|how\s+did|how\s+has)\b", q_lower):
        return "explain_why"

    return "single_lookup"


def parse_query(question: str, hints: Optional[Dict[str, Any]] = None) -> ParsedQuery:
    """Parse complete query applying the priority rule: Question entities ALWAYS override dropdown context."""
    hints = hints or {}
    selected_state = hints.get("state")
    selected_district = hints.get("district")
    selected_year = hints.get("year")

    # Extract directly from question
    locations = extract_locations(question, selected_state=selected_state)
    metrics = extract_metrics(question)
    years = extract_years(question)

    override_note = None

    # Priority rule: If question specified locations, they win!
    if locations:
        if len(locations) >= 2:
            loc_names = ", ".join(loc.canonical_str() for loc in locations)
            if selected_state and all(loc.state.lower() != selected_state.lower() for loc in locations):
                override_note = f"Using locations from your question ({loc_names}); the selected state '{selected_state}' was ignored."
            elif selected_state:
                override_note = f"Comparing {loc_names} as specified in your question."
    else:
        # Fallback to dropdown context if question named none
        if selected_state:
            loc = LocationEntity(
                state=selected_state,
                district=selected_district if (selected_district and selected_district != "State-level (no district)") else None,
                raw_name=selected_state,
            )
            locations.append(loc)

    # Year fallback to dropdown
    if not years and selected_year:
        years.append(str(selected_year))
    elif not years:
        years.append("2025")

    # Metrics fallback to extraction if empty
    if not metrics:
        metrics.append("extraction")

    intent = detect_intent(question, locations_count=len(locations), years_count=len(years))

    return ParsedQuery(
        locations=locations,
        metrics=metrics,
        years=years,
        intent=intent,
        override_note=override_note,
    )
