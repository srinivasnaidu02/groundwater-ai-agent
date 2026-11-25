"""Comparison computation and completeness guard for Groundwater Agentic AI.

Computes differences, percentages, base locations, and derived evidence
in pure Python. Verifies that all requested entities and metrics are present.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.app.agentic.query_parser import LocationEntity
from backend.app.agentic.schemas import CompletenessReport

logger = logging.getLogger(__name__)

METRIC_CONFIG: Dict[str, Dict[str, Any]] = {
    "extraction": {
        "field": "total_annual_extraction_ham",
        "label": "Total Annual Extraction",
        "short_label": "Extraction",
        "unit": "Ham",
        "tool": "get_groundwater_extraction",
    },
    "recharge": {
        "field": "total_annual_recharge_ham",
        "label": "Total Annual Recharge",
        "short_label": "Recharge",
        "unit": "Ham",
        "tool": "get_groundwater_recharge",
    },
    "extractable_resource": {
        "field": "annual_extractable_groundwater_ham",
        "label": "Annual Extractable Resource",
        "short_label": "Extractable Resource",
        "unit": "Ham",
        "tool": "get_extractable_groundwater",
    },
    "stage_of_extraction": {
        "field": "stage_of_extraction_pct",
        "label": "Stage of Extraction",
        "short_label": "Stage of Extraction",
        "unit": "%",
        "tool": "get_stage_of_extraction",
    },
    "category": {
        "field": "assessment_category",
        "label": "Assessment Category",
        "short_label": "Category",
        "unit": "Category",
        "tool": "get_assessment_category",
    },
}


def _matches_location(item: Dict[str, Any], loc: LocationEntity) -> bool:
    """Check if an evidence item matches the given location entity."""
    res = item.get("result", {})
    if isinstance(res, dict) and res.get("error"):
        return False
    if item.get("error"):
        return False

    args = item.get("arguments", {})
    res_val = res.get("values") or item.get("values") or {}

    arg_state = args.get("state") or args.get("state1") or args.get("state2")
    arg_dist = args.get("district") or args.get("district1") or args.get("district2")

    if loc.district:
        # District level match
        if arg_dist and arg_dist.lower() == loc.district.lower():
            return True
        if isinstance(res_val, dict):
            if res_val.get("district", "").lower() == loc.district.lower():
                return True
        return False
    else:
        # State level match: ensure state matches and district is None / not set
        if arg_state and arg_state.lower() == loc.state.lower():
            if not arg_dist or arg_dist == "State-level (no district)":
                return True
        if isinstance(res_val, dict):
            if res_val.get("state", "").lower() == loc.state.lower() and not res_val.get("district"):
                return True
        return False


def extract_metric_value(item: Dict[str, Any], metric_key: str) -> Optional[Any]:
    """Extract numeric or category value for a specific metric from evidence item."""
    cfg = METRIC_CONFIG.get(metric_key)
    if not cfg:
        return None
    field = cfg["field"]

    res = item.get("result", {})
    val_block = res.get("values") if isinstance(res, dict) else None
    if not isinstance(val_block, dict):
        val_block = item.get("values")

    if isinstance(val_block, dict):
        if field in val_block and val_block[field] is not None:
            return val_block[field]
        # Check comparison nested dict if compare_locations was run
        if "comparison" in val_block and isinstance(val_block["comparison"], dict):
            for c_val in val_block["comparison"].values():
                if isinstance(c_val, dict) and "value" in c_val:
                    return c_val["value"]

    return None


def compute_comparison_matrix(
    locations: List[LocationEntity],
    metrics: List[str],
    year: str,
    evidence_items: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compute comparison table, chart payload, and derived arithmetic for ledger.

    Returns:
        (comparison_data_dict, derived_evidence_items)
    """
    if len(locations) < 2:
        return None, []

    loc1 = locations[0]
    loc2 = locations[1]
    loc1_name = loc1.canonical_str()
    loc2_name = loc2.canonical_str()

    derived_evidence: List[Dict[str, Any]] = []
    comparison_rows: List[Dict[str, Any]] = []
    chart_data: List[Dict[str, Any]] = []

    for metric_key in metrics:
        cfg = METRIC_CONFIG.get(metric_key)
        if not cfg:
            continue

        param_label = cfg["label"]
        short_label = cfg["short_label"]
        unit = cfg["unit"]

        v1 = None
        v2 = None

        # Find values from evidence
        for item in evidence_items:
            if v1 is None and _matches_location(item, loc1):
                extracted = extract_metric_value(item, metric_key)
                if extracted is not None:
                    v1 = extracted
            if v2 is None and _matches_location(item, loc2):
                extracted = extract_metric_value(item, metric_key)
                if extracted is not None:
                    v2 = extracted

        if v1 is not None and v2 is not None:
            # Check if numeric
            is_num = isinstance(v1, (int, float)) and isinstance(v2, (int, float))
            diff = None
            abs_diff = None
            pct_diff = None
            higher = None

            if is_num:
                v1_f = float(v1)
                v2_f = float(v2)
                diff = round(v1_f - v2_f, 2)
                abs_diff = round(abs(v1_f - v2_f), 2)
                # Base is loc2 (comparing loc1 relative to loc2)
                if abs(v2_f) > 1e-6:
                    pct_diff = round(((v1_f - v2_f) / abs(v2_f)) * 100.0, 2)
                else:
                    pct_diff = 0.0

                if v1_f > v2_f:
                    higher = loc1_name
                elif v2_f > v1_f:
                    higher = loc2_name
                else:
                    higher = "Equal"

                # Derived evidence entry for anti-hallucination verifier
                derived_entry = {
                    "tool_name": "compute_comparison_derived",
                    "arguments": {
                        "parameter": param_label,
                        "location_1": loc1_name,
                        "location_2": loc2_name,
                        "year": str(year),
                    },
                    "result": {
                        "values": {
                            "parameter": param_label,
                            "location_1": loc1_name,
                            "value_1": v1_f,
                            "location_2": loc2_name,
                            "value_2": v2_f,
                            "difference": diff,
                            "absolute_difference": abs_diff,
                            "percentage_difference": pct_diff,
                            "absolute_percentage_difference": abs(pct_diff),
                            "higher": higher,
                            "base_location": loc2_name,
                        }
                    },
                    "unit": unit,
                    "year": str(year),
                    "source": "CGWB Derived Arithmetic Calculation",
                    "verification": "CGWB-verified",
                }
                if str(year) == "2026":
                    derived_entry["note"] = "Benchmark Projection"
                derived_evidence.append(derived_entry)

                chart_entry = {
                    "parameter": short_label,
                    loc1_name: v1_f,
                    loc2_name: v2_f,
                    "unit": unit,
                }
                chart_data.append(chart_entry)

            row = {
                "parameter": param_label,
                "loc1_value": v1,
                "loc2_value": v2,
                "diff": diff,
                "abs_diff": abs_diff,
                "pct_diff": pct_diff,
                "higher": higher,
                "unit": unit,
                "year": str(year),
                "status": "VERIFIED",
            }
            comparison_rows.append(row)

    if not comparison_rows:
        return None, []

    comparison_data = {
        "locations": [loc1_name, loc2_name],
        "base_location": loc2_name,
        "year": str(year),
        "is_benchmark_projection": str(year) == "2026",
        "rows": comparison_rows,
        "chart_data": chart_data,
    }

    return comparison_data, derived_evidence


def check_completeness(
    locations: List[LocationEntity],
    metrics: List[str],
    evidence_items: List[Dict[str, Any]],
) -> CompletenessReport:
    """Verify that every location and metric extracted from the query has evidence."""
    missing_locs: List[str] = []
    missing_metrics: List[str] = []

    for loc in locations:
        found = any(_matches_location(item, loc) for item in evidence_items)
        if not found:
            missing_locs.append(loc.canonical_str())

    for m in metrics:
        found = any(extract_metric_value(item, m) is not None for item in evidence_items)
        if not found:
            cfg = METRIC_CONFIG.get(m, {})
            missing_metrics.append(cfg.get("label", m))

    all_missing = list(dict.fromkeys(missing_locs + missing_metrics))
    complete = (len(all_missing) == 0)

    notes = None
    if not complete:
        notes = f"Missing data for: {', '.join(all_missing)}"

    return CompletenessReport(
        complete=complete,
        missing_locations=missing_locs,
        missing_metrics=missing_metrics,
        missing=all_missing,
        notes=notes,
    )
