"""Tests for metadata endpoints and guided context validation.

Covers:
1. GET /api/meta/years, /api/meta/states, /api/meta/districts (known state, unknown state).
2. Context validation: unknown state -> 422, district without state -> 422, invalid year -> 422.
3. Context default is used by template path when question omits location/year.
4. Explicit question overrides context (e.g. query asks about Rajasthan when Punjab is in context).
5. SQL-injection-style strings in state/district are safely rejected with 422.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_meta_years_endpoint():
    """Verify /api/meta/years returns assessment years list."""
    res = client.get("/api/meta/years")
    assert res.status_code == 200
    data = res.json()
    assert "years" in data
    assert "assessment_years" in data
    assert "2025" in data["years"]
    assert "2022" in data["years"]


def test_meta_states_endpoint():
    """Verify /api/meta/states returns state list."""
    res = client.get("/api/meta/states")
    assert res.status_code == 200
    data = res.json()
    assert "states" in data
    assert len(data["states"]) >= 28
    assert "Punjab" in data["states"]
    assert "Bihar" in data["states"]


def test_meta_districts_known_state():
    """Verify /api/meta/districts for valid state returns district list."""
    res = client.get("/api/meta/districts?state=Punjab")
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "Punjab"
    assert "districts" in data
    assert "Ludhiana" in data["districts"]
    assert "Jalandhar" in data["districts"]


def test_meta_districts_normalized_alias():
    """Verify state aliases like 'PB' or 'UP' resolve properly in /api/meta/districts."""
    res = client.get("/api/meta/districts?state=pb")
    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "Punjab"
    assert "Ludhiana" in data["districts"]


def test_meta_districts_unknown_state():
    """Verify /api/meta/districts returns 404 for unknown state."""
    res = client.get("/api/meta/districts?state=Atlantis")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_context_validation_district_without_state():
    """Verify selecting district without state returns 422."""
    payload = {
        "query": "Show extraction summary",
        "district": "Ludhiana",
        "state": None,
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 422
    assert "district cannot be specified without a state" in res.json()["detail"].lower()


def test_context_validation_unknown_state():
    """Verify unknown state in context returns 422."""
    payload = {
        "query": "Show extraction summary",
        "state": "Narnia",
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 422
    assert "unknown" in res.json()["detail"].lower()


def test_context_validation_invalid_year():
    """Verify invalid assessment year returns 422."""
    payload = {
        "query": "Show extraction summary",
        "year": 1990,
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 422
    assert "invalid" in res.json()["detail"].lower()


def test_context_validation_district_not_in_state():
    """Verify district not belonging to chosen state returns 422."""
    payload = {
        "query": "Show extraction summary",
        "state": "Bihar",
        "district": "Ludhiana",
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 422
    assert "not found in state" in res.json()["detail"].lower()


def test_context_validation_sql_injection_attempt():
    """Verify SQL-injection patterns in state or district are safely rejected with 422."""
    payload_state = {
        "query": "Show extraction summary",
        "state": "' OR '1'='1",
    }
    res = client.post("/api/agent/query", json=payload_state)
    assert res.status_code == 422

    payload_dist = {
        "query": "Show extraction summary",
        "state": "Punjab",
        "district": "'; DROP TABLE districts; --",
    }
    res2 = client.post("/api/agent/query", json=payload_dist)
    assert res2.status_code == 422


def test_context_default_used_by_template_path():
    """Verify context defaults (e.g. Rajasthan, 2024) are used by template path when query has no location."""
    payload = {
        "query": "Show extraction summary",
        "state": "Rajasthan",
        "year": 2024,
        "mode": "template",
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["mode_used"] == "template"
    # Verification and evidence should reflect Rajasthan
    assert any(
        e["arguments"].get("state") == "Rajasthan"
        for e in data["evidence"]
    )


def test_explicit_question_overrides_context():
    """Verify explicit location in question overrides selected context."""
    # Context says Bihar, but query explicitly asks about Rajasthan
    payload = {
        "query": "Show groundwater summary for Rajasthan in 2024.",
        "state": "Bihar",
        "year": 2022,
        "mode": "template",
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Evidence must be for Rajasthan, not Bihar
    assert any(
        e["arguments"].get("state") == "Rajasthan"
        for e in data["evidence"]
    )


def test_meta_states_filtered_by_year():
    """Verify /api/meta/states filters available states according to the assessment year."""
    # Year 2025 has benchmark subset of 13 states
    res_2025 = client.get("/api/meta/states?year=2025")
    assert res_2025.status_code == 200
    states_2025 = res_2025.json()["states"]
    assert len(states_2025) == 13
    assert "Bihar" in states_2025
    assert "Punjab" in states_2025
    assert "Rajasthan" in states_2025
    assert "Kerala" not in states_2025
    assert "Assam" not in states_2025

    # Year 2022 has comprehensive 31 states/UTs
    res_2022 = client.get("/api/meta/states?year=2022")
    assert res_2022.status_code == 200
    states_2022 = res_2022.json()["states"]
    assert len(states_2022) == 31
    assert "Kerala" in states_2022
    assert "Assam" in states_2022


def test_meta_districts_filtered_by_year():
    """Verify /api/meta/districts filters available districts according to state and year."""
    # Bihar in 2025 has exactly 10 districts
    res_bihar_2025 = client.get("/api/meta/districts?state=Bihar&year=2025")
    assert res_bihar_2025.status_code == 200
    dists_2025 = res_bihar_2025.json()["districts"]
    assert len(dists_2025) == 10
    assert "Patna" in dists_2025
    assert "Gaya" in dists_2025
    assert "Katihar" not in dists_2025

    # Bihar in 2022 has comprehensive 41 districts (including Katihar, Purnia, etc.)
    res_bihar_2022 = client.get("/api/meta/districts?state=Bihar&year=2022")
    assert res_bihar_2022.status_code == 200
    dists_2022 = res_bihar_2022.json()["districts"]
    assert len(dists_2022) >= 38
    assert "Patna" in dists_2022
    assert "Katihar" in dists_2022


def test_context_validation_state_not_in_year():
    """Verify context validation rejects state that has no records for the given year."""
    # Kerala is only in 2022, not in 2025
    payload = {
        "query": "Show extraction summary",
        "state": "Kerala",
        "year": 2025,
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 422
    assert "has no groundwater assessment records for year 2025" in res.json()["detail"].lower()


def test_context_validation_district_not_in_year():
    """Verify context validation rejects district not present in chosen assessment year."""
    # Katihar exists in Bihar in 2022, but NOT in 2025
    payload = {
        "query": "Show extraction summary",
        "state": "Bihar",
        "district": "Katihar",
        "year": 2025,
    }
    res = client.post("/api/agent/query", json=payload)
    assert res.status_code == 422
    assert "has no groundwater assessment records in 'bihar' for year 2025" in res.json()["detail"].lower()

