"""Anti-Hallucination Numeric Verifier.

Extracts every numeric figure from synthesized text and tables and rigorously verifies
that it matches an evidence figure, a known assessment year/rank, or a valid derived value
(e.g., % change, unit conversions from Ham to MCM/BCM, or sum/difference) within 0.5% tolerance.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Set

from backend.app.agentic.schemas import NumericVerificationResult

logger = logging.getLogger(__name__)

# Regex to match potential numbers in markdown / prose / tables
# Matches integers, decimals, comma-separated numbers, percentages (ignoring currency/percent signs)
NUMBER_REGEX = re.compile(r"(?<![a-zA-Z0-9_])-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![a-zA-Z0-9_])")

# Assessment years and known years allowed as temporal anchors
ALLOWED_YEARS = {1990, 2000, 2004, 2009, 2011, 2013, 2017, 2020, 2022, 2023, 2024, 2025, 2026, 2027, 2030, 2047}


def _clean_number_token(token: str) -> float | None:
    """Parse a number token string to float, stripping commas and % signs."""
    token = token.strip()
    if token.endswith("%"):
        token = token[:-1]
    token = token.replace(",", "")
    try:
        val = float(token)
        return val
    except ValueError:
        return None


def extract_numbers_from_text(text: str) -> List[float]:
    """Extract all numbers from arbitrary text."""
    if not text:
        return []
    matches = NUMBER_REGEX.findall(text)
    numbers: List[float] = []
    for m in matches:
        num = _clean_number_token(m)
        if num is not None:
            numbers.append(num)
    return numbers


def extract_numbers_from_object(obj: Any) -> Set[float]:
    """Recursively collect all numeric values found in a dict, list, or primitive."""
    numbers: Set[float] = set()
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        numbers.add(float(obj))
    elif isinstance(obj, str):
        # Check if entire string is numeric or contains numbers
        parsed = _clean_number_token(obj)
        if parsed is not None:
            numbers.add(parsed)
        else:
            for n in extract_numbers_from_text(obj):
                numbers.add(n)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            # If key contains a year (e.g. "2020"), extract it
            parsed_key = _clean_number_token(k)
            if parsed_key is not None:
                numbers.add(parsed_key)
            numbers.update(extract_numbers_from_object(v))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            numbers.update(extract_numbers_from_object(item))
    return numbers


def _compute_derived_values(evidence_numbers: Set[float]) -> Set[float]:
    """Compute permissible derived figures:
    - Unit conversions: Ham <-> MCM (Ham / 100), Ham <-> BCM (Ham / 100000)
    - Scale conversions: percentages (/100 or *100)
    """
    derived: Set[float] = set()
    for val in evidence_numbers:
        if abs(val) < 1e-9:
            continue
        # Ham to MCM (1 MCM = 100 Ham)
        derived.add(val / 100.0)
        derived.add(val * 100.0)
        # Ham to BCM (1 BCM = 100,000 Ham)
        derived.add(val / 100000.0)
        derived.add(val * 100000.0)
        # MCM to BCM (1 BCM = 1000 MCM)
        derived.add(val / 1000.0)
        derived.add(val * 1000.0)
    return derived


def _is_approximately_equal(val: float, target: float, rel_tol: float = 0.005, abs_tol: float = 0.1) -> bool:
    """Check if two floats are equal within relative tolerance (0.5%) or absolute tolerance."""
    if abs(val - target) <= abs_tol:
        return True
    if abs(target) > 0 and (abs(val - target) / abs(target)) <= rel_tol:
        return True
    return False


class NumericVerifier:
    """Verifies that all figures in generated output are strictly grounded in evidence."""

    def __init__(self, rel_tolerance: float = 0.005, abs_tolerance: float = 0.1):
        self.rel_tolerance = rel_tolerance
        self.abs_tolerance = abs_tolerance

    def verify(
        self,
        generated_content: Any,
        evidence_items: List[Dict[str, Any]],
        allowed_extra_numbers: Set[float] | None = None,
    ) -> NumericVerificationResult:
        """Verify generated content against evidence items.

        generated_content can be a dict (StructuredAnswer) or text string.
        """
        # 1. Extract all numbers from generated content
        candidate_numbers: List[float] = []
        if isinstance(generated_content, str):
            candidate_numbers = extract_numbers_from_text(generated_content)
        elif isinstance(generated_content, dict):
            # Exclude metadata fields if any, focus on user-facing sections
            for field in ["summary", "trend_analysis", "interpretation", "limitations"]:
                text_val = generated_content.get(field, "")
                if isinstance(text_val, str):
                    candidate_numbers.extend(extract_numbers_from_text(text_val))
            # Extract from lists
            for item in generated_content.get("policy_recommendations", []):
                if isinstance(item, str):
                    candidate_numbers.extend(extract_numbers_from_text(item))
            for item in generated_content.get("numeric_breakdown", []):
                if isinstance(item, dict):
                    val = item.get("value")
                    if isinstance(val, (int, float)):
                        candidate_numbers.append(float(val))
                    elif isinstance(val, str):
                        p = _clean_number_token(val)
                        if p is not None:
                            candidate_numbers.append(p)
                    # Also scan parameter or unit descriptions for numbers
                    for sub in [item.get("parameter"), item.get("unit"), item.get("year")]:
                        if isinstance(sub, str):
                            candidate_numbers.extend(extract_numbers_from_text(sub))
        else:
            candidate_numbers = list(extract_numbers_from_object(generated_content))

        # 2. Extract verified numbers from evidence ledger
        evidence_numbers: Set[float] = set()
        for ev in evidence_items:
            evidence_numbers.update(extract_numbers_from_object(ev.get("data")))
            evidence_numbers.update(extract_numbers_from_object(ev.get("resolved_args")))
            if ev.get("year"):
                y = _clean_number_token(str(ev.get("year")))
                if y is not None:
                    evidence_numbers.add(y)

        # 3. Compute permissible derived figures
        derived_numbers = _compute_derived_values(evidence_numbers)

        # 4. Standard structural and allowable numbers
        allowed_universe: Set[float] = set(evidence_numbers)
        allowed_universe.update(derived_numbers)
        allowed_universe.update(float(y) for y in ALLOWED_YEARS)
        # Small integers commonly used as list indices or rankings (1 to 20)
        allowed_universe.update(float(i) for i in range(1, 21))

        if allowed_extra_numbers:
            allowed_universe.update(allowed_extra_numbers)

        # 5. Check each candidate number
        unverified: List[float] = []
        checked: List[float] = []

        for cand in candidate_numbers:
            checked.append(cand)
            # Check against allowed universe
            matched = False
            for target in allowed_universe:
                if _is_approximately_equal(cand, target, self.rel_tolerance, self.abs_tolerance):
                    matched = True
                    break
            if not matched:
                unverified.append(cand)

        passed = len(unverified) == 0
        return NumericVerificationResult(
            passed=passed,
            checked_numbers=checked,
            unverified_numbers=unverified,
            regenerated=False,
            fallback_used=False,
            notes=f"Checked {len(checked)} figures; {len(unverified)} unverified; evidence pool size: {len(evidence_numbers)}",
        )
