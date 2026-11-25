"""ReAct loop orchestrator with parallel tool execution, duplicate suppression, and timeout guards."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.agentic.config import AgenticSettings, get_agentic_settings
from backend.app.agentic.llm_client import LLMClient, LLMResponse, ToolCall, get_llm_client
from backend.app.agentic.schemas import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentStep,
    CompletenessReport,
    EvidenceItem,
    NumericVerification,
)
from backend.app.agentic.synthesizer import GroundedSynthesizer, build_template_answer
from backend.app.agentic.tools import ToolRegistry, default_tool_registry, ALIAS_MAP, STATE_ALIASES, ALL_STATES
from backend.app.agentic.verifier import NumericVerifier
from backend.app.agentic.query_parser import parse_query, LocationEntity
from backend.app.agentic.comparison_helper import (
    compute_comparison_matrix,
    check_completeness,
    METRIC_CONFIG,
    _matches_location,
    extract_metric_value,
)
import re

logger = logging.getLogger(__name__)

ORCHESTRATOR_SYSTEM_PROMPT = """You are the autonomous Query Orchestrator for the official Indian Groundwater Database.
Your task is to analyze complex or multi-part questions, devise a step-by-step query plan, and call the available database tools to gather verified empirical evidence.

=== STRICT GROUNDING RULES ===
1. Use ONLY tools to gather data. You do NOT have direct database access.
2. Call all necessary tools to answer the question thoroughly.
3. When sufficient evidence is collected, respond with your final reasoning (no tool calls).
"""


def _make_cache_key(tool_name: str, args: Dict[str, Any]) -> str:
    sorted_items = sorted((k, str(v)) for k, v in args.items())
    return f"{tool_name}::" + json.dumps(sorted_items)


def _extract_query_overrides(query: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract explicit year, state, or district from query text if present."""
    q_lower = query.lower()

    # Check explicit year
    m_year = re.search(r"\b(2020|2022|2023|2024|2025|2026)\b", query)
    q_year = m_year.group(1) if m_year else None

    # Check explicit district first (so e.g. 'Ludhiana' infers Punjab if not specified)
    q_dist = None
    q_state = None
    for alias, (mapped_dist, mapped_state) in ALIAS_MAP.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", q_lower):
            q_dist = mapped_dist
            q_state = mapped_state
            break

    # Check explicit state if not set by district
    if not q_state:
        for full_state in ALL_STATES:
            if full_state.lower() in q_lower:
                q_state = full_state
                break
    if not q_state:
        for alias, full_state in STATE_ALIASES.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", q_lower):
                q_state = full_state
                break

    return q_year, q_state, q_dist


class AgenticOrchestrator:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        config: Optional[AgenticSettings] = None,
        verifier: Optional[NumericVerifier] = None,
        synthesizer: Optional[GroundedSynthesizer] = None,
    ):
        self.config = config or get_agentic_settings()
        self.llm_client = llm_client or get_llm_client()
        self.tool_registry = tool_registry or default_tool_registry
        self.verifier = verifier or NumericVerifier()
        self.synthesizer = synthesizer or GroundedSynthesizer(self.llm_client)

    async def run(
        self,
        query: str,
        mode: str = "agentic",
        hints: Optional[Dict[str, Any]] = None,
    ) -> AgentQueryResponse:
        start_time = time.perf_counter()
        steps: List[AgentStep] = []
        evidence_items: List[Dict[str, Any]] = []
        citations: Set[str] = set()
        cache: Dict[str, Dict[str, Any]] = {}
        tool_call_counts: Dict[str, int] = {}

        parsed = parse_query(query, hints=hints)
        year = parsed.years[0] if parsed.years else str((hints or {}).get("year") or "2025")

        # FAST PATH: Template mode (no LLM call)
        if mode == "template" or not self.config.has_api_key():
            return await self._run_template_pipeline(
                query=query,
                hints=hints,
                start_time=start_time,
                mode_used="template" if mode == "template" else "template_fallback",
            )

        # RE-ACT LOOP
        context_parts = []
        if hints:
            if hints.get("year"):
                context_parts.append(f"year: {hints['year']}")
            if hints.get("state"):
                context_parts.append(f"state: {hints['state']}")
            if hints.get("district") and hints["district"] != "State-level (no district)":
                context_parts.append(f"district: {hints['district']}")

        if context_parts:
            context_str = ", ".join(context_parts)
            prompt_with_hints = (
                f"{query}\n"
                f"Selected context -> {context_str} (use as defaults if the question does not specify otherwise)."
            )
        else:
            prompt_with_hints = query

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_with_hints},
        ]

        step_num = 1
        tool_schemas = self.tool_registry.get_schemas()
        partial_evidence = False

        while step_num <= self.config.AGENT_MAX_STEPS:
            elapsed = time.perf_counter() - start_time
            if elapsed >= self.config.AGENT_TIMEOUT_SECONDS:
                logger.warning("Agent execution timeout reached. Proceeding with partial evidence.")
                partial_evidence = True
                break

            try:
                resp = await self.llm_client.chat(messages=messages, tools=tool_schemas)
            except Exception as e:
                logger.error(f"LLM chat failure in orchestrator: {e}. Falling back to template.")
                return await self._run_template_pipeline(
                    query=query,
                    hints=hints,
                    start_time=start_time,
                    mode_used="template_fallback",
                )

            # Check if LLM finished planning (no tool calls)
            if not resp or not resp.tool_calls:
                break

            # Separate cached vs uncached calls
            uncached_calls: List[ToolCall] = []
            for tc in resp.tool_calls:
                ckey = _make_cache_key(tc.name, tc.arguments)
                if ckey in cache:
                    cached_res = cache[ckey]
                    steps.append(
                        AgentStep(
                            step_number=step_num,
                            thought="[Cached] Duplicate call suppressed; re-using observation",
                            tool_called=tc.name,
                            arguments=tc.arguments,
                            result_summary="Cached tool result reused",
                            latency_ms=0.0,
                        )
                    )
                    step_num += 1
                else:
                    uncached_calls.append(tc)

            if not uncached_calls:
                break

            # Execute independent tool calls in parallel using asyncio.gather
            async def _run_tool(tc_call: ToolCall):
                t0 = time.perf_counter()
                res = await asyncio.to_thread(self.tool_registry.run, tc_call.name, **tc_call.arguments)
                dur = round((time.perf_counter() - t0) * 1000.0, 2)
                return tc_call, res, dur

            tool_results = await asyncio.gather(*[_run_tool(c) for c in uncached_calls])

            for tc_call, res, dur in tool_results:
                ckey = _make_cache_key(tc_call.name, tc_call.arguments)
                cache[ckey] = res
                tool_call_counts[tc_call.name] = tool_call_counts.get(tc_call.name, 0) + 1

                step_thought = resp.content or f"Calling tool {tc_call.name}"
                steps.append(
                    AgentStep(
                        step_number=step_num,
                        thought=step_thought,
                        tool_called=tc_call.name,
                        arguments=tc_call.arguments,
                        result_summary=f"{tc_call.name} executed successfully",
                        latency_ms=dur,
                    )
                )

                # Append to evidence ledger
                ev_entry = {
                    "tool_name": tc_call.name,
                    "arguments": tc_call.arguments,
                    "result": res,
                    "unit": res.get("unit", "Ham"),
                    "year": res.get("year", year),
                    "source": res.get("source", "CGWB National Compilation"),
                    "verification": res.get("verification", "CGWB-verified"),
                }
                evidence_items.append(ev_entry)
                if res.get("source"):
                    citations.add(res["source"])

                # Feed observation back to conversation history
                messages.append({
                    "role": "tool",
                    "content": f"Observation from {tc_call.name}:\n{json.dumps(res, default=str)}",
                    "name": tc_call.name,
                })

                step_num += 1
                if step_num > self.config.AGENT_MAX_STEPS:
                    partial_evidence = True
                    break

        if step_num > self.config.AGENT_MAX_STEPS:
            partial_evidence = True

        # Precompute comparison data & derived arithmetic
        comparison_data, derived_ev = compute_comparison_matrix(
            locations=parsed.locations,
            metrics=parsed.metrics,
            year=year,
            evidence_items=evidence_items,
        )
        if derived_ev:
            evidence_items.extend(derived_ev)

        # Completeness Guard
        completeness_rep = check_completeness(parsed.locations, parsed.metrics, evidence_items)
        if not completeness_rep.complete:
            # (1) Try one extra tool round to fetch missing data
            missing_recovered = False
            for loc in parsed.locations:
                for m in parsed.metrics:
                    cfg = METRIC_CONFIG.get(m)
                    if not cfg:
                        continue
                    has_it = any(
                        _matches_location(it, loc) and extract_metric_value(it, m) is not None
                        for it in evidence_items
                    )
                    if not has_it:
                        t_name = cfg["tool"]
                        t_args = {"state": loc.state, "assessment_year": year}
                        if loc.district:
                            t_args["district"] = loc.district
                        try:
                            t_res = self.tool_registry.run(t_name, **t_args)
                            if not t_res.get("error"):
                                evidence_items.append({
                                    "tool_name": t_name,
                                    "arguments": t_args,
                                    "result": t_res,
                                    "unit": t_res.get("unit", cfg["unit"]),
                                    "year": t_res.get("year", year),
                                    "source": t_res.get("source", "CGWB National Compilation"),
                                    "verification": t_res.get("verification", "CGWB-verified"),
                                })
                                missing_recovered = True
                        except Exception as ex:
                            logger.warning(f"Error fetching missing data: {ex}")

            if missing_recovered:
                c_data, d_ev = compute_comparison_matrix(parsed.locations, parsed.metrics, year, evidence_items)
                if c_data:
                    comparison_data = c_data
                if d_ev:
                    evidence_items.extend(d_ev)
                completeness_rep = check_completeness(parsed.locations, parsed.metrics, evidence_items)

        # SYNTHESIS & VERIFICATION
        answer = await self.synthesizer.synthesize(query=query, evidence_items=evidence_items)
        if partial_evidence:
            answer["partial"] = True

        # If incomplete, record in limitations
        if not completeness_rep.complete:
            if "limitations" not in answer or not isinstance(answer["limitations"], list):
                answer["limitations"] = []
            for miss in completeness_rep.missing:
                limit_msg = f"Data for {miss} could not be retrieved from official CGWB compilation."
                if limit_msg not in answer["limitations"]:
                    answer["limitations"].append(limit_msg)

        # Populate missing location in numeric breakdown
        for row in answer.get("numeric_breakdown", []):
            if not row.get("location"):
                if parsed.locations:
                    row["location"] = parsed.locations[0].canonical_str()
                elif (hints or {}).get("state"):
                    st = hints["state"]
                    dt = hints.get("district")
                    row["location"] = f"{dt}, {st}" if dt and dt != "State-level (no district)" else st

        ver_res = self.verifier.verify(answer, evidence_items)

        # Regeneration attempt if unverified numbers detected
        if not ver_res.passed:
            logger.info("Verification failed on numbers. Attempting single regeneration.")
            regen_answer = await self.synthesizer.regenerate_with_flags(
                query=query,
                evidence_items=evidence_items,
                previous_output=answer,
                unverified_numbers=ver_res.checked_numbers,
            )
            regen_ver = self.verifier.verify(regen_answer, evidence_items)
            if regen_ver.passed:
                answer = regen_answer
                ver_res = regen_ver
                ver_res.regenerated = True
            else:
                logger.warning("Regeneration failed verification. Falling back to template answer.")
                answer = build_template_answer(query, evidence_items)
                ver_res = self.verifier.verify(answer, evidence_items)
                ver_res.fallback_used = True

        evidence_models = [
            EvidenceItem(
                tool_name=e["tool_name"],
                arguments=e["arguments"],
                result=e["result"],
                unit=e["unit"],
                year=e["year"],
                source=e["source"],
                verification=e["verification"],
            )
            for e in evidence_items
        ]

        total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)

        return AgentQueryResponse(
            answer=answer,
            mode_used="agentic",
            steps=steps,
            evidence=evidence_models,
            citations=list(citations),
            verification=ver_res,
            completeness=completeness_rep,
            comparison_data=comparison_data,
            override_note=parsed.override_note,
            latency_ms=total_latency,
            model=self.config.LLM_MODEL,
        )

    async def _run_template_pipeline(
        self,
        query: str,
        hints: Optional[Dict[str, Any]],
        start_time: float,
        mode_used: str,
    ) -> AgentQueryResponse:
        """Execute template pipeline using tools and evidence-only answers (no LLM)."""
        t0 = time.perf_counter()
        parsed = parse_query(query, hints=hints)
        year = parsed.years[0] if parsed.years else str((hints or {}).get("year") or "2025")

        evidence_items: List[Dict[str, Any]] = []
        citations: Set[str] = set()
        steps: List[AgentStep] = []
        step_idx = 1

        if parsed.intent == "compare_years" and len(parsed.years) >= 2:
            # Multi-year comparison
            loc = parsed.locations[0] if parsed.locations else LocationEntity(
                state=(hints or {}).get("state") or "Maharashtra",
                district=(hints or {}).get("district"),
            )
            m = parsed.metrics[0] if parsed.metrics else "stage_of_extraction"
            param = "stage" if m == "stage_of_extraction" else ("recharge" if m == "recharge" else "extraction")
            t_args = {
                "state": loc.state,
                "district": loc.district,
                "parameter": param,
                "year1": parsed.years[0],
                "year2": parsed.years[1],
            }
            t_res = self.tool_registry.run("compare_assessment_years", **t_args)
            steps.append(
                AgentStep(
                    step_number=1,
                    thought=f"Template execution: comparing {parsed.years[0]} and {parsed.years[1]} for {loc.canonical_str()}",
                    tool_called="compare_assessment_years",
                    arguments=t_args,
                    result_summary="Template tool execution completed",
                    latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                )
            )
            evidence_items.append({
                "tool_name": "compare_assessment_years",
                "arguments": t_args,
                "result": t_res,
                "unit": t_res.get("unit", "%" if param == "stage" else "Ham"),
                "year": f"{parsed.years[0]}-{parsed.years[1]}",
                "source": t_res.get("source", "CGWB National Compilation"),
                "verification": t_res.get("verification", "CGWB-verified"),
            })
            if t_res.get("source"):
                citations.add(t_res["source"])

        elif parsed.intent == "compare_locations" or len(parsed.locations) >= 2:
            # Multi-location comparison
            for loc in parsed.locations:
                for m in parsed.metrics:
                    cfg = METRIC_CONFIG.get(m)
                    t_name = cfg["tool"] if cfg else "get_groundwater_extraction"
                    t_args = {"state": loc.state, "assessment_year": year}
                    if loc.district:
                        t_args["district"] = loc.district
                    t_res = self.tool_registry.run(t_name, **t_args)
                    steps.append(
                        AgentStep(
                            step_number=step_idx,
                            thought=f"Template execution: running {t_name} for {loc.canonical_str()}",
                            tool_called=t_name,
                            arguments=t_args,
                            result_summary="Template tool execution completed",
                            latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                        )
                    )
                    step_idx += 1
                    evidence_items.append({
                        "tool_name": t_name,
                        "arguments": t_args,
                        "result": t_res,
                        "unit": t_res.get("unit", cfg["unit"] if cfg else "Ham"),
                        "year": t_res.get("year", year),
                        "source": t_res.get("source", "CGWB National Compilation"),
                        "verification": t_res.get("verification", "CGWB-verified"),
                    })
                    if t_res.get("source"):
                        citations.add(t_res["source"])
        else:
            # Single lookup
            loc = parsed.locations[0] if parsed.locations else LocationEntity(
                state=(hints or {}).get("state") or "Punjab",
                district=(hints or {}).get("district"),
            )
            m = parsed.metrics[0] if parsed.metrics else "extraction"
            cfg = METRIC_CONFIG.get(m)
            t_name = cfg["tool"] if cfg else "get_groundwater_extraction"
            t_args = {"state": loc.state, "assessment_year": year}
            if loc.district and loc.district != "State-level (no district)":
                t_args["district"] = loc.district

            if "overexploited" in query.lower() or "over-exploited" in query.lower():
                t_name = "get_overexploited_units"
                t_args = {"state": loc.state, "assessment_year": year}

            t_res = self.tool_registry.run(t_name, **t_args)
            dur = round((time.perf_counter() - t0) * 1000.0, 2)

            steps.append(
                AgentStep(
                    step_number=1,
                    thought="Template execution path: running tool",
                    tool_called=t_name,
                    arguments=t_args,
                    result_summary="Template tool execution completed",
                    latency_ms=dur,
                )
            )

            evidence_items.append({
                "tool_name": t_name,
                "arguments": t_args,
                "result": t_res,
                "unit": t_res.get("unit", cfg["unit"] if cfg else "Ham"),
                "year": t_res.get("year", year),
                "source": t_res.get("source", "CGWB National Compilation"),
                "verification": t_res.get("verification", "CGWB-verified"),
            })
            if t_res.get("source"):
                citations.add(t_res["source"])

        # Precompute comparison data & derived arithmetic
        comparison_data, derived_ev = compute_comparison_matrix(
            locations=parsed.locations,
            metrics=parsed.metrics,
            year=year,
            evidence_items=evidence_items,
        )
        if derived_ev:
            evidence_items.extend(derived_ev)

        # Completeness Guard
        completeness_rep = check_completeness(parsed.locations, parsed.metrics, evidence_items)
        if not completeness_rep.complete:
            # (1) Try one extra tool round to fetch missing data
            missing_recovered = False
            for loc in parsed.locations:
                for m in parsed.metrics:
                    cfg = METRIC_CONFIG.get(m)
                    if not cfg:
                        continue
                    has_it = any(
                        _matches_location(it, loc) and extract_metric_value(it, m) is not None
                        for it in evidence_items
                    )
                    if not has_it:
                        t_name = cfg["tool"]
                        t_args = {"state": loc.state, "assessment_year": year}
                        if loc.district:
                            t_args["district"] = loc.district
                        try:
                            t_res = self.tool_registry.run(t_name, **t_args)
                            if not t_res.get("error"):
                                evidence_items.append({
                                    "tool_name": t_name,
                                    "arguments": t_args,
                                    "result": t_res,
                                    "unit": t_res.get("unit", cfg["unit"]),
                                    "year": t_res.get("year", year),
                                    "source": t_res.get("source", "CGWB National Compilation"),
                                    "verification": t_res.get("verification", "CGWB-verified"),
                                })
                                missing_recovered = True
                        except Exception as ex:
                            logger.warning(f"Error fetching missing data: {ex}")

            if missing_recovered:
                c_data, d_ev = compute_comparison_matrix(parsed.locations, parsed.metrics, year, evidence_items)
                if c_data:
                    comparison_data = c_data
                if d_ev:
                    evidence_items.extend(d_ev)
                completeness_rep = check_completeness(parsed.locations, parsed.metrics, evidence_items)

        answer = build_template_answer(query, evidence_items)

        # If incomplete, record in limitations
        if not completeness_rep.complete:
            if "limitations" not in answer or not isinstance(answer["limitations"], list):
                answer["limitations"] = []
            for miss in completeness_rep.missing:
                limit_msg = f"Data for {miss} could not be retrieved from official CGWB compilation."
                if limit_msg not in answer["limitations"]:
                    answer["limitations"].append(limit_msg)

        # Populate missing location in numeric breakdown
        for row in answer.get("numeric_breakdown", []):
            if not row.get("location"):
                if parsed.locations:
                    row["location"] = parsed.locations[0].canonical_str()
                elif (hints or {}).get("state"):
                    st = hints["state"]
                    dt = hints.get("district")
                    row["location"] = f"{dt}, {st}" if dt and dt != "State-level (no district)" else st

        ver_res = self.verifier.verify(answer, evidence_items)
        if mode_used == "template_fallback":
            ver_res.fallback_used = True

        evidence_models = [EvidenceItem(**e) for e in evidence_items]
        total_latency = round((time.perf_counter() - start_time) * 1000.0, 2)

        return AgentQueryResponse(
            answer=answer,
            mode_used=mode_used,
            steps=steps,
            evidence=evidence_models,
            citations=list(citations),
            verification=ver_res,
            completeness=completeness_rep,
            comparison_data=comparison_data,
            override_note=parsed.override_note,
            latency_ms=total_latency,
            model="template-engine",
        )
