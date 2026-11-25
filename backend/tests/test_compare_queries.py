"""Test suite for Multi-Entity, Multi-Metric, and Multi-Year Comparison Queries."""

import pytest
from unittest.mock import patch

from backend.app.agentic.query_parser import (
    extract_locations,
    extract_metrics,
    extract_years,
    detect_intent,
    parse_query,
)
from backend.app.agentic.orchestrator import AgenticOrchestrator
from backend.app.agentic.llm_client import MockLLMClient
from backend.app.agentic.verifier import NumericVerifier


# ============================================================================
# Section A / G: Parser Unit Tests
# ============================================================================

def test_extract_locations_ordered():
    """extract_locations on the Punjab/Haryana question returns ['Punjab', 'Haryana'] in order."""
    q = "Compare groundwater extraction and recharge between Punjab and Haryana in 2025."
    locs = extract_locations(q)
    names = [loc.state for loc in locs]
    assert names == ["Punjab", "Haryana"]
    assert locs[0].district is None
    assert locs[1].district is None


def test_extract_metrics_multi():
    """extract_metrics returns both extraction and recharge."""
    q = "Compare groundwater extraction and recharge between Punjab and Haryana in 2025."
    metrics = extract_metrics(q)
    assert "extraction" in metrics
    assert "recharge" in metrics


def test_south_delhi_not_truncated_and_alias_normalization():
    """'South Delhi' is not truncated to 'Delhi'; an alias such as 'Prayagraj' normalises."""
    q_delhi = "Show groundwater assessment for South Delhi in 2025."
    locs_delhi = extract_locations(q_delhi)
    assert len(locs_delhi) >= 1
    # South Delhi should be recognized with district 'South Delhi', not truncated
    assert locs_delhi[0].district == "South Delhi"
    assert locs_delhi[0].state == "Delhi"

    q_alias = "Show groundwater extraction for Prayagraj in 2024."
    locs_alias = extract_locations(q_alias)
    assert len(locs_alias) >= 1
    assert "Allahabad (Prayagraj)" in locs_alias[0].district
    assert locs_alias[0].state == "Uttar Pradesh"


def test_intent_detection():
    """Intent detection for compare / vs / between / change-from-to phrasing."""
    assert detect_intent("Compare groundwater between Punjab and Haryana", locations_count=2) == "compare_locations"
    assert detect_intent("Extraction in Punjab vs Haryana", locations_count=2) == "compare_locations"
    assert detect_intent("Difference between Ludhiana and Amritsar", locations_count=2) == "compare_locations"
    assert detect_intent("How did extraction change from 2020 to 2025 in Pune?", years_count=2) == "compare_years"
    assert detect_intent("Compare 2022 and 2024 for Pune", years_count=2) == "compare_years"
    assert detect_intent("Why is Ludhiana overexploited?", locations_count=1) == "explain_why"
    assert detect_intent("Show historical trend for Rajasthan", locations_count=1) == "trend"
    assert detect_intent("Show groundwater extraction for Punjab in 2025", locations_count=1) == "single_lookup"


def test_question_entities_override_dropdown():
    """The question's entities override the dropdown context."""
    q = "Compare groundwater extraction and recharge between Punjab and Haryana in 2025."
    parsed = parse_query(q, hints={"state": "Gujarat", "year": "2023"})

    loc_states = [loc.state for loc in parsed.locations]
    assert loc_states == ["Punjab", "Haryana"]
    # Dropdown state Gujarat is overridden
    assert "Gujarat" not in loc_states
    assert parsed.override_note is not None
    assert "Gujarat" in parsed.override_note or "Punjab" in parsed.override_note


def test_sql_injection_safety():
    """SQL-injection-like text inside location names is not matched and is handled safely."""
    malicious = "Compare Punjab'; DROP TABLE states; -- and Haryana in 2025"
    locs = extract_locations(malicious)
    names = [loc.state for loc in locs]
    assert names == ["Punjab", "Haryana"]
    for loc in locs:
        assert "DROP TABLE" not in loc.state
        assert ";" not in loc.state


# ============================================================================
# Section B & C & D: Behaviour Tests (Template, Auto, Agentic)
# ============================================================================

@pytest.mark.asyncio
async def test_punjab_vs_haryana_template_mode():
    """Punjab vs Haryana in Template mode returns BOTH states, BOTH metrics, and differences."""
    orc = AgenticOrchestrator(llm_client=MockLLMClient())
    res = await orc.run(
        "Compare groundwater extraction and recharge between Punjab and Haryana in 2025.",
        mode="template",
        hints={"state": "Punjab", "year": "2025"},
    )
    assert res.mode_used == "template"
    assert res.comparison_data is not None
    assert set(res.comparison_data["locations"]) == {"Punjab", "Haryana"}

    # Must contain both extraction and recharge in rows
    params = [r["parameter"] for r in res.comparison_data["rows"]]
    assert "Total Annual Extraction" in params
    assert "Total Annual Recharge" in params

    # Numeric breakdown must have at least 4 base rows plus difference rows
    assert len(res.answer.get("numeric_breakdown", [])) >= 4

    # Verifier passed
    assert res.verification.passed is True
    assert res.completeness.complete is True


@pytest.mark.asyncio
async def test_punjab_vs_haryana_agentic_mode():
    """Punjab vs Haryana in Agentic mode executes tools for both states and both metrics."""
    orc = AgenticOrchestrator(llm_client=MockLLMClient())
    res = await orc.run(
        "Compare groundwater extraction and recharge between Punjab and Haryana in 2025.",
        mode="agentic",
        hints={"state": "Punjab", "year": "2025"},
    )
    assert res.mode_used == "agentic"
    assert len(res.steps) >= 4
    assert res.comparison_data is not None
    assert res.verification.passed is True
    assert res.completeness.complete is True


@pytest.mark.asyncio
async def test_completeness_guard_flagged_on_missing_location():
    """A compare answer is flagged incomplete if one location is forced to be missing."""
    orc = AgenticOrchestrator(llm_client=MockLLMClient())

    # Monkeypatch tool registry run to fail for Haryana
    orig_run = orc.tool_registry.run

    def mock_run(name, **kwargs):
        if kwargs.get("state") == "Haryana":
            return {"error": "Location data unavailable"}
        return orig_run(name, **kwargs)

    with patch.object(orc.tool_registry, "run", side_effect=mock_run):
        res = await orc.run(
            "Compare groundwater extraction between Punjab and Haryana in 2025.",
            mode="template",
            hints={"state": "Punjab"},
        )
        assert res.completeness.complete is False
        assert any("Haryana" in m for m in res.completeness.missing_locations)
        assert any("Haryana" in lim for lim in res.answer.get("limitations", []))


@pytest.mark.asyncio
async def test_compare_years_pune():
    """'Compare groundwater extraction stage in Pune for 2022 and 2024.' uses compare_assessment_years."""
    orc = AgenticOrchestrator(llm_client=MockLLMClient())
    res = await orc.run(
        "Compare groundwater extraction stage in Pune for 2022 and 2024.",
        mode="template",
    )
    assert any(step.tool_called == "compare_assessment_years" for step in res.steps)
    assert res.verification.passed is True


@pytest.mark.asyncio
async def test_single_entity_no_regression():
    """Single-entity queries still return a single result without comparison_data."""
    orc = AgenticOrchestrator(llm_client=MockLLMClient())
    res = await orc.run(
        "Show the groundwater summary for Rajasthan in 2024.",
        mode="template",
        hints={"state": "Rajasthan", "year": "2024"},
    )
    assert res.comparison_data is None
    assert res.verification.passed is True
    assert len(res.answer.get("numeric_breakdown", [])) >= 1


def test_verifier_accepts_derived_and_rejects_hallucination():
    """The verifier rejects a hallucinated number and accepts the derived difference and percentage values."""
    verifier = NumericVerifier()

    evidence = [
        {
            "tool_name": "get_groundwater_extraction",
            "arguments": {"state": "Punjab"},
            "result": {"values": {"total_annual_extraction_ham": 2000.0}},
            "unit": "Ham",
            "year": "2025",
        },
        {
            "tool_name": "get_groundwater_extraction",
            "arguments": {"state": "Haryana"},
            "result": {"values": {"total_annual_extraction_ham": 1000.0}},
            "unit": "Ham",
            "year": "2025",
        },
        {
            "tool_name": "compute_comparison_derived",
            "arguments": {},
            "result": {
                "values": {
                    "difference": 1000.0,
                    "absolute_difference": 1000.0,
                    "percentage_difference": 100.0,
                }
            },
            "unit": "Ham",
            "year": "2025",
        },
    ]

    # Valid answer with derived numbers
    valid_answer = {
        "summary": "Extraction in Punjab is 2,000 Ham, 100.00% higher than Haryana's 1,000 Ham with difference 1,000 Ham.",
        "numeric_breakdown": [{"value": 2000.0}, {"value": 1000.0}],
    }
    res_valid = verifier.verify(valid_answer, evidence)
    assert res_valid.passed is True

    # Hallucinated answer with an invented figure 75432.0
    hallucinated_answer = {
        "summary": "Total groundwater extraction reached 75,432.00 Ham in the region.",
        "numeric_breakdown": [{"value": 75432.0}],
    }
    res_invalid = verifier.verify(hallucinated_answer, evidence)
    assert res_invalid.passed is False
