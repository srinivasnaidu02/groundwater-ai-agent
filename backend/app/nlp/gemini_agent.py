"""
Gemini NLP Agent — Uses Gemini Flash for intelligent intent understanding,
entity parsing, and conversational response generation when an API key is available.
Includes seamless offline fallback to Rule-Based and Scikit-Learn ML classifiers.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

GEMINI_SYSTEM_PROMPT = """You are an NLP parser for an official Indian Groundwater Database Query Agent (IN-GRES / CGWB).
Your task is to parse a user's natural language question into structured JSON.

Allowed Intents:
- get_assessment_years (e.g. what assessment years are available)
- get_state_list (e.g. list all states covered)
- get_country_summary (e.g. all India groundwater stats)
- get_state_summary (e.g. groundwater situation in Bihar)
- get_district_summary (e.g. full groundwater data for Patna)
- get_groundwater_recharge (e.g. recharge in Patna)
- get_extractable_groundwater (e.g. extractable resource in Gaya)
- get_groundwater_extraction (e.g. groundwater extraction in Patna in 2022)
- get_stage_of_extraction (e.g. stage of extraction in Jalandhar)
- get_assessment_category (e.g. what category is Gaya district)
- get_overexploited_units (e.g. which districts in Bihar are over-exploited)
- compare_locations (e.g. compare extraction between Patna and Gaya)
- compare_assessment_years (e.g. compare extraction in Patna between 2020 and 2026)
- get_districts_in_state (e.g. which districts in Punjab have data)
- get_historical_groundwater_data (e.g. show historical trend of extraction in Patna)
- get_groundwater_level (e.g. groundwater depth/well level)
- domain_explanation (e.g. what is an aquifer, explain depletion, explain over-exploited)
- general_greeting (e.g. hi, hello, good morning)

Output strictly valid JSON with this exact schema:
{
  "intent": "<one of the allowed intents above>",
  "confidence": <float between 0.0 and 1.0>,
  "state": "<State name if mentioned or inferred, else null>",
  "district": "<District name if mentioned, else null>",
  "assessment_year": "<4-digit year e.g. 2020, 2022, 2023, 2024, 2025, 2026 if mentioned, else null>",
  "parameter": "<recharge | extraction | extractable | stage | category, else null>",
  "requires_clarification": <true | false>,
  "clarification_question": "<question string if ambiguous, else null>"
}
"""


class GeminiNLPAgent:
    """Intelligent parsing and reasoning agent backed by Gemini."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = None
        self._initialized = False

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                self._initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize Gemini model: {e}")

    @property
    def is_available(self) -> bool:
        return self._initialized and self.model is not None

    def parse_query(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Parse natural-language query using Gemini structured output.
        Returns None if unavailable or on error, prompting offline fallback.
        """
        if not self.is_available:
            return None

        try:
            prompt = f"{GEMINI_SYSTEM_PROMPT}\n\nUser Question: {question}\n\nStructured JSON:"
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            parsed["model"] = "gemini-2.5-flash"
            return parsed
        except Exception as e:
            logger.warning(f"Gemini API parse call failed: {e}")
            return None


# Singleton instance
_gemini_agent: Optional[GeminiNLPAgent] = None


def get_gemini_agent() -> GeminiNLPAgent:
    global _gemini_agent
    if _gemini_agent is None:
        _gemini_agent = GeminiNLPAgent()
    return _gemini_agent

