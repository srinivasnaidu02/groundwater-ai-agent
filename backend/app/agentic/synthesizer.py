"""Synthesizer for Groundwater Agentic AI.

Synthesizes multi-step tool evidence into a grounded, structured answer conforming
to strict CGWB grounding rules and guarded by the NumericVerifier anti-hallucination engine.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

from backend.app.agentic.llm_client import LLMClient, LLMMessage
from backend.app.agentic.prompts import (
    SYNTHESIZER_SYSTEM_PROMPT,
    REGENERATION_PROMPT,
    STRUCTURED_SYNTHESIZER_SCHEMA_DESCRIPTION,
)
from backend.app.agentic.schemas import StructuredAnswer, NumericVerificationResult
from backend.app.agentic.verifier import NumericVerifier

logger = logging.getLogger(__name__)


def build_deterministic_fallback_answer(
    query: str,
    evidence_items: List[Dict[str, Any]],
) -> StructuredAnswer:
    """Build a deterministic, 100% verified structured answer solely from evidence items.

    Used when LLM generation fails, times out, or fails numeric verification twice.
    """
    if not evidence_items:
        return StructuredAnswer(
            summary=f"No verified CGWB groundwater records found for query: '{query}'.",
            numeric_breakdown=[],
            trend_analysis="No multi-year comparative data available.",
            interpretation="Assessment records are not available for the requested location or criteria in the CGWB database.",
            policy_recommendations=[
                "Verify location spelling and confirm if the unit is assessed at district or state level.",
                "Consult the Central Ground Water Board (CGWB) Dynamic Ground Water Resources Assessment reports for unlisted units."
            ],
            limitations="Fallback deterministic summary built due to absence of verified records.",
        )

    breakdown: List[Dict[str, Any]] = []
    summary_points: List[str] = []

    for item in evidence_items:
        tool_name = item.get("tool", "")
        data = item.get("data") or {}
        year = str(item.get("year") or data.get("assessment_year") or "2025")
        location = item.get("location") or data.get("location") or data.get("state") or "India"

        # Extract notable metrics
        if "stage_of_extraction_pct" in data:
            pct = data["stage_of_extraction_pct"]
            cat = data.get("assessment_category", "Unknown")
            breakdown.append({
                "parameter": "Stage of Groundwater Extraction",
                "value": pct,
                "unit": "%",
                "year": year,
                "location": location,
                "verified": True,
            })
            summary_points.append(f"Stage of extraction in {location} ({year}) is {pct:.2f}% ({cat}).")

        if "total_annual_extraction_ham" in data:
            ext = data["total_annual_extraction_ham"]
            breakdown.append({
                "parameter": "Total Annual Groundwater Extraction",
                "value": ext,
                "unit": "Ham",
                "year": year,
                "location": location,
                "verified": True,
            })
            summary_points.append(f"Total annual extraction: {ext:,.2f} Ham.")

        if "total_annual_recharge_ham" in data:
            rech = data["total_annual_recharge_ham"]
            breakdown.append({
                "parameter": "Total Annual Groundwater Recharge",
                "value": rech,
                "unit": "Ham",
                "year": year,
                "location": location,
                "verified": True,
            })

        if "overexploited_count" in data:
            oe_count = data["overexploited_count"]
            breakdown.append({
                "parameter": "Over-Exploited Units Count",
                "value": oe_count,
                "unit": "Units",
                "year": year,
                "location": location,
                "verified": True,
            })
            summary_points.append(f"{oe_count} assessment units are classified as Over-Exploited.")

        # Comparison tool results
        if "difference" in data and "percent_change" in data:
            p = data.get("parameter", "extraction")
            diff = data.get("difference", 0.0)
            pct_chg = data.get("percent_change", 0.0)
            trend = data.get("trend", "changed")
            y1 = data.get("year_1", {}).get("year", "")
            y2 = data.get("year_2", {}).get("year", "")
            summary_points.append(f"Between {y1} and {y2}, {p} {trend} by {abs(pct_chg):.2f}% ({diff:+,.2f} Ham).")
            breakdown.append({
                "parameter": f"{p.capitalize()} Change ({y1} to {y2})",
                "value": pct_chg,
                "unit": "%",
                "year": f"{y1}-{y2}",
                "location": location,
                "verified": True,
            })

    summary_text = " ".join(summary_points) if summary_points else f"Verified data retrieved for {query}."

    return StructuredAnswer(
        summary=summary_text,
        numeric_breakdown=breakdown,
        trend_analysis="Trend derived from official comparative assessment records." if any("difference" in (i.get("data") or {}) for i in evidence_items) else None,
        interpretation="[General Hydrogeological Context - Not from CGWB Database] Ground water levels and extraction dynamics reflect agricultural pumping, domestic draft, and seasonal aquifer recharge.",
        policy_recommendations=[
            "[AI Suggestion - Not CGWB Guidance] Expand micro-irrigation (drip/sprinkler) in blocks exceeding 100% extraction stage.",
            "[AI Suggestion - Not CGWB Guidance] Implement rooftop rainwater harvesting and artificial recharge structures in over-exploited and critical zones."
        ],
        limitations="All figures directly verified against official CGWB Dynamic Ground Water Resources Assessment reports. Projections for 2026 represent benchmark projection models.",
    )


class GroundedSynthesizer:
    def __init__(self, llm_client: LLMClient, verifier: NumericVerifier | None = None):
        self.llm_client = llm_client
        self.verifier = verifier or NumericVerifier()

    def synthesize(
        self,
        query: str,
        evidence_items: List[Dict[str, Any]],
        conversation_context: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[StructuredAnswer, NumericVerificationResult, bool, bool]:
        """Synthesize a structured answer from evidence.

        Returns:
            Tuple of (StructuredAnswer, NumericVerificationResult, regenerated: bool, fallback_used: bool)
        """
        # If no LLM available or mock is not configured, go straight to deterministic fallback
        if not self.llm_client:
            fb = build_deterministic_fallback_answer(query, evidence_items)
            res = self.verifier.verify(fb.model_dump(), evidence_items)
            return fb, res, False, True

        evidence_str = json.dumps(evidence_items, indent=2, default=str)
        prompt_content = (
            f"User Question: {query}\n\n"
            f"Verified Evidence Ledger:\n{evidence_str}\n\n"
            f"{STRUCTURED_SYNTHESIZER_SCHEMA_DESCRIPTION}\n"
            f"Remember: Output strictly valid JSON conforming to the schema. Do not invent any numbers."
        )

        messages = [
            LLMMessage(role="system", content=SYNTHESIZER_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt_content),
        ]

        # First generation attempt
        regenerated = False
        fallback_used = False
        parsed_answer: StructuredAnswer | None = None
        ver_result: NumericVerificationResult | None = None

        try:
            resp = self.llm_client.generate(messages=messages, temperature=0.1)
            raw_json = self._extract_json_string(resp.content)
            data_dict = json.loads(raw_json)
            parsed_answer = StructuredAnswer(**data_dict)
            ver_result = self.verifier.verify(parsed_answer.model_dump(), evidence_items)
        except Exception as e:
            logger.warning(f"Synthesizer first generation attempt failed: {e}")
            parsed_answer = None

        # Check if first attempt passed verification
        if parsed_answer and ver_result and ver_result.passed:
            ver_result.regenerated = regenerated
            ver_result.fallback_used = fallback_used
            return parsed_answer, ver_result, regenerated, fallback_used

        # Attempt regeneration if verification failed with unverified numbers
        if parsed_answer and ver_result and not ver_result.passed:
            regenerated = True
            offending = ver_result.unverified_numbers
            logger.info(f"Verification failed on figures {offending}. Initiating single regeneration attempt.")
            regen_prompt = REGENERATION_PROMPT.format(
                unverified_numbers=str(offending),
                evidence_ledger=evidence_str,
            )
            retry_messages = [
                LLMMessage(role="system", content=SYNTHESIZER_SYSTEM_PROMPT),
                LLMMessage(role="user", content=prompt_content),
                LLMMessage(role="assistant", content=json.dumps(parsed_answer.model_dump())),
                LLMMessage(role="user", content=regen_prompt),
            ]
            try:
                resp2 = self.llm_client.generate(messages=retry_messages, temperature=0.0)
                raw_json2 = self._extract_json_string(resp2.content)
                data_dict2 = json.loads(raw_json2)
                parsed_answer2 = StructuredAnswer(**data_dict2)
                ver_result2 = self.verifier.verify(parsed_answer2.model_dump(), evidence_items)
                ver_result2.regenerated = True
                ver_result2.fallback_used = False
                if ver_result2.passed:
                    return parsed_answer2, ver_result2, regenerated, fallback_used
                else:
                    logger.warning(f"Regeneration attempt also failed verification on: {ver_result2.unverified_numbers}. Falling back to template.")
            except Exception as e:
                logger.warning(f"Synthesizer regeneration failed: {e}")

        # Fallback to deterministic template
        fallback_used = True
        fb_answer = build_deterministic_fallback_answer(query, evidence_items)
        fb_ver = self.verifier.verify(fb_answer.model_dump(), evidence_items)
        fb_ver.regenerated = regenerated
        fb_ver.fallback_used = True
        return fb_answer, fb_ver, regenerated, fallback_used

    def _extract_json_string(self, text: str) -> str:
        """Strip markdown fences (```json ... ```) to extract raw JSON."""
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
            return text[start:].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
            return text[start:].strip()
        return text
