"""
End-to-End Real Conversation Test Suite
Tests the 10-turn conversation sequence against the live running FastAPI backend.
"""
import sys
sys.path.insert(0, "backend")
import json
import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
SESSION_ID = f"test_e2e_session_{int(time.time())}"

TURNS = [
    {
        "turn": 1,
        "question": "What is groundwater extraction in Patna in 2022?",
        "expected_substrings": ["174,600", "Ham"],
        "expect_db_function": "get_groundwater_extraction",
        "description": "Initial factual query for Patna 2022 extraction."
    },
    {
        "turn": 2,
        "question": "What about 2025?",
        "expected_substrings": ["59,747.83", "Ham"],
        "expect_db_function": "get_groundwater_extraction",
        "description": "Follow-up year only: retains Patna and extraction, updates to 2025."
    },
    {
        "turn": 3,
        "question": "Compare both.",
        "expected_substrings": ["174,600", "59,747.83", "decreased"],
        "expect_db_function": "compare_assessment_years",
        "description": "Follow-up comparison: compares 2022 and 2025."
    },
    {
        "turn": 4,
        "question": "What about 2020?",
        "expected_substrings": ["Verified data for this location, parameter and assessment year is not currently available", "2025"],
        "expect_db_function": "get_groundwater_extraction",
        "description": "Unavailable year: explains 2020 status and points to latest verified year (2025) without losing context."
    },
    {
        "turn": 5,
        "question": "And 2026?",
        "expected_substrings": ["Verified data for this location, parameter and assessment year is not currently available", "2025"],
        "expect_db_function": "get_groundwater_extraction",
        "description": "Future unavailable year: explains 2026 CGWB status and points to latest verified year (2025)."
    },
    {
        "turn": 6,
        "question": "What about recharge?",
        "expected_substrings": ["311,600", "Ham"],
        "expect_db_function": "get_groundwater_recharge",
        "description": "Parameter follow-up: retains Patna and retrieves verified recharge (2022: 311,600 Ham)."
    },
    {
        "turn": 7,
        "question": "Hi.",
        "expected_substrings": ["Groundwater AI"],
        "expect_db_function": None,
        "description": "Pure greeting: natural response, zero database calls, preserves active context."
    },
    {
        "turn": 8,
        "question": "How are you?",
        "expected_substrings": ["doing well"],
        "expect_db_function": None,
        "description": "Small talk: natural conversational answer, zero database calls, preserves active context."
    },
    {
        "turn": 9,
        "question": "Explain that result.",
        "expected_substrings": ["recharge", "GEC-2015"],
        "expect_db_function": None,
        "description": "Follow-up explanation: explains previous recharge figure from context without executing unrelated DB query."
    },
    {
        "turn": 10,
        "question": "What about Punjab?",
        "expected_substrings": ["Punjab", "1,852,400", "Ham"],
        "expect_db_function": "get_groundwater_recharge",
        "description": "Location follow-up: retains recharge and 2022, sets state to Punjab, aggregates recharge across Punjab."
    }
]

def run_e2e_tests():
    print(f"======================================================================")
    print(f"STARTING LIVE E2E CONVERSATION TEST (Session: {SESSION_ID})")
    print(f"Target: FastAPI TestClient (/api/chat)")
    print(f"======================================================================\n")

    results = []
    all_passed = True

    for item in TURNS:
        t_num = item["turn"]
        q = item["question"]
        desc = item["description"]
        exp_subs = item["expected_substrings"]
        exp_func = item["expect_db_function"]

        print(f"--- TURN {t_num}: '{q}' ---")
        print(f"Description: {desc}")

        payload = {
            "question": q,
            "session_id": SESSION_ID,
            "mode": "hybrid"
        }

        try:
            resp = client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"FAILED TO CALL API: {e}")
            all_passed = False
            results.append({"turn": t_num, "status": "FAIL", "error": str(e)})
            continue

        answer = data.get("answer", "")
        intent = data.get("intent")
        func_called = data.get("selected_function")
        active_ctx = data.get("active_context", {})
        exec_ms = data.get("execution_time_ms", 0)

        print(f"Intent: {intent}")
        print(f"Function Called: {func_called} (Expected: {exp_func})")
        print(f"Active Context: {active_ctx}")
        print(f"Execution Time: {exec_ms} ms")
        print(f"Answer Preview:\n{answer[:250]}...")

        # Assertions
        missing_subs = [s for s in exp_subs if s not in answer]
        func_matches = (func_called == exp_func)

        turn_passed = (len(missing_subs) == 0) and func_matches

        if not turn_passed:
            all_passed = False
            print(f">>> TEST FAILED <<<")
            if missing_subs:
                print(f"Missing substrings: {missing_subs}")
            if not func_matches:
                print(f"Function mismatch: got {func_called}, expected {exp_func}")
        else:
            print(f">>> TEST PASSED <<<")

        results.append({
            "turn": t_num,
            "question": q,
            "intent": intent,
            "function": func_called,
            "exec_ms": exec_ms,
            "passed": turn_passed,
            "active_context": active_ctx,
            "answer": answer
        })
        print()

    print("======================================================================")
    print(f"E2E TEST SUMMARY: {'ALL 10 TURNS PASSED!' if all_passed else 'SOME TURNS FAILED'}")
    print("======================================================================")

    # Save results to json for reporting
    with open("evaluation/e2e_live_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_e2e_tests()
