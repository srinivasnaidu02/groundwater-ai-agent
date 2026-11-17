"""
Automated evaluation script for the Groundwater AI Agent.
Runs 100+ benchmark test cases and calculates actual performance metrics.

Usage:
    python scripts/evaluate_agent.py
"""
import sys
import json
import csv
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database.connection import init_db, get_sync_db
from app.database.models import EvaluationResult
from app.nlp.query_parser import parse_question
from app.agent.planner import QueryPlanner


# ──────────────────────── Test Cases ─────────────────────────────────────────

TEST_CASES = [
    # Assessment year queries
    {"id": "TC001", "question": "What assessment years are available?", "expected_intent": "get_assessment_years", "expected_function": "get_assessment_years", "expected_status": "success", "category": "metadata"},
    {"id": "TC002", "question": "Which years have groundwater data?", "expected_intent": "get_assessment_years", "expected_function": "get_assessment_years", "expected_status": "success", "category": "metadata"},
    {"id": "TC003", "question": "Show me the available assessment periods", "expected_intent": "get_assessment_years", "expected_function": "get_assessment_years", "expected_status": "success", "category": "metadata"},

    # State list queries
    {"id": "TC004", "question": "Which states have groundwater data?", "expected_intent": "get_state_list", "expected_function": "get_state_list", "expected_status": "success", "category": "metadata"},
    {"id": "TC005", "question": "List all states available", "expected_intent": "get_state_list", "expected_function": "get_state_list", "expected_status": "success", "category": "metadata"},

    # State summary queries
    {"id": "TC006", "question": "Show groundwater statistics for Bihar", "expected_intent": "get_state_summary", "expected_function": "get_state_summary", "expected_status": "success", "category": "state"},
    {"id": "TC007", "question": "Give me a summary of groundwater in Rajasthan", "expected_intent": "get_state_summary", "expected_function": "get_state_summary", "expected_status": "success", "category": "state"},
    {"id": "TC008", "question": "Show groundwater overview for Maharashtra", "expected_intent": "get_state_summary", "expected_function": "get_state_summary", "expected_status": "success", "category": "state"},

    # District summary queries
    {"id": "TC009", "question": "Show all groundwater data for Patna Bihar", "expected_intent": "get_district_summary", "expected_function": "get_district_summary", "expected_status": "success", "category": "district"},
    {"id": "TC010", "question": "What is the groundwater situation in Gaya Bihar?", "expected_intent": "get_district_summary", "expected_function": "get_district_summary", "expected_status": "success", "category": "district"},
    {"id": "TC011", "question": "Show data for Jaipur Rajasthan", "expected_intent": "get_district_summary", "expected_function": "get_district_summary", "expected_status": "success", "category": "district"},

    # Recharge queries
    {"id": "TC012", "question": "What is the groundwater recharge in Patna Bihar?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC013", "question": "Show annual groundwater recharge in Gaya district of Bihar", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC014", "question": "What is the total recharge in Bihar?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC015", "question": "Show recharge data for Lucknow Uttar Pradesh", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC016", "question": "Annual groundwater recharge in Gujarat", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC017", "question": "What is the recharge in Muzaffarpur Bihar?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC018", "question": "Show groundwater recharge in Maharashtra", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC019", "question": "Groundwater recharge in Rajasthan 2022", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC020", "question": "What is the annual recharge in Delhi?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},

    # Extraction queries
    {"id": "TC021", "question": "What is the groundwater extraction in Patna?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC022", "question": "How much groundwater is extracted in Gaya district?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC023", "question": "Show annual groundwater utilization in Bihar", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC024", "question": "Total groundwater extraction in Punjab", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC025", "question": "How much groundwater is used in Ludhiana?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC026", "question": "What is the annual groundwater extraction in Jaipur Rajasthan?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC027", "question": "Show groundwater extraction for Ahmedabad Gujarat", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC028", "question": "Annual extraction in Uttar Pradesh", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC029", "question": "Groundwater used in Tamil Nadu", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},

    # Extractable groundwater
    {"id": "TC030", "question": "What is the extractable groundwater in Patna Bihar?", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},
    {"id": "TC031", "question": "Show annual extractable groundwater resources in Gaya", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},
    {"id": "TC032", "question": "Net groundwater availability for future in Bihar", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},
    {"id": "TC033", "question": "Extractable groundwater resources in Gujarat", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},

    # Stage of extraction queries
    {"id": "TC034", "question": "What is the stage of groundwater extraction in Patna?", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC035", "question": "Show stage of extraction for Gaya Bihar", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC036", "question": "What is the stage of groundwater extraction in Amritsar Punjab?", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC037", "question": "Stage of extraction in Jaipur", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC038", "question": "What percent of groundwater is extracted in Ludhiana?", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC039", "question": "Show stage of extraction for Bihar", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC040", "question": "Stage of extraction in Delhi", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},

    # Assessment category queries
    {"id": "TC041", "question": "What assessment category is Patna Bihar in?", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC042", "question": "What is the classification of Gaya district?", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC043", "question": "Show assessment categories in Bihar", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC044", "question": "What category is Ludhiana Punjab classified as?", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC045", "question": "Is Jaipur safe or critical?", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC046", "question": "Show groundwater classification for all districts in Rajasthan", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},

    # Over-exploited queries
    {"id": "TC047", "question": "Which districts in Bihar are over-exploited?", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC048", "question": "Show over-exploited areas in Rajasthan", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC049", "question": "Which districts are over exploited in Punjab?", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC050", "question": "List over-exploited groundwater assessment units in Haryana", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC051", "question": "Which areas are critically over exploited in Uttar Pradesh?", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC052", "question": "Show all over-exploited districts in Maharashtra", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},

    # Comparison queries
    {"id": "TC053", "question": "Compare groundwater extraction in Patna and Gaya", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC054", "question": "Compare extraction between Lucknow and Kanpur", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC055", "question": "Compare recharge in Jaipur and Jodhpur", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC056", "question": "Patna vs Gaya groundwater extraction", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC057", "question": "Compare stage of extraction between Amritsar and Ludhiana", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},

    # Country level
    {"id": "TC058", "question": "Show national groundwater statistics for 2022", "expected_intent": "get_country_summary", "expected_function": "get_country_summary", "expected_status": "success", "category": "national"},
    {"id": "TC059", "question": "What is the total groundwater extraction across India in 2022?", "expected_intent": "get_country_summary", "expected_function": "get_country_summary", "expected_status": "success", "category": "national"},

    # With specific year 2022
    {"id": "TC060", "question": "What is the groundwater extraction in Patna in 2022?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC061", "question": "Show recharge in Bihar 2022", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},

    # Invalid year queries
    {"id": "TC062", "question": "What is the groundwater extraction in Patna in 2023?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "not_found", "category": "invalid_year"},
    {"id": "TC063", "question": "Show recharge in Bihar in 2015", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "not_found", "category": "invalid_year"},
    {"id": "TC064", "question": "Groundwater data for 2010", "expected_intent": "get_country_summary", "expected_function": "get_country_summary", "expected_status": "not_found", "category": "invalid_year"},

    # Invalid location queries
    {"id": "TC065", "question": "Show groundwater extraction in XYZCity", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "not_found", "category": "invalid_location"},
    {"id": "TC066", "question": "What is the recharge in Atlantis province?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "not_found", "category": "invalid_location"},

    # Groundwater level (unsupported)
    {"id": "TC067", "question": "What is the groundwater level in Patna?", "expected_intent": "get_groundwater_level", "expected_function": "get_groundwater_level", "expected_status": "unsupported", "category": "unsupported"},
    {"id": "TC068", "question": "Show water table depth in Gaya", "expected_intent": "get_groundwater_level", "expected_function": "get_groundwater_level", "expected_status": "unsupported", "category": "unsupported"},
    {"id": "TC069", "question": "What is the depth to water table in Bihar?", "expected_intent": "get_groundwater_level", "expected_function": "get_groundwater_level", "expected_status": "unsupported", "category": "unsupported"},

    # Additional varied queries
    {"id": "TC070", "question": "Show extractable groundwater in Patna in 2022", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},
    {"id": "TC071", "question": "What is the stage of extraction in Bihar?", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC072", "question": "Annual extraction in Muzaffarpur Bihar", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC073", "question": "Show groundwater recharge in Darbhanga", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC074", "question": "What category is Aurangabad Bihar?", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC075", "question": "Is Nawada district over-exploited?", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC076", "question": "Show stage of extraction for Nashik Maharashtra", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC077", "question": "What is the annual recharge in Kolkata West Bengal?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC078", "question": "Show extraction in Hyderabad Telangana", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC079", "question": "What is groundwater recharge in Dehradun Uttarakhand?", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC080", "question": "Show all groundwater data for Shimla", "expected_intent": "get_district_summary", "expected_function": "get_district_summary", "expected_status": "success", "category": "district"},
    {"id": "TC081", "question": "Compare extraction in Bangalore and Mysore", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC082", "question": "What is the stage of extraction in Bikaner Rajasthan?", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC083", "question": "Show over-exploited districts in Gujarat", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC084", "question": "Annual extractable groundwater in Pune Maharashtra", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},
    {"id": "TC085", "question": "What is the assessment category of Bathinda Punjab?", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC086", "question": "Show groundwater summary for Ranchi Jharkhand", "expected_intent": "get_district_summary", "expected_function": "get_district_summary", "expected_status": "success", "category": "district"},
    {"id": "TC087", "question": "Total annual recharge in Tamil Nadu", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC088", "question": "Groundwater extraction in West Bengal 2022", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC089", "question": "Stage of extraction in Gurugram Haryana", "expected_intent": "get_stage_of_extraction", "expected_function": "get_stage_of_extraction", "expected_status": "success", "category": "stage"},
    {"id": "TC090", "question": "Compare recharge in Patna and Muzaffarpur", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC091", "question": "Show state summary for Uttar Pradesh 2022", "expected_intent": "get_state_summary", "expected_function": "get_state_summary", "expected_status": "success", "category": "state"},
    {"id": "TC092", "question": "List districts in Bihar with groundwater data", "expected_intent": "get_districts_in_state", "expected_function": "get_districts_in_state", "expected_status": "success", "category": "metadata"},
    {"id": "TC093", "question": "What is the groundwater extraction in Rohtas Bihar?", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC094", "question": "Show recharge in Katihar Bihar", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC095", "question": "Annual extraction in Latur Maharashtra", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "success", "category": "extraction"},
    {"id": "TC096", "question": "Show groundwater level in Guwahati", "expected_intent": "get_groundwater_level", "expected_function": "get_groundwater_level", "expected_status": "unsupported", "category": "unsupported"},
    {"id": "TC097", "question": "What is the depth to water in Jaipur?", "expected_intent": "get_groundwater_level", "expected_function": "get_groundwater_level", "expected_status": "unsupported", "category": "unsupported"},
    {"id": "TC098", "question": "Show groundwater extraction in 2050", "expected_intent": "get_groundwater_extraction", "expected_function": "get_groundwater_extraction", "expected_status": "not_found", "category": "invalid_year"},
    {"id": "TC099", "question": "Recharge data for FakeState", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "not_found", "category": "invalid_location"},
    {"id": "TC100", "question": "Show all over-exploited units in Karnataka", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
    {"id": "TC101", "question": "Annual groundwater recharge in Siwan Bihar", "expected_intent": "get_groundwater_recharge", "expected_function": "get_groundwater_recharge", "expected_status": "success", "category": "recharge"},
    {"id": "TC102", "question": "What is the extractable groundwater in Kolkata?", "expected_intent": "get_extractable_groundwater", "expected_function": "get_extractable_groundwater", "expected_status": "success", "category": "extractable"},
    {"id": "TC103", "question": "Compare stage of extraction in Bikaner and Jodhpur", "expected_intent": "compare_locations", "expected_function": "compare_locations", "expected_status": "success", "category": "comparison"},
    {"id": "TC104", "question": "Show assessment category for all districts in Punjab", "expected_intent": "get_assessment_category", "expected_function": "get_assessment_category", "expected_status": "success", "category": "category"},
    {"id": "TC105", "question": "Which districts in Uttar Pradesh are over-exploited?", "expected_intent": "get_overexploited_units", "expected_function": "get_overexploited_units", "expected_status": "success", "category": "overexploited"},
]


def calculate_entity_score(parsed, test_case):
    """Calculate what fraction of expected entities were correctly extracted."""
    q = test_case["question"].lower()
    expected_entities = {}

    # Determine expected entities from the question content
    state_in_q = None
    district_in_q = None
    year_in_q = None

    for state in ["Bihar", "Rajasthan", "Maharashtra", "Gujarat", "Uttar Pradesh",
                  "Punjab", "Haryana", "Delhi", "Madhya Pradesh", "Tamil Nadu",
                  "Karnataka", "West Bengal", "Jharkhand", "Telangana", "Andhra Pradesh"]:
        if state.lower() in q:
            state_in_q = state
            break

    for district in ["Patna", "Gaya", "Muzaffarpur", "Jaipur", "Jodhpur", "Bikaner",
                     "Lucknow", "Kanpur", "Mumbai", "Pune", "Ludhiana", "Amritsar",
                     "Gurugram", "Darbhanga", "Siwan", "Rohtas", "Katihar", "Nawada",
                     "Aurangabad", "Nashik", "Kolkata", "Hyderabad", "Bangalore"]:
        if district.lower() in q:
            district_in_q = district
            break

    import re
    yr_match = re.search(r'\b(20\d{2})\b', q)
    if yr_match:
        year_in_q = yr_match.group(1)

    score = 1.0
    total = 0
    correct = 0

    if state_in_q:
        total += 1
        if parsed.get("state") and state_in_q.lower() in (parsed.get("state") or "").lower():
            correct += 1

    if district_in_q:
        total += 1
        if parsed.get("district") and district_in_q.lower() in (parsed.get("district") or "").lower():
            correct += 1

    if year_in_q:
        total += 1
        if parsed.get("assessment_year") == year_in_q:
            correct += 1

    if total == 0:
        return 1.0
    return correct / total


def run_evaluation():
    print("[INFO] Initializing database...")
    init_db()
    db = get_sync_db()

    results = []
    t_total = time.time()

    print(f"[INFO] Running {len(TEST_CASES)} test cases...\n")

    for tc in TEST_CASES:
        t_start = time.time()
        try:
            parsed = parse_question(tc["question"])
            planner = QueryPlanner(db)
            result = planner.plan_and_execute(parsed)

            actual_intent = result.get("intent")
            actual_function = result.get("selected_function")
            actual_status = result.get("status")

            intent_correct = actual_intent == tc["expected_intent"]
            function_correct = actual_function == tc["expected_function"]
            status_correct = actual_status == tc["expected_status"]
            entity_score = calculate_entity_score(parsed, tc)
            end_to_end = intent_correct and function_correct and status_correct

            exec_ms = (time.time() - t_start) * 1000
            emoji = "[PASS]" if end_to_end else "[FAIL]"
            print(f"  {emoji} {tc['id']}: {tc['question'][:60]}")
            if not end_to_end:
                print(f"      Expected: intent={tc['expected_intent']}, fn={tc['expected_function']}, status={tc['expected_status']}")
                print(f"      Actual:   intent={actual_intent}, fn={actual_function}, status={actual_status}")

            results.append({
                "test_case_id": tc["id"],
                "question": tc["question"],
                "category": tc.get("category", ""),
                "expected_intent": tc["expected_intent"],
                "actual_intent": actual_intent,
                "intent_correct": intent_correct,
                "expected_function": tc["expected_function"],
                "actual_function": actual_function,
                "function_correct": function_correct,
                "expected_status": tc["expected_status"],
                "actual_status": actual_status,
                "status_correct": status_correct,
                "entity_extraction_score": entity_score,
                "end_to_end_correct": end_to_end,
                "execution_time_ms": round(exec_ms, 2),
                "error_category": tc.get("category") if not end_to_end else None,
                "notes": None,
            })

        except Exception as e:
            exec_ms = (time.time() - t_start) * 1000
            print(f"  [ERROR] {tc['id']}: {e}")
            results.append({
                "test_case_id": tc["id"],
                "question": tc["question"],
                "category": tc.get("category", ""),
                "expected_intent": tc["expected_intent"],
                "actual_intent": None,
                "intent_correct": False,
                "expected_function": tc["expected_function"],
                "actual_function": None,
                "function_correct": False,
                "expected_status": tc["expected_status"],
                "actual_status": "error",
                "status_correct": False,
                "entity_extraction_score": 0.0,
                "end_to_end_correct": False,
                "execution_time_ms": round(exec_ms, 2),
                "error_category": "exception",
                "notes": str(e),
            })

    db.close()

    # Save to DB
    db2 = get_sync_db()
    # Clear old results
    db2.query(EvaluationResult).delete()
    for r in results:
        er = EvaluationResult(
            test_case_id=r["test_case_id"],
            input_question=r["question"],
            expected_intent=r["expected_intent"],
            actual_intent=r["actual_intent"],
            intent_correct=r["intent_correct"],
            expected_function=r["expected_function"],
            actual_function=r["actual_function"],
            function_correct=r["function_correct"],
            expected_status=r["expected_status"],
            actual_status=r["actual_status"],
            status_correct=r["status_correct"],
            entity_extraction_score=r["entity_extraction_score"],
            end_to_end_correct=r["end_to_end_correct"],
            execution_time_ms=r["execution_time_ms"],
            error_category=r["error_category"],
            notes=r["notes"],
        )
        db2.add(er)
    db2.commit()
    db2.close()

    # Calculate metrics
    total = len(results)
    intent_ok = sum(1 for r in results if r["intent_correct"])
    fn_ok = sum(1 for r in results if r["function_correct"])
    status_ok = sum(1 for r in results if r["status_correct"])
    e2e_ok = sum(1 for r in results if r["end_to_end_correct"])
    unsupported = [r for r in results if r.get("category") in ("unsupported",)]
    unsup_ok = sum(1 for r in unsupported if r["status_correct"])
    entity_scores = [r["entity_extraction_score"] for r in results if r["entity_extraction_score"] is not None]
    entity_acc = sum(entity_scores) / len(entity_scores) * 100 if entity_scores else 0
    avg_time = sum(r["execution_time_ms"] for r in results) / total

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_test_cases": total,
        "passed": e2e_ok,
        "failed": total - e2e_ok,
        "intent_accuracy_pct": round(intent_ok / total * 100, 2),
        "entity_accuracy_pct": round(entity_acc, 2),
        "function_accuracy_pct": round(fn_ok / total * 100, 2),
        "db_success_rate_pct": round(status_ok / total * 100, 2),
        "end_to_end_accuracy_pct": round(e2e_ok / total * 100, 2),
        "unsupported_handling_pct": round(unsup_ok / len(unsupported) * 100, 2) if unsupported else 0,
        "avg_response_time_ms": round(avg_time, 2),
    }

    # Save JSON
    eval_dir = Path(__file__).parent.parent / "evaluation"
    eval_dir.mkdir(exist_ok=True)

    with open(eval_dir / "results.json", "w") as f:
        json.dump({"metrics": report, "results": results}, f, indent=2)

    with open(eval_dir / "results.csv", "w", newline="") as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    # Markdown report
    with open(eval_dir / "evaluation_report.md", "w", encoding="utf-8") as f:
        f.write("# Groundwater AI Agent — Evaluation Report\n\n")
        f.write(f"**Generated:** {report['timestamp']}\n\n")
        f.write("## Summary\n\n")
        f.write(f"| Metric | Value |\n|---|---|\n")
        for k, v in report.items():
            if k != "timestamp":
                f.write(f"| {k.replace('_', ' ').title()} | {v} |\n")
        f.write("\n## Detailed Results\n\n")
        f.write("| ID | Question | Intent OK | Fn OK | Status OK | E2E OK | Time (ms) |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in results:
            f.write(
                f"| {r['test_case_id']} | {r['question'][:50]} | "
                f"{'PASS' if r['intent_correct'] else 'FAIL'} | "
                f"{'PASS' if r['function_correct'] else 'FAIL'} | "
                f"{'PASS' if r['status_correct'] else 'FAIL'} | "
                f"{'PASS' if r['end_to_end_correct'] else 'FAIL'} | "
                f"{r['execution_time_ms']:.1f} |\n"
            )

    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    for k, v in report.items():
        if k != "timestamp":
            print(f"  {k:40s}: {v}")
    print("="*60)
    print(f"\n[OK] Results saved to evaluation/")
    return report


if __name__ == "__main__":
    run_evaluation()

