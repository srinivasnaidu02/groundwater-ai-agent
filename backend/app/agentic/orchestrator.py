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
    EvidenceItem,
    NumericVerification,
)
from backend.app.agentic.synthesizer import GroundedSynthesizer, build_template_answer
from backend.app.agentic.tools import ToolRegistry, default_tool_registry, ALIAS_MAP, STATE_ALIASES, ALL_STATES
from backend.app.agentic.verifier import NumericVerifier
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
                    "year": res.get("year", "2025"),
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

        # SYNTHESIS & VERIFICATION
        answer = await self.synthesizer.synthesize(query=query, evidence_items=evidence_items)
        if partial_evidence:
            answer["partial"] = True

        ver_res = self.verifier.verify(answer, evidence_items)

        # Regeneration attempt if unverified numbers detected
        if not ver_res.passed:
            import re
            unverified_nums = [n for n in ver_res.checked_numbers if n not in self.verifier.verify(answer, evidence_items).checked_numbers]
            logger.info(f"Verification failed on numbers. Attempting single regeneration.")
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
        q_year, q_state, q_dist = _extract_query_overrides(query)

        # Question wins if explicit, otherwise fall back to hints/defaults
        state = q_state or (hints or {}).get("state") or "Punjab"
        district = q_dist or (hints or {}).get("district")
        if district == "State-level (no district)":
            district = None
        year = str(q_year or (hints or {}).get("year") or "2025")

        evidence_items = []
        citations = set()
        steps = []

        # Determine tool to call
        tool_name = "get_stage_of_extraction"
        tool_args: Dict[str, Any] = {"state": state or "Punjab", "assessment_year": year}
        if district:
            tool_args["district"] = district

        if "recharge" in query.lower():
            tool_name = "get_groundwater_recharge"
        elif "extraction" in query.lower():
            tool_name = "get_groundwater_extraction"
        elif "overexploited" in query.lower() or "over-exploited" in query.lower():
            tool_name = "get_overexploited_units"
            tool_args = {"state": state or "Punjab", "assessment_year": year}

        res = self.tool_registry.run(tool_name, **tool_args)
        dur = round((time.perf_counter() - t0) * 1000.0, 2)

        steps.append(
            AgentStep(
                step_number=1,
                thought="Template execution path: running tool",
                tool_called=tool_name,
                arguments=tool_args,
                result_summary="Template tool execution completed",
                latency_ms=dur,
            )
        )

        ev_entry = {
            "tool_name": tool_name,
            "arguments": tool_args,
            "result": res,
            "unit": res.get("unit", "Ham"),
            "year": res.get("year", year),
            "source": res.get("source", "CGWB National Compilation"),
            "verification": res.get("verification", "CGWB-verified"),
        }
        evidence_items.append(ev_entry)
        if res.get("source"):
            citations.add(res["source"])

        answer = build_template_answer(query, evidence_items)
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
            latency_ms=total_latency,
            model="template-engine",
        )
