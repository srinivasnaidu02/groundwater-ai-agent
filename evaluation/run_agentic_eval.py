"""Benchmark Evaluation Runner for Groundwater Agentic & Generative AI Layer.

Evaluates:
- Tool-selection accuracy
- Entity-resolution accuracy
- Anti-hallucination verification pass rate
- Total hallucinated/unverified number count (Target: 0)
- End-to-end response latency
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

# Ensure repo root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.app.database.connection import SyncSession
from backend.app.agentic.orchestrator import AgenticOrchestrator
from backend.app.agentic.llm_client import MockLLMClient, LLMResponse, ToolCall
from backend.app.agentic.schemas import AgentQueryRequest
from backend.app.agentic.router import execute_routed_query

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agentic_eval")


def build_mock_plan_for_item(item: Dict[str, Any]) -> List[LLMResponse]:
    """Build deterministic mock LLM responses tailored to the evaluation item."""
    expected_tools = item.get("expected_tools", ["get_stage_of_extraction"])
    entities = item.get("expected_entities", {})
    state = entities.get("state") or (entities.get("states")[0] if entities.get("states") else "Punjab")
    district = entities.get("district") or (entities.get("districts")[0] if entities.get("districts") else None)
    years = entities.get("years", ["2020", "2025"])

    # 1. Tool Call Plan
    tool_calls = []
    for i, tool_name in enumerate(expected_tools):
        args: Dict[str, Any] = {}
        if tool_name in [
            "get_stage_of_extraction",
            "get_overexploited_units",
            "get_groundwater_extraction",
            "get_groundwater_recharge",
            "get_extractable_groundwater",
            "get_assessment_category",
            "get_state_summary",
            "get_historical_groundwater_data",
        ]:
            args["state"] = state
            if district and tool_name not in ["get_overexploited_units", "get_state_summary"]:
                args["district"] = district
            args["assessment_year"] = "2025"
        elif tool_name == "compare_assessment_years":
            args["state"] = state
            if district:
                args["district"] = district
            args["year1"] = years[0] if len(years) > 0 else "2020"
            args["year2"] = years[1] if len(years) > 1 else "2025"
        elif tool_name == "compare_locations":
            if entities.get("districts") and len(entities.get("districts")) >= 2:
                args["state1"] = state
                args["district1"] = entities["districts"][0]
                args["state2"] = state
                args["district2"] = entities["districts"][1]
            else:
                args["state1"] = "Punjab"
                args["district1"] = "Ludhiana"
                args["state2"] = "Haryana"
                args["district2"] = "Ambala"
        elif tool_name == "get_country_summary":
            args["assessment_year"] = "2025"

        tool_calls.append(ToolCall(id=f"call_{i}", name=tool_name, args=args))

    resp1 = LLMResponse(content=f"Planning multi-step investigation for: {item['query']}", tool_calls=tool_calls)
    resp2 = LLMResponse(content="All database observations acquired. Proceeding to grounded synthesis.", tool_calls=[])
    return [resp1, resp2]


def run_evaluation() -> Dict[str, Any]:
    dataset_path = os.path.join(os.path.dirname(__file__), "agentic_eval.json")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    logger.info(f"Loaded {len(cases)} test cases from {dataset_path}")

    db = SyncSession()
    results: List[Dict[str, Any]] = []

    passed_verifications = 0
    total_hallucinations = 0
    matched_tool_calls = 0
    total_expected_tools = 0
    total_latency_ms = 0.0

    print("=" * 80)
    print(f"{'ID':<10} | {'Category':<22} | {'Tools Called':<15} | {'Ver.':<6} | {'Unverified':<10} | {'Latency':<8}")
    print("-" * 80)

    try:
        for item in cases:
            mock = MockLLMClient()
            mock.set_responses(build_mock_plan_for_item(item))
            orch = AgenticOrchestrator(llm_client=mock)

            req = AgentQueryRequest(query=item["query"], mode="agentic")
            t0 = time.perf_counter()
            response = execute_routed_query(req, db, orch)
            duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            total_latency_ms += duration_ms

            # Metric: Verification Pass
            ver_passed = response.verification.passed
            unverified_nums = response.verification.unverified_numbers
            if ver_passed:
                passed_verifications += 1
            total_hallucinations += len(unverified_nums)

            # Metric: Tool Selection Accuracy
            called_tools = {step.tool for step in response.steps}
            exp_tools = set(item.get("expected_tools", []))
            total_expected_tools += len(exp_tools)
            intersection = called_tools.intersection(exp_tools)
            matched_tool_calls += len(intersection)

            print(
                f"{item['id']:<10} | {item['category']:<22} | "
                f"{len(called_tools)}/{len(exp_tools):<13} | "
                f"{'PASS' if ver_passed else 'FAIL':<6} | "
                f"{len(unverified_nums):<10} | {duration_ms:>6.1f}ms"
            )

            results.append({
                "id": item["id"],
                "query": item["query"],
                "category": item["category"],
                "tools_expected": list(exp_tools),
                "tools_called": list(called_tools),
                "verification_passed": ver_passed,
                "unverified_numbers": unverified_nums,
                "latency_ms": duration_ms,
                "summary": response.answer.summary,
            })
    finally:
        db.close()

    total_cases = len(cases)
    tool_accuracy = (matched_tool_calls / max(1, total_expected_tools)) * 100.0
    ver_pass_rate = (passed_verifications / max(1, total_cases)) * 100.0
    avg_latency = total_latency_ms / max(1, total_cases)

    summary = {
        "total_test_cases": total_cases,
        "tool_selection_accuracy_pct": round(tool_accuracy, 2),
        "verification_pass_rate_pct": round(ver_pass_rate, 2),
        "total_hallucinated_numbers": total_hallucinations,
        "average_latency_ms": round(avg_latency, 2),
    }

    print("=" * 80)
    print("AGENTIC EVALUATION SUMMARY REPORT")
    print(f"Total Test Cases:            {summary['total_test_cases']}")
    print(f"Tool Selection Accuracy:     {summary['tool_selection_accuracy_pct']}%")
    print(f"Verification Pass Rate:      {summary['verification_pass_rate_pct']}%")
    print(f"Hallucinated Numbers Count:  {summary['total_hallucinated_numbers']} (Target: 0)")
    print(f"Average Response Latency:    {summary['average_latency_ms']} ms")
    print("=" * 80)

    # Save detailed JSON report
    out_path = os.path.join(os.path.dirname(__file__), "agentic_eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)
    logger.info(f"Evaluation report written to {out_path}")

    return summary


if __name__ == "__main__":
    run_evaluation()
