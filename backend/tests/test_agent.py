"""
Comprehensive test suite for Groundwater AI Agent.
Tests NLP, intent classification, entity extraction, database functions, and API endpoints.
"""
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.nlp.intent_classifier import classify_intent
from app.nlp.entity_extractor import extract_entities
from app.nlp.query_parser import parse_question
from app.schemas.schemas import QueryRequest, StructuredQueryRequest
from app.database.connection import init_db, get_sync_db
from app.main import (
    health_check, get_metadata, list_states, list_districts,
    list_assessment_years, natural_language_query, structured_query,
    get_functions, query_history, evaluation_summary,
    data_sources, state_comparison, category_distribution, district_data
)


# ─────────────── Intent Classification Tests ──────────────────────────────────

class TestIntentClassifier:

    def test_assessment_years_intent(self):
        result = classify_intent("What assessment years are available?")
        assert result["intent"] == "get_assessment_years"

    def test_state_list_intent(self):
        result = classify_intent("Which states have groundwater data?")
        assert result["intent"] == "get_state_list"

    def test_overexploited_intent(self):
        result = classify_intent("Which districts in Bihar are over-exploited?")
        assert result["intent"] == "get_overexploited_units"

    def test_assessment_category_intent(self):
        result = classify_intent("What assessment category is Patna in?")
        assert result["intent"] == "get_assessment_category"

    def test_stage_of_extraction_intent(self):
        result = classify_intent("What is the stage of groundwater extraction in Patna?")
        assert result["intent"] == "get_stage_of_extraction"

    def test_comparison_intent(self):
        result = classify_intent("Compare extraction in Patna and Gaya")
        assert result["intent"] == "compare_locations"

    def test_recharge_intent(self):
        result = classify_intent("Show groundwater recharge in Bihar")
        assert result["intent"] == "get_groundwater_recharge"

    def test_extraction_intent(self):
        result = classify_intent("What is the groundwater extraction in Patna?")
        assert result["intent"] == "get_groundwater_extraction"

    def test_extractable_intent(self):
        result = classify_intent("What is the extractable groundwater in Patna?")
        assert result["intent"] == "get_extractable_groundwater"

    def test_groundwater_level_intent(self):
        result = classify_intent("What is the groundwater level in Patna?")
        assert result["intent"] == "get_groundwater_level"

    def test_ambiguous_intent_requires_clarification(self):
        result = classify_intent("Show groundwater in Bihar")
        assert result["requires_clarification"] == True

    def test_country_summary_intent(self):
        result = classify_intent("Show national groundwater statistics for 2022")
        assert result["intent"] == "get_country_summary"

    def test_state_summary_intent(self):
        result = classify_intent("Give me a summary of groundwater in Bihar")
        assert result["intent"] == "get_state_summary"


# ─────────────── Entity Extraction Tests ──────────────────────────────────────

class TestEntityExtractor:

    def test_state_extraction_bihar(self):
        result = extract_entities("Show groundwater in Bihar")
        assert result["state"] == "Bihar"

    def test_state_extraction_rajasthan(self):
        result = extract_entities("Show extraction in Jaipur Rajasthan")
        assert result["state"] == "Rajasthan"

    def test_district_extraction_patna(self):
        result = extract_entities("What is extraction in Patna district?")
        assert result["district"] is not None
        assert "Patna" in result["district"]

    def test_district_extraction_gaya(self):
        result = extract_entities("Show recharge in Gaya Bihar")
        assert result["district"] is not None
        assert "Gaya" in result["district"]

    def test_year_extraction_2022(self):
        result = extract_entities("Show extraction in Bihar in 2022")
        assert result["assessment_year"] == "2022"

    def test_year_extraction_2023(self):
        result = extract_entities("Show extraction in Patna in 2023")
        assert result["assessment_year"] == "2023"

    def test_no_year_when_absent(self):
        result = extract_entities("Show extraction in Patna")
        assert result["assessment_year"] is None

    def test_state_inference_from_district(self):
        result = extract_entities("What is extraction in Patna?")
        assert result["state"] == "Bihar"

    def test_aggregation_district_level(self):
        result = extract_entities("Show extraction in Patna Bihar")
        assert result["aggregation"] == "district"

    def test_aggregation_state_level(self):
        result = extract_entities("Show extraction in Bihar")
        assert result["aggregation"] == "state"

    def test_parameter_recharge(self):
        result = extract_entities("Show groundwater recharge in Bihar")
        assert result["parameter"] == "recharge"

    def test_parameter_extraction(self):
        result = extract_entities("Show groundwater extraction in Bihar")
        assert result["parameter"] == "extraction"

    def test_comparison_locations(self):
        result = extract_entities("Compare extraction in Patna and Gaya")
        locs = result["comparison_locations"]
        district_names = [loc["district"] for loc in locs]
        assert any("Patna" in d for d in district_names)
        assert any("Gaya" in d for d in district_names)


# ─────────────── Query Parser Tests ───────────────────────────────────────────

class TestQueryParser:

    def test_full_parse_recharge_query(self):
        result = parse_question("Show groundwater recharge in Gaya district of Bihar")
        assert result["intent"] == "get_groundwater_recharge"
        assert result["state"] == "Bihar"
        assert "Gaya" in (result["district"] or "")

    def test_full_parse_extraction_query(self):
        result = parse_question("What is the groundwater extraction in Patna?")
        assert result["intent"] == "get_groundwater_extraction"
        assert result["state"] == "Bihar"

    def test_full_parse_overexploited_query(self):
        result = parse_question("Which districts in Bihar are over-exploited?")
        assert result["intent"] == "get_overexploited_units"
        assert result["state"] == "Bihar"

    def test_ambiguous_query_flagged(self):
        result = parse_question("Show groundwater in Bihar")
        assert result["requires_clarification"] == True
        assert result["clarification_question"] is not None

    def test_unsupported_level_query(self):
        result = parse_question("What is the groundwater level in Patna?")
        assert result["intent"] == "get_groundwater_level"


# ─────────────── Database Function Tests ──────────────────────────────────────

class TestDatabaseFunctions:
    """Tests that require an initialized database with imported data."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        init_db()
        self.db = get_sync_db()
        yield
        self.db.close()

    def _has_data(self):
        from app.database.models import GroundwaterResource
        count = self.db.query(GroundwaterResource).count()
        return count > 0

    def test_get_assessment_years_returns_list(self):
        from app.database.repository import get_assessment_years
        result = get_assessment_years(self.db)
        assert result["status"] in ("success", "not_found")

    def test_get_state_list(self):
        from app.database.repository import get_state_list
        result = get_state_list(self.db)
        assert result["status"] in ("success", "not_found")

    def test_get_assessment_years_excludes_unverified_years(self):
        from app.database.repository import get_assessment_years
        result = get_assessment_years(self.db)
        if result["status"] == "success" and result["data"]:
            assert "2022" in result["data"] and "2025" in result["data"]
            assert "2021" not in result["data"]

    def test_get_state_list_has_bihar(self):
        from app.database.repository import get_state_list
        result = get_state_list(self.db)
        if result["status"] == "success" and result["data"]:
            assert "Bihar" in result["data"]

    def test_get_district_summary_patna(self):
        from app.database.repository import get_district_summary
        if not self._has_data():
            pytest.skip("No data imported")
        result = get_district_summary(self.db, state="Bihar", district="Patna")
        assert result["status"] in ("success", "not_found")

    def test_get_groundwater_recharge_bihar(self):
        from app.database.repository import get_groundwater_recharge
        if not self._has_data():
            pytest.skip("No data imported")
        result = get_groundwater_recharge(self.db, state="Bihar")
        assert result["status"] in ("success", "not_found")
        if result["status"] == "success":
            assert result["data"]["total_annual_recharge_ham"] is not None

    def test_get_groundwater_extraction_patna(self):
        from app.database.repository import get_groundwater_extraction
        if not self._has_data():
            pytest.skip("No data imported")
        result = get_groundwater_extraction(self.db, state="Bihar", district="Patna")
        assert result["status"] in ("success", "not_found")

    def test_get_overexploited_units_bihar_without_verified_category_data(self):
        from app.database.repository import get_overexploited_units
        if not self._has_data():
            pytest.skip("No data imported")
        result = get_overexploited_units(self.db, state="Bihar", assessment_year="2021")
        assert result["status"] == "not_found"

    def test_invalid_state_returns_not_found(self):
        from app.database.repository import get_district_summary
        result = get_district_summary(self.db, state="FakeState", district="FakeCity")
        assert result["status"] == "not_found"

    def test_invalid_year_returns_not_found(self):
        from app.database.repository import get_groundwater_extraction
        if not self._has_data():
            pytest.skip("No data imported")
        result = get_groundwater_extraction(self.db, state="Bihar", district="Patna", assessment_year="2050")
        assert result["status"] == "not_found"

    def test_groundwater_level_unsupported(self):
        from app.database.repository import get_groundwater_level
        result = get_groundwater_level(self.db)
        assert result["status"] == "unsupported"

    def test_compare_locations_patna_gaya(self):
        from app.database.repository import compare_locations
        if not self._has_data():
            pytest.skip("No data imported")
        result = compare_locations(
            self.db,
            state1="Bihar", district1="Patna",
            state2="Bihar", district2="Gaya",
            parameter="extraction"
        )
        assert result["status"] == "success"
        assert "comparison" in result["data"]

    def test_no_sql_injection_in_state(self):
        from app.database.repository import get_district_summary
        result = get_district_summary(
            self.db,
            state="'; DROP TABLE states; --",
            district="test"
        )
        assert result["status"] == "not_found"


# ─────────────── API Direct Integration Tests ────────────────────────────────

class TestAPIEndpoints:

    @pytest.fixture(autouse=True)
    def setup_db(self):
        init_db()
        self.db = get_sync_db()
        yield
        self.db.close()

    def test_health_endpoint(self):
        res = health_check(self.db)
        assert res.status == "healthy"
        assert res.database_connected is True
        assert res.total_records > 0

    def test_metadata_endpoint(self):
        res = get_metadata(self.db)
        assert res.app_name == "Groundwater AI Agent"
        assert res.total_records > 0

    def test_states_endpoint(self):
        res = list_states(self.db)
        assert "states" in res
        assert "Bihar" in res["states"]

    def test_assessment_years_endpoint(self):
        res = list_assessment_years(self.db)
        assert "assessment_years" in res
        assert "2022" in res["assessment_years"]
        assert "2025" in res["assessment_years"]
        assert len(res["assessment_years"]) >= 2

    def test_functions_endpoint(self):
        res = get_functions()
        assert "functions" in res
        assert len(res["functions"]) > 0

    def test_query_endpoint_basic(self):
        req = QueryRequest(question="What assessment years are available?")
        res = natural_language_query(req, self.db)
        assert res.intent == "get_assessment_years"
        assert res.answer is not None

    def test_query_endpoint_extraction(self):
        req = QueryRequest(question="What is the groundwater extraction in Patna Bihar?")
        res = natural_language_query(req, self.db)
        assert res.intent == "get_groundwater_extraction"
        assert res.result is not None

    def test_query_endpoint_overexploited(self):
        req = QueryRequest(question="Which districts in Bihar are over-exploited?")
        res = natural_language_query(req, self.db)
        assert res.intent == "get_overexploited_units"
        assert res.result is not None

    def test_query_endpoint_unsupported(self):
        req = QueryRequest(question="What is the groundwater level in Patna?")
        res = natural_language_query(req, self.db)
        assert res.status in ("unsupported", "success")

    def test_query_history_endpoint(self):
        res = query_history(limit=10, db=self.db)
        assert "history" in res

    def test_sources_endpoint(self):
        res = data_sources(self.db)
        assert "sources" in res
        assert len(res["sources"]) > 0

    def test_evaluation_summary_endpoint(self):
        res = evaluation_summary(self.db)
        assert res is not None

    def test_analytics_state_comparison(self):
        res = state_comparison(year="2025", db=self.db)
        assert "states" in res
        assert len(res["states"]) > 0

    def test_analytics_category_distribution(self):
        res = category_distribution(year="2025", db=self.db)
        assert "distribution" in res

    def test_districts_endpoint_bihar(self):
        res = list_districts("Bihar", self.db)
        assert res["state"] == "Bihar"
        assert "Patna" in res["districts"]

    def test_analytics_district_data(self):
        res = district_data("Bihar", year="2025", db=self.db)
        assert res["state"] == "Bihar"
        assert len(res["districts"]) > 0
