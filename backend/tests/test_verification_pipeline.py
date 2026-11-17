"""
Verification Pipeline & Authenticity Test Suite
Testing the 10 critical criteria defined in Section 9:
1. Patna 2022 extraction (Verified)
2. Patna 2025 extraction (Verified)
3. Patna 2026 extraction (Rejected/Synthetic -> Not Found)
4. Patna 2025 recharge (Missing in source -> Not Found)
5. Ludhiana 2024 extraction (Synthetic -> Not Found)
6. Jalandhar 2025 extraction (Synthetic -> Not Found)
7. Unsupported locations (Not Found)
8. Missing assessment years (Not Found)
9. Unverified records policy enforcement (Never presented as official data)
10. Historical comparisons (Verified vs Verified, and Verified vs Unverified)
"""
import pytest
from app.database.connection import get_sync_db
from app.agent.planner import QueryPlanner
from app.nlp.query_parser import parse_question
from app.database import repository as repo
from app.database.models import GroundwaterResource, SourceDataset, State, District, AssessmentYear


UNAVAILABLE_MSG = "Verified data for this location, parameter and assessment year is not currently available in the database."


class TestVerificationPipeline:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.db = get_sync_db()
        self.planner = QueryPlanner(self.db)
        yield
        self.db.close()

    # 1. Patna 2022 extraction
    def test_patna_2022_extraction(self):
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

        # Check provenance
        prov = res["provenance"][0]
        assert prov["assessment_year"] == "2022"
        assert prov["assessment_unit_level"] == "District"
        assert prov["verification_status"] == "VERIFIED"
        assert prov["record_verified"] is True
        assert "CGWB National Compilation" in prov["source_document"]

        # Check natural language answer & provenance display (Section 8)
        pq = parse_question("What was the groundwater extraction in Patna in 2022?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "success"
        assert "174,600.00 Ham" in plan_res["answer"]
        assert "Actual Assessment Year: 2022" in plan_res["answer"]
        assert "Patna, Bihar (District)" in plan_res["answer"]
        assert "Source Agency:" in plan_res["answer"]
        assert "Verification Status: VERIFIED" in plan_res["answer"]

    # 2. Patna 2025 extraction
    def test_patna_2025_extraction(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2025"
        )
        assert res["status"] == "success"
        data = res["data"]
        # Authoritative verified values from Ministry of Jal Shakti 2025 compilation
        assert data["total_annual_extraction_ham"] == 59747.83
        assert data["extraction_irrigation_ham"] == 41223.39
        assert data["extraction_domestic_ham"] == 17061.84
        assert data["extraction_industrial_ham"] == 1462.64
        assert data["unit"] == "Ham"

        # Check provenance
        prov = res["provenance"][0]
        assert prov["assessment_year"] == "2025"
        assert prov["publication_year"] == "2025"
        assert prov["verification_status"] == "VERIFIED"
        assert prov["record_verified"] is True
        assert "711d8d476bbf498cd90f8038e7371227.pdf" in prov["source_document_url"]
        assert "District 26" in prov["source_page_table"]

        # Check natural language answer & provenance display
        pq = parse_question("What is total annual groundwater extraction in Patna district in 2025?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "success"
        assert "59,747.83 Ham" in plan_res["answer"]
        assert "Actual Assessment Year: 2025" in plan_res["answer"]
        assert "Verification Status: VERIFIED" in plan_res["answer"]

    # 3. Patna 2026 extraction (Synthetic future year -> Not Found)
    def test_patna_2026_extraction(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2026"
        )
        assert res["status"] == "not_found"

        pq = parse_question("What is the groundwater extraction in Patna in 2026?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res["answer"]
        # Never silently substitute 2025 or 2022
        assert "59,747.83" not in plan_res["answer"]
        assert "174,600" not in plan_res["answer"]

    # 4. Patna 2025 recharge (Recharge is missing in 2025 source -> Not Found)
    def test_patna_2025_recharge(self):
        res = repo.get_groundwater_recharge(
            self.db, state="Bihar", district="Patna", assessment_year="2025"
        )
        assert res["status"] == "not_found"

        pq = parse_question("What is the groundwater recharge in Patna in 2025?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res["answer"]

    # 5. Ludhiana 2024 extraction (Synthetic -> Not Found)
    def test_ludhiana_2024_extraction(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Punjab", district="Ludhiana", assessment_year="2024"
        )
        assert res["status"] == "not_found"

        pq = parse_question("What is extraction in Ludhiana Punjab in 2024?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res["answer"]

    # 6. Jalandhar 2025 extraction (Synthetic -> Not Found)
    def test_jalandhar_2025_extraction(self):
        res = repo.get_groundwater_extraction(
            self.db, state="Punjab", district="Jalandhar", assessment_year="2025"
        )
        assert res["status"] == "not_found"

        pq = parse_question("What is extraction in Jalandhar Punjab in 2025?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res["answer"]

    # 7. Unsupported locations
    def test_unsupported_locations(self):
        # Fake state
        res_fake_state = repo.get_groundwater_extraction(
            self.db, state="Atlantis", district="Patna"
        )
        assert res_fake_state["status"] == "not_found"

        # Fake district in Bihar
        res_fake_district = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Narnia"
        )
        assert res_fake_district["status"] == "not_found"

        pq = parse_question("What is extraction in Atlantis in 2022?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res["answer"]

    # 8. Missing assessment years
    def test_missing_assessment_years(self):
        res_missing_yr = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Patna", assessment_year="2019"
        )
        assert res_missing_yr["status"] == "not_found"

        pq = parse_question("What is extraction in Patna in 2019?")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res["answer"]

    # 9. Unverified records policy
    def test_unverified_records_policy(self):
        # Ensure rejected Ludhiana in Bihar 2020 cannot be retrieved as official data
        res_rejected = repo.get_groundwater_extraction(
            self.db, state="Bihar", district="Ludhiana", assessment_year="2020"
        )
        assert res_rejected["status"] == "not_found"

        # Verify that all returned records from repository have is_verified == True
        verified_years = repo.get_assessment_years(self.db)["data"]
        assert verified_years == ["2022", "2025"]

        # Ensure no synthetic years (2020, 2023, 2024, 2026) are returned in assessment_years
        for synthetic_year in ["2020", "2023", "2024", "2026"]:
            assert synthetic_year not in verified_years

        # Ensure unverified records count in database matches expectation
        unverified_in_db = self.db.query(GroundwaterResource).filter(
            GroundwaterResource.is_verified.is_(False)
        ).count()
        assert unverified_in_db > 200

    # 10. Historical comparisons
    def test_historical_comparisons(self):
        # Case A: Verified vs Verified (Patna 2022 vs 2025)
        res_valid = repo.compare_assessment_years(
            self.db, state="Bihar", district="Patna", parameter="extraction",
            year1="2022", year2="2025"
        )
        assert res_valid["status"] == "success"
        data = res_valid["data"]
        assert data["year_1"]["year"] == "2022"
        assert data["year_1"]["value"] == 174600.0
        assert data["year_2"]["year"] == "2025"
        assert data["year_2"]["value"] == 59747.83
        assert data["difference"] == -114852.17
        assert data["percent_change"] == -65.78
        assert data["trend"] == "decreased"
        assert len(res_valid["provenance"]) == 2

        # Check via planner
        pq = parse_question("Compare extraction in Patna between 2022 and 2025")
        plan_res = self.planner.plan_and_execute(pq)
        assert plan_res["status"] == "success"
        assert "174,600.00 Ham" in plan_res["answer"]
        assert "59,747.83 Ham" in plan_res["answer"]
        assert "decrease of 114,852.17 Ham" in plan_res["answer"]
        assert "Source Provenance:" in plan_res["answer"]

        # Case B: Verified vs Unverified (Patna 2022 vs 2026)
        res_unverified = repo.compare_assessment_years(
            self.db, state="Bihar", district="Patna", parameter="extraction",
            year1="2022", year2="2026"
        )
        assert res_unverified["status"] == "not_found"

        pq_unverified = parse_question("Compare extraction in Patna between 2022 and 2026")
        plan_res_unverified = self.planner.plan_and_execute(pq_unverified)
        assert plan_res_unverified["status"] == "not_found"
        assert UNAVAILABLE_MSG in plan_res_unverified["answer"]
