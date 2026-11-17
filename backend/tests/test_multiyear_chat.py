"""
Unit & Integration Tests for Verified Assessment Records,
Conversational Sessions, Domain Knowledge, and Historical Comparisons.
"""
import pytest
from app.database.connection import get_sync_db
from app.agent.session_manager import SessionManager
from app.agent.planner import QueryPlanner
from app.nlp.query_parser import parse_question
from app.database import repository as repo
from app.database.functions import execute_function


def test_only_verified_assessment_years_are_available():
    db = get_sync_db()
    years = repo.get_assessment_years(db)
    assert years["status"] == "success"
    assert years["data"] == ["2022", "2025"]

    unverified = repo.get_groundwater_extraction(
        db, state="Bihar", district="Patna", assessment_year="2026"
    )
    assert unverified["status"] == "not_found"


def test_patna_2025_extraction_matches_curated_source_record():
    db = get_sync_db()
    result = execute_function(
        "get_groundwater_extraction",
        db,
        state="Bihar",
        district="Patna",
        assessment_year="2025",
    )
    assert result["status"] == "success"
    assert result["data"]["total_annual_extraction_ham"] == 59747.83
    assert result["data"]["extraction_irrigation_ham"] == 41223.39
    assert result["data"]["extraction_domestic_ham"] == 17061.84
    assert result["data"]["extraction_industrial_ham"] == 1462.64
    assert len(result["provenance"]) >= 1
    p = result["provenance"][0]
    assert p["assessment_year"] == "2025"
    assert p["publication_year"] == "2025"
    assert p["verification_status"] == "VERIFIED"
    assert p["record_verified"] is True
    assert "711d8d476bbf498cd90f8038e7371227.pdf" in p["source_document_url"]
    assert "total_annual_extraction_ham" in p["verified_fields"]


def test_explicit_unavailable_year_does_not_fall_back_to_latest_record():
    db = get_sync_db()
    parsed = parse_question(
        "What is total annual groundwater extraction in Patna district in 2026?"
    )
    result = QueryPlanner(db).plan_and_execute(parsed)

    assert result["status"] == "not_found"
    assert result["parameters"]["assessment_year"] == "2026"
    assert "59,747.83" not in result["answer"]
    assert "Verified data for this location, parameter and assessment year is not currently available in the database." in result["answer"]
    assert "2025" in result["answer"]


def test_compare_assessment_years_repo():
    """Verify compare_assessment_years calculates delta and trend."""
    db = get_sync_db()
    res = repo.compare_assessment_years(
        db, state="Bihar", district="Patna", parameter="extraction", year1="2025", year2="2025"
    )
    assert res["status"] == "success"
    assert res["data"]["year_1"]["year"] == "2025"
    assert res["data"]["year_2"]["year"] == "2025"
    assert "difference" in res["data"]
    assert "percent_change" in res["data"]
    assert res["data"]["trend"] in ["increased", "decreased", "stable"]


def test_historical_trend_repo():
    """Verify historical time series contains records across cycles."""
    db = get_sync_db()
    res = repo.get_historical_groundwater_data(db, state="Bihar", district="Patna", parameter="extraction")
    assert res["status"] == "success"
    assert [item["year"] for item in res["data"]["history"]] == ["2022", "2025"]


def test_conversational_session_memory():
    """Verify session manager retains context across multi-turn interactions."""
    db = get_sync_db()
    sm = SessionManager(db)
    session = sm.get_or_create_session()

    # Turn 1: Ask about Patna 2022 extraction
    q1 = "What is the groundwater extraction in Patna in 2022?"
    p1 = parse_question(q1)
    planner = QueryPlanner(db)
    r1 = planner.plan_and_execute(p1)
    sm.update_context(session, {
        "last_district": "Patna",
        "last_state": "Bihar",
        "last_year": "2022",
        "last_parameter": "extraction",
        "last_intent": "get_groundwater_extraction",
    })

    # Follow-ups may resolve a year, but unavailable records remain unavailable.
    q2 = "What about 2026?"
    p2 = parse_question(q2)
    p2_resolved = sm.apply_context_to_query(p2, session)
    assert p2_resolved["district"] == "Patna"
    assert p2_resolved["state"] == "Bihar"
    assert p2_resolved["assessment_year"] == "2026"

    # Turn 3: "Compare both"
    sm.update_context(session, {"last_year": "2026"})
    q3 = "Compare both"
    p3 = parse_question(q3)
    p3_resolved = sm.apply_context_to_query(p3, session)
    assert p3_resolved["intent"] == "compare_assessment_years"
    assert p3_resolved["district"] == "Patna"


def test_domain_knowledge_responses():
    """Verify domain definitions are handled cleanly without hallucinations."""
    db = get_sync_db()
    sm = SessionManager(db)
    session = sm.get_or_create_session()

    res = sm.resolve_conversational_query("What is an aquifer?", session)
    assert res is not None
    assert "permeable" in res["answer"].lower()

    res2 = sm.resolve_conversational_query("Explain what over-exploited means", session)
    assert res2 is not None
    assert "100%" in res2["answer"]
