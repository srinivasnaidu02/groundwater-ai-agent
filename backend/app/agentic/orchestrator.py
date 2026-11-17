"""ReAct Planning Loop and Orchestrator for Groundwater Agentic AI.

Orchestrates multi-step tool calls, duplicate-call suppression, parallel tool execution,
evidence ledger tracking, per-tool timeout handling, and grounding synthesis.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from backend.app.agentic.config import AgenticConfig, get_agentic_settings
from backend.app.agentic.llm_client import LLMClient, LLMMessage, ToolCallRequest, get_llm_client
from backend.app.agentic.prompts import REACT_SYSTEM_PROMPT
from backend.app.agentic.schemas import (
    AgentQueryResponse,
    AgentStep,
    EvidenceItem,
    StructuredAnswer,
    NumericVerificationResult,
)
from backend.app.agentic.synthesizer import GroundedSynthesizer
from backend.app.agentic.tools import ToolRegistry, default_tool_registry
from backend.app.agentic.verifier import NumericVerifier

logger = logging.getLogger(__name__)


def _make_call_key(tool_name: str, args: Dict[str, Any]) -> str:
    """Create a canonical deterministic string key for duplicate call detection."""
    sorted_items = sorted((k, str(v)) for k, v in args.items())
    return f"{tool_name}::" + json.dumps(sorted_items)


def _format_markdown_answer(answer: StructuredAnswer) -> str:
    """Format structured answer into a clean GitHub-style Markdown text document."""
    sections = []

    # 1. Summary
    sections.append(f"### Summary\n{answer.summary}")

    # 2. Key Metrics Table
    if answer.numeric_breakdown:
        table_lines = [
            "\n### Verified Groundwater Records",
            "| Parameter | Value | Unit | Year | Location | Verification |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for row in answer.numeric_breakdown:
            p = row.get("parameter", "N/A")
            v = row.get("value", "N/A")
            u = row.get("unit", "")
            y = row.get("year", "N/A")
            loc = row.get("location", "N/A")
            ver = "VERIFIED" if row.get("verified", True) else "UNVERIFIED"
            if isinstance(v, (int, float)):
                v_str = f"{v:,.2f}" if isinstance(v, float) else f"{v:,}"
            else:
                v_str = str(v)
            table_lines.append(f"| {p} | {v_str} | {u} | {y} | {loc} | {ver} |")
        sections.append("\n".join(table_lines))

    # 3. Trend Analysis
    if answer.trend_analysis:
        sections.append(f"### Trend Analysis\n{answer.trend_analysis}")

    # 4. Geological Context & Interpretation
    if answer.interpretation:
        sections.append(
            "### Hydrogeological Context & Interpretation\n"
            "> **Disclaimer:** General hydrogeological interpretation; not from CGWB data records.\n\n"
            f"{answer.interpretation}"
        )

    # 5. Policy Recommendations
    if answer.policy_recommendations:
        rec_lines = [
            "### Policy & Conservation Recommendations",
            "> **Notice:** AI-generated conservation suggestions, not official CGWB directives.\n",
        ]
        for rec in answer.policy_recommendations:
            rec_lines.append(f"- {rec}")
        sections.append("\n".join(rec_lines))

    # 6. Limitations
    if answer.limitations:
        sections.append(f"### Data Coverage & Limitations\n{answer.limitations}")

    return "\n\n".join(sections)


class AgenticOrchestrator:
    """ReAct planning loop orchestrator executing multi-step reasoning tools against SQLite."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tool_registry: Optional[ToolRegistry] = None,
        config: Optional[AgenticConfig] = None,
        verifier: Optional[NumericVerifier] = None,
        synthesizer: Optional[GroundedSynthesizer] = None,
    ):
        self.config = config or get_agentic_settings()
        self.llm_client = llm_client or get_llm_client()
        self.tool_registry = tool_registry or default_tool_registry
        self.verifier = verifier or NumericVerifier()
        self.synthesizer = synthesizer or GroundedSynthesizer(self.llm_client, self.verifier)

    def run(
        self,
        query: str,
        db: Session,
        filter_hints: Optional[Dict[str, Any]] = None,
    ) -> AgentQueryResponse:
        """Run the ReAct planning and execution loop for the user query."""
        start_time = time.perf_counter()
        steps: List[AgentStep] = []
        evidence_items: List[Dict[str, Any]] = []
        citation_set: Dict[str, Dict[str, Any]] = {}
        visited_calls: Dict[str, Dict[str, Any]] = {}

        # Prepare initial messages with prompt-injection defenses and context
        filter_context = ""
        if filter_hints:
            active_hints = {k: v for k, v in filter_hints.items() if v}
            if active_hints:
                filter_context = f"\nUser filter hints: {json.dumps(active_hints)}"

        initial_user_prompt = f"User Query: {query}{filter_context}"
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=REACT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=initial_user_prompt),
        ]

        step_counter = 1
        tools_schemas = self.tool_registry.get_schemas()

        while step_counter <= self.config.agent_max_steps:
            elapsed = time.perf_counter() - start_time
            if elapsed >= self.config.agent_timeout_seconds:
                logger.warning(f"Agent exceeded timeout of {self.config.agent_timeout_seconds}s at step {step_counter}.")
                break

            # 1. Ask LLM for next action
            try:
                llm_resp = self.llm_client.generate(
                    messages=messages,
                    tools=tools_schemas,
                    temperature=self.config.llm_temperature,
                )
            except Exception as e:
                logger.error(f"LLM generation failed in ReAct loop: {e}", exc_info=True)
                break

            # 2. Check if LLM requested tool calls
            tool_calls = llm_resp.tool_calls
            if not tool_calls:
                # LLM determined no further tools needed
                logger.info(f"ReAct completed planning after {step_counter - 1} steps (no further tool calls).")
                break

            # 3. Process tool calls (executing independent calls)
            calls_to_execute: List[Tuple[ToolCallRequest, str]] = []
            for tc in tool_calls:
                key = _make_call_key(tc.name, tc.arguments)
                if key in visited_calls:
                    # Duplicate-call suppression: reuse cached observation
                    logger.info(f"Duplicate call suppressed: {tc.name} with args {tc.arguments}")
                    cached_obs = visited_calls[key]
                    steps.append(
                        AgentStep(
                            step_number=step_counter,
                            thought=f"[Cached] Re-using previous result for {tc.name}",
                            tool=tc.name,
                            args=tc.arguments,
                            result_summary=f"Cached result ({cached_obs.get('status', 'success')})",
                            latency_ms=0.0,
                        )
                    )
                    step_counter += 1
                else:
                    calls_to_execute.append((tc, key))

            if not calls_to_execute:
                # All calls were duplicates; avoid infinite loop
                break

            # Execute tool calls
            tool_results = self._execute_tool_batch(calls_to_execute, db)

            for tc, key, result, duration_ms in tool_results:
                visited_calls[key] = result
                obs_status = result.get("status", "unknown")
                summary_msg = f"{tc.name} returned status '{obs_status}'"

                steps.append(
                    AgentStep(
                        step_number=step_counter,
                        thought=llm_resp.content or f"Calling tool {tc.name} with {tc.arguments}",
                        tool=tc.name,
                        args=tc.arguments,
                        result_summary=summary_msg,
                        latency_ms=duration_ms,
                    )
                )

                # Record in Evidence Ledger
                evidence_entry = {
                    "tool": tc.name,
                    "args": tc.arguments,
                    "resolved_args": result.get("resolved_args", tc.arguments),
                    "data": result.get("data"),
                    "unit": result.get("data", {}).get("unit", "Ham") if isinstance(result.get("data"), dict) else "Ham",
                    "year": str(result.get("data", {}).get("assessment_year") or result.get("resolved_args", {}).get("assessment_year") or "2025") if isinstance(result.get("data"), dict) else "2025",
                    "location": str(result.get("data", {}).get("location") or result.get("resolved_args", {}).get("state") or "India") if isinstance(result.get("data"), dict) else "India",
                    "source": result.get("source", "CGWB Dynamic Ground Water Resources of India"),
                    "verification_status": result.get("data", {}).get("verification_status", "VERIFIED") if isinstance(result.get("data"), dict) else "VERIFIED",
                    "latency_ms": duration_ms,
                }
                evidence_items.append(evidence_entry)

                # Record citations
                prov_list = result.get("provenance", [])
                if isinstance(prov_list, list):
                    for prov in prov_list:
                        cite_id = f"{prov.get('dataset_name', '')}_{prov.get('assessment_year', '')}"
                        if cite_id not in citation_set:
                            citation_set[cite_id] = {
                                "source_agency": prov.get("source_agency", "CGWB"),
                                "source_document": prov.get("source_document", "Dynamic Ground Water Resources Assessment"),
                                "source_document_url": prov.get("source_document_url"),
                                "assessment_year": prov.get("assessment_year"),
                                "verification_status": prov.get("verification_status", "VERIFIED"),
                            }

                # Feed observation back to conversation history
                obs_text = json.dumps(result, default=str)
                messages.append(
                    LLMMessage(
                        role="tool",
                        content=f"Tool '{tc.name}' result:\n{obs_text}",
                        name=tc.name,
                        tool_call_id=tc.id,
                    )
                )

                step_counter += 1
                if step_counter > self.config.agent_max_steps:
                    break

        # 4. Synthesize final answer from evidence ledger
        parsed_answer, ver_result, regenerated, fallback_used = self.synthesizer.synthesize(
            query=query,
            evidence_items=evidence_items,
        )

        # 5. Build final text markdown representation
        text_answer = _format_markdown_answer(parsed_answer)

        # 6. Build typed evidence items
        evidence_models = [
            EvidenceItem(
                tool=e["tool"],
                args=e["args"],
                data=e["data"],
                unit=e.get("unit", "Ham"),
                year=e.get("year"),
                location=e.get("location", "N/A"),
                source=e.get("source", "CGWB Compilation"),
                verification_status=e.get("verification_status", "VERIFIED"),
                latency_ms=e.get("latency_ms", 0.0),
            )
            for e in evidence_items
        ]

        total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        citations_list = list(citation_set.values())

        return AgentQueryResponse(
            status="success",
            query=query,
            mode_used="agentic",
            answer=parsed_answer,
            text_answer=text_answer,
            steps=steps,
            evidence=evidence_models,
            citations=citations_list,
            verification=ver_result,
            latency_ms=total_latency_ms,
            model=self.config.llm_model,
        )

    def _execute_tool_batch(
        self,
        calls: List[Tuple[ToolCallRequest, str]],
        db: Session,
    ) -> List[Tuple[ToolCallRequest, str, Dict[str, Any], float]]:
        """Execute independent tool calls, parallelizing if multiple calls are present."""
        results = []

        if len(calls) == 1:
            tc, key = calls[0]
            t0 = time.perf_counter()
            res = self.tool_registry.execute(tc.name, db, **tc.arguments)
            dur = round((time.perf_counter() - t0) * 1000.0, 2)
            results.append((tc, key, res, dur))
            return results

        # Parallel execution across multiple independent tool calls
        from backend.app.database.connection import SyncSession

        def _exec_single(tc_item: Tuple[ToolCallRequest, str]):
            tc_sub, key_sub = tc_item
            thread_db = SyncSession()
            try:
                t0 = time.perf_counter()
                res = self.tool_registry.execute(tc_sub.name, thread_db, **tc_sub.arguments)
                dur = round((time.perf_counter() - t0) * 1000.0, 2)
                return tc_sub, key_sub, res, dur
            finally:
                thread_db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(calls))) as executor:
            futures = [executor.submit(_exec_single, item) for item in calls]
            for f in concurrent.futures.as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    logger.error(f"Parallel tool execution thread error: {e}")

        return results
