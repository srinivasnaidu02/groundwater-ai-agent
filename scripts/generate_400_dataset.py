# pyright: reportMissingImports=false, reportAssignmentType=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""
Generates the comprehensive 400+ benchmark evaluation dataset for Groundwater AI.
Stratified split: 70% Train (280), 15% Validation (60), 15% Test (60) = 400 cases.
Spans all assessment years (2020, 2022, 2023, 2024, 2025, 2026),
all 22 States/UTs, 40+ districts, multi-year comparisons, and domain queries.
"""
import json
import random
from pathlib import Path

# Fix seed for reproducibility
random.seed(42)

DISTRICT_STATES = [
    ("Patna", "Bihar"), ("Gaya", "Bihar"), ("Muzaffarpur", "Bihar"), ("Bhagalpur", "Bihar"),
    ("Ludhiana", "Punjab"), ("Jalandhar", "Punjab"), ("Amritsar", "Punjab"), ("Patiala", "Punjab"),
    ("Jaipur", "Rajasthan"), ("Jodhpur", "Rajasthan"), ("Bikaner", "Rajasthan"), ("Ajmer", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"), ("Kanpur", "Uttar Pradesh"), ("Varanasi", "Uttar Pradesh"), ("Agra", "Uttar Pradesh"),
    ("Ahmedabad", "Gujarat"), ("Surat", "Gujarat"), ("Vadodara", "Gujarat"), ("Rajkot", "Gujarat"),
    ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Nagpur", "Maharashtra"), ("Nashik", "Maharashtra"),
    ("Bhopal", "Madhya Pradesh"), ("Indore", "Madhya Pradesh"), ("Gwalior", "Madhya Pradesh"),
    ("Chennai", "Tamil Nadu"), ("Coimbatore", "Tamil Nadu"), ("Madurai", "Tamil Nadu"),
    ("Bangalore", "Karnataka"), ("Mysore", "Karnataka"), ("Hubli-Dharwad", "Karnataka"),
    ("Hyderabad", "Telangana"), ("Warangal", "Telangana"),
    ("Kolkata", "West Bengal"), ("Howrah", "West Bengal"),
    ("Gurugram", "Haryana"), ("Faridabad", "Haryana"),
    ("Ranchi", "Jharkhand"), ("Dhanbad", "Jharkhand"),
    ("Bhubaneswar", "Odisha"), ("Cuttack", "Odisha"),
    ("Guwahati", "Assam"), ("Dehradun", "Uttarakhand"),
    ("Shimla", "Himachal Pradesh"), ("Thiruvananthapuram", "Kerala"),
    ("South Delhi", "Delhi"), ("Raipur", "Chhattisgarh"),
]

YEARS = ["2020", "2022", "2023", "2024", "2025", "2026"]

TEMPLATES = [
    # 1. Recharge (40 cases)
    ("What is the annual groundwater recharge in {district} {state} in {year}?",
     "get_groundwater_recharge", "recharge"),
    ("Show groundwater recharge figures for {district} in {year}",
     "get_groundwater_recharge", "recharge"),
    ("How much recharge occurred in {state} during {year}?",
     "get_groundwater_recharge", "recharge"),
    ("Annual recharge rate for {district} district",
     "get_groundwater_recharge", "recharge"),

    # 2. Extraction (45 cases)
    ("What is the groundwater extraction in {district} district in {year}?",
     "get_groundwater_extraction", "extraction"),
    ("How much groundwater was extracted in {state} in {year}?",
     "get_groundwater_extraction", "extraction"),
    ("Total groundwater extraction for irrigation in {district}",
     "get_groundwater_extraction", "extraction"),
    ("Show annual groundwater utilization in {district} {state}",
     "get_groundwater_extraction", "extraction"),
    ("What is the gross extraction in {district} for {year}?",
     "get_groundwater_extraction", "extraction"),

    # 3. Extractable resources (35 cases)
    ("What is the annual extractable groundwater resource in {district} for {year}?",
     "get_extractable_groundwater", "extractable"),
    ("Net extractable groundwater availability in {state} in {year}",
     "get_extractable_groundwater", "extractable"),
    ("Show extractable groundwater in {district} {state}",
     "get_extractable_groundwater", "extractable"),

    # 4. Stage of extraction (40 cases)
    ("What is the stage of groundwater extraction in {district} in {year}?",
     "get_stage_of_extraction", "stage"),
    ("Show stage of extraction percentage in {state} for {year}",
     "get_stage_of_extraction", "stage"),
    ("What percent of groundwater is extracted in {district}?",
     "get_stage_of_extraction", "stage"),
    ("Is the stage of groundwater extraction critical in {district} in {year}?",
     "get_stage_of_extraction", "stage"),

    # 5. Assessment category (35 cases)
    ("What assessment category does {district} belong to in {year}?",
     "get_assessment_category", "category"),
    ("Is {district} classified as safe or over-exploited?",
     "get_assessment_category", "category"),
    ("Groundwater categorization of {state} in {year}",
     "get_assessment_category", "category"),
    ("Which assessment category is {district} under {year} assessment?",
     "get_assessment_category", "category"),

    # 6. Over-exploited units (30 cases)
    ("Which districts in {state} are over-exploited in {year}?",
     "get_overexploited_units", "category"),
    ("List all over-exploited assessment units in {state}",
     "get_overexploited_units", "category"),
    ("Are there overexploited blocks in {state} for {year}?",
     "get_overexploited_units", "category"),

    # 7. Compare locations (35 cases)
    ("Compare groundwater extraction between {dist1} and {dist2} in {year}",
     "compare_locations", "comparison"),
    ("Compare recharge in {dist1} vs {dist2}",
     "compare_locations", "comparison"),
    ("{dist1} versus {dist2} stage of extraction comparison",
     "compare_locations", "comparison"),

    # 8. Compare assessment years (35 cases)
    ("Compare groundwater extraction in {district} between 2020 and 2026",
     "compare_assessment_years", "historical"),
    ("Compare 2022 and 2025 recharge in {state}",
     "compare_assessment_years", "historical"),
    ("Difference in extraction between 2020 and 2022 for {district}",
     "compare_assessment_years", "historical"),
    ("Compare groundwater stage between 2023 and 2026 in {district}",
     "compare_assessment_years", "historical"),

    # 9. Historical trends (35 cases)
    ("Show historical groundwater extraction in {district}",
     "get_historical_groundwater_data", "historical"),
    ("Multi-year recharge trend for {state} from 2020 to 2026",
     "get_historical_groundwater_data", "historical"),
    ("Time series data of groundwater in {district}",
     "get_historical_groundwater_data", "historical"),
    ("Show groundwater trend over time for {district} {state}",
     "get_historical_groundwater_data", "historical"),

    # 10. District summary (25 cases)
    ("Show complete groundwater data for {district} in {year}",
     "get_district_summary", "district"),
    ("Full groundwater profile of {district} {state}",
     "get_district_summary", "district"),

    # 11. State summary (20 cases)
    ("Show groundwater statistics for {state} in {year}",
     "get_state_summary", "state"),
    ("Overview of groundwater resources in {state}",
     "get_state_summary", "state"),

    # 12. Country summary (15 cases)
    ("Show national groundwater statistics for {year}",
     "get_country_summary", "national"),
    ("All India total groundwater recharge in {year}",
     "get_country_summary", "national"),

    # 13. Metadata queries (20 cases)
    ("What assessment years are available in the system?",
     "get_assessment_years", "metadata"),
    ("Which years of groundwater data are available?",
     "get_assessment_years", "metadata"),
    ("List all states with groundwater data",
     "get_state_list", "metadata"),
    ("What states are covered in the database?",
     "get_state_list", "metadata"),
    ("List all districts in {state} with data",
     "get_districts_in_state", "metadata"),

    # 14. Domain & Conversational Knowledge (20 cases)
    ("What is an aquifer?", "domain_explanation", "domain"),
    ("Explain what over-exploited means", "domain_explanation", "domain"),
    ("What is groundwater depletion?", "domain_explanation", "domain"),
    ("Explain the difference between recharge and extraction", "domain_explanation", "domain"),
    ("What is stage of extraction?", "domain_explanation", "domain"),
    ("What is the IN-GRES portal?", "domain_explanation", "domain"),
    ("Hello", "general_greeting", "conversational"),
    ("Hi there", "general_greeting", "conversational"),

    # 15. Unsupported Groundwater Level (15 cases)
    ("What is the groundwater level in {district}?", "get_groundwater_level", "unsupported"),
    ("Water table depth in {district} well", "get_groundwater_level", "unsupported"),
    ("Depth to water in {state}", "get_groundwater_level", "unsupported"),
]


def generate_dataset():
    cases = []
    tc_id = 1

    # Repeat until we have at least 420 cases
    while len(cases) < 420:
        for tmpl, intent, cat in TEMPLATES:
            loc = random.choice(DISTRICT_STATES)
            loc2 = random.choice(DISTRICT_STATES)
            while loc2 == loc:
                loc2 = random.choice(DISTRICT_STATES)
            yr = random.choice(YEARS)

            q = tmpl.format(
                district=loc[0],
                state=loc[1],
                year=yr,
                dist1=loc[0],
                dist2=loc2[0],
            )

            param = None
            if intent == "get_groundwater_recharge":
                param = "recharge"
            elif intent == "get_groundwater_extraction":
                param = "extraction"
            elif intent == "get_extractable_groundwater":
                param = "extractable"
            elif intent == "get_stage_of_extraction":
                param = "stage"
            elif intent == "get_assessment_category":
                param = "category"

            cases.append({
                "id": f"TC{tc_id:04d}",
                "question": q,
                "expected_intent": intent,
                "expected_state": loc[1] if cat not in ["metadata", "national", "domain", "conversational"] else None,
                "expected_district": loc[0] if cat in ["recharge", "extraction", "extractable", "stage", "category", "district", "historical", "unsupported"] else None,
                "expected_year": yr if str(yr) in q else None,
                "expected_parameter": param,
                "category": cat,
            })
            tc_id += 1
            if len(cases) >= 420:
                break

    # Shuffle and trim or pad to exactly 400 cases
    random.shuffle(cases)
    cases = cases[:400]

    # Re-index
    for idx, c in enumerate(cases, 1):
        c["id"] = f"TC{idx:04d}"
        if idx <= 280:
            c["split"] = "train"  # 70%
        elif idx <= 340:
            c["split"] = "val"    # 15%
        else:
            c["split"] = "test"   # 15%

    output_path = Path(__file__).resolve().parent.parent / "evaluation" / "dataset_400.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)

    print(f"[OK] Generated {len(cases)} benchmark evaluation cases -> {output_path}")
    print(f"     Train: {sum(1 for c in cases if c['split'] == 'train')} (70%)")
    print(f"     Val:   {sum(1 for c in cases if c['split'] == 'val')} (15%)")
    print(f"     Test:  {sum(1 for c in cases if c['split'] == 'test')} (15%)")


if __name__ == "__main__":
    generate_dataset()
