"""Comprehensive Integration Test Suite for Groundwater AI with INGRES-Agent pipeline.

Tests all 15 critical scenarios required by Phase 8:
1. Patna 2022 extraction (Verified benchmark).
2. Patna 2025 extraction (Verified authentic).
3. Patna 2026 extraction (Rejected/Synthetic future year -> Not Found contract).
4. Patna 2025 recharge (Missing in source -> Not Found contract).
5. Ludhiana 2024 extraction (Unverified OpenCity -> Not Found contract).
6. Jalandhar 2025 extraction (Unverified in 2025 -> Not Found contract).
7. Unsupported locations (Non-existent location -> Not Found).
8. Missing assessment years (2021 uncompiled year -> Not Found contract).
9. Strict verification policy enforcement (Unverified records never served to factual queries).
10. Historical comparison (Patna 2022 vs 2025 verified; Ludhiana 2022 vs 2024 blocked).
11. Telangana 2025 extraction (All 33 districts verified, including Hyderabad).
12. Tamil Nadu 2025 extraction (All 38 districts verified, including Chennai).
13. Stage of extraction percentage (Hyderabad 2025 stage: 98.32%, Patna 2022 stage: 61.65%).
14. Sub-district assessment unit categorisation (2023 Major City taluks).
15. Macro state volumetric resources (2025 Telangana & Tamil Nadu Bcm records).
"""
import pytest
from app.database.connection import get_sync_db
from app.agent.planner import QueryPlanner
from app.nlp.query_parser import parse_question
from app.database import repository as repo
from app.database.models import (
    GroundwaterResource, SourceDataset, State, District, AssessmentYear,
    AssessmentUnitCategory, StateGroundwaterResource
)

CONTRACT_MSG = "Verified data for this location, parameter and assessment year is not currently available in the database."


class TestIntegratedSystem:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = get_sync_db()
        self.planner = QueryPlanner(self.db)
        yield
        self.db.close()

    # 1. Patna 2022 extraction
    def test_01_patna_2022_extraction(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2022"
        )
        assert res["status"] == "success"
        data = res["data"]
        assert data["total_annual_extraction_ham"] == 174600.0
        assert data["extraction_irrigation_ham"] == 142300.0
        assert data["extraction_domestic_ham"] == 24100.0
        assert data["extraction_industrial_ham"] == 8200.0
        assert data["unit"] == "Ham"
        assert data["verification_status"] == "VERIFIED"

    # 2. Patna 2025 extraction
    def test_02_patna_2025_extraction(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2025"
        )
        assert res["status"] == "success"
        data = res["data"]
        assert data["total_annual_extraction_ham"] == 59747.83
        assert data["extraction_irrigation_ham"] == 41223.39
        assert data["extraction_domestic_ham"] == 17061.84
        assert data["extraction_industrial_ham"] == 1462.64
        assert data["unit"] == "Ham"
        assert data["verification_status"] == "VERIFIED"
        prov = res["provenance"][0]
        assert "711d8d476bbf498cd90f8038e7371227.pdf" in prov["source_document_url"]

    # 3. Patna 2026 extraction (Synthetic future year)
    def test_03_patna_2026_extraction_blocked(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2026"
        )
        assert res["status"] == "not_found"
        assert CONTRACT_MSG in res["message"]

    # 4. Patna 2025 recharge (Missing in source)
    def test_04_patna_2025_recharge_missing(self):
        res = repo.get_groundwater_recharge(
            self.db, state="Bihar", district="Patna", assessment_year="2025"
        )
        assert res["status"] == "not_found"
        assert CONTRACT_MSG in res["message"]

    # 5. Ludhiana 2024 extraction (Unverified year)
    def test_05_ludhiana_2024_unverified_blocked(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Punjab", district="Ludhiana", assessment_year="2024"
        )
        assert res["status"] == "not_found"
        assert CONTRACT_MSG in res["message"]

    # 6. Jalandhar 2025 extraction (Unverified state in 2025)
    def test_06_jalandhar_2025_unverified_blocked(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Punjab", district="Jalandhar", assessment_year="2025"
        )
        assert res["status"] == "not_found"
        assert CONTRACT_MSG in res["message"]

    # 7. Unsupported location
    def test_07_unsupported_location(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Atlantis", district="PoseidonCity", assessment_year="2022"
        )
        assert res["status"] == "not_found"

    # 8. Missing assessment year (2021)
    def test_08_missing_assessment_year_2021(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2021"
        )
        assert res["status"] == "not_found"
        assert CONTRACT_MSG in res["message"]

    # 9. Verification policy: unverified records in DB are never returned
    def test_09_unverified_records_never_returned(self):
        # 2020 Delhi records exist in DB as UNVERIFIED
        res = repo.get_groundwater_extraction(
            self.db, state="Delhi", district="Central", assessment_year="2020"
        )
        assert res["status"] == "not_found"
        assert CONTRACT_MSG in res["message"]

    # 10. Historical comparisons
    def test_10_historical_comparisons(self):
        # Case A: Patna 2022 vs 2025 (both verified)
        res_valid = repo.compare_assessment_years(
            self.db, state="Bihar", district="Patna", parameter="extraction",
            year1="2022", year2="2025"
        )
        assert res_valid["status"] == "success"
        data = res_valid["data"]
        assert data["year_1"]["value"] == 174600.0
        assert data["year_2"]["value"] == 59747.83
        assert data["difference"] == -114852.17
        assert data["verification_status"] == "VERIFIED"

        # Case B: Ludhiana 2022 vs 2024 (2024 unverified -> blocked)
        res_blocked = repo.compare_assessment_years(
            self.db, state="Punjab", district="Ludhiana", parameter="extraction",
            year1="2022", year2="2024"
        )
        assert res_blocked["status"] == "not_found"
        assert CONTRACT_MSG in res_blocked["message"]

    # 11. Telangana 2025 extraction (all 33 districts verified)
    def test_11_telangana_2025_coverage_and_hyderabad(self):
        # Check Hyderabad record
        res = repo.get_groundwater_extraction(
            self.db, state="Telangana", district="Hyderabad", assessment_year="2025"
        )
        assert res["status"] == "success"
        data = res["data"]
        assert data["total_annual_extraction_ham"] == 6061.83
        assert data["extraction_irrigation_ham"] == 0.0
        assert data["extraction_industrial_ham"] == 415.80
        assert data["extraction_domestic_ham"] == 5646.03
        assert data["verification_status"] == "VERIFIED"

        # Check total verified districts in Telangana 2025
        yr = self.db.query(AssessmentYear).filter(AssessmentYear.year == "2025").first()
        st = self.db.query(State).filter(State.name == "Telangana").first()
        verified_count = self.db.query(GroundwaterResource).filter(
            GroundwaterResource.state_id == st.id,
            GroundwaterResource.assessment_year_id == yr.id,
            GroundwaterResource.is_verified.is_(True),
        ).count()
        assert verified_count == 33

    # 12. Tamil Nadu 2025 extraction (all 38 districts verified)
    def test_12_tamil_nadu_2025_coverage_and_chennai(self):
        # Check Chennai record
        res = repo.get_groundwater_extraction(
            self.db, state="Tamil Nadu", district="Chennai", assessment_year="2025"
        )
        assert res["status"] == "success"
        data = res["data"]
        assert data["total_annual_extraction_ham"] == 10854.47
        assert data["verification_status"] == "VERIFIED"

        # Check total verified districts in Tamil Nadu 2025
        yr = self.db.query(AssessmentYear).filter(AssessmentYear.year == "2025").first()
        st = self.db.query(State).filter(State.name == "Tamil Nadu").first()
        verified_count = self.db.query(GroundwaterResource).filter(
            GroundwaterResource.state_id == st.id,
            GroundwaterResource.assessment_year_id == yr.id,
            GroundwaterResource.is_verified.is_(True),
        ).count()
        assert verified_count == 38

    # 13. Stage of extraction percentage
    def test_13_stage_of_extraction(self):
        res_hyd = repo.get_stage_of_extraction(
            self.db, state="Telangana", district="Hyderabad", assessment_year="2025"
        )
        assert res_hyd["status"] == "success"
        assert res_hyd["data"]["stage_of_extraction_pct"] == 98.32

        res_patna = repo.get_stage_of_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2022"
        )
        assert res_patna["status"] == "success"
        assert res_patna["data"]["stage_of_extraction_pct"] == 61.65

    # 14. Sub-district unit categorisation (2023 Major Cities taluks)
    def test_14_sub_district_unit_categories_2023(self):
        res = repo.get_assessment_unit_categories(self.db, year=2023)
        assert res["status"] == "success"
        assert res["data"]["total_units_returned"] > 0
        units = res["data"]["assessment_units"]
        assert any("Bangalore" in str(u.get("district") or "") or "Bengaluru" in str(u.get("district") or "") for u in units)

    # 15. Macro state volumetric resources (StateGroundwaterResource in Bcm for 2025)
    def test_15_state_volumetric_resources_bcm(self):
        res = repo.get_state_volumetric_resources(self.db, state="Telangana", year=2025)
        assert res["status"] == "success"
        tg = res["data"]["state_resources"][0]
        assert tg["annual_recharge_bcm"] == 21.93
        assert tg["extractable_resources_bcm"] == 19.84
        assert tg["total_extraction_bcm"] == 9.26
        assert tg["unit"] == "Bcm"
        assert tg["verification_status"] == "VERIFIED"

