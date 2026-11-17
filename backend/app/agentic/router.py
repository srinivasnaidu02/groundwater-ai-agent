"""Pure Python keyword execution router. Zero network calls, no LLM."""
from __future__ import annotations

import re
from typing import Optional

COMPLEX_KEYWORDS = [
    "why",
    "how did",
    "how has",
    "explain",
    "trend",
    "recommend",
    "compare",
    "difference",
    "over time",
    "change",
    "cause",
    "reason",
    "factors",
]

YEAR_REGEX = re.compile(r"\b(2020|2022|2023|2024|2025|2026)\b")


def decide_route(query: str, mode: Optional[str] = "auto") -> str:
    """Decide execution path without LLM calls.
    Returns: 'agentic' | 'template'
    """
    if mode == "agentic":
        return "agentic"
    if mode == "template":
        return "template"

    # auto mode heuristics
    q_lower = query.lower()

    # Check for complexity keywords
    for kw in COMPLEX_KEYWORDS:
        if kw in q_lower:
            return "agentic"

    # Check for multiple years (e.g. 2020 and 2025)
    years = YEAR_REGEX.findall(query)
    if len(set(years)) > 1:
        return "agentic"

    # Fast path template
    return "template"
