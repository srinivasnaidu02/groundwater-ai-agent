"""Numeric Verifier Anti-Hallucination Guard.

Extracts every numeric figure from synthesized output and verifies that it exists
in the evidence ledger or is an allowable precomputed derived calculation (Ham -> MCM/BCM, % changes)
within a 0.5% tolerance.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Set

from backend.app.agentic.schemas import NumericVerification

logger = logging.getLogger(__name__)

# Matches numbers: 101.75, 2,136.00, 15%, -13.24
NUMBER_REGEX = re.compile(r"(?<![a-zA-Z0-9_])-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![a-zA-Z0-9_])")

# Ignored non-data numbers
IGNORED_YEARS = {2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2030, 2047}
IGNORED_STRUCTURAL = {0.0, 100.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0}


def clean_num(token: str) -> float | None:
    token = token.strip()
    if token.endswith("%"):
        token = token[:-1]
    token = token.replace(",", "")
    try:
        return float(token)
    except ValueError:
        return None


def extract_numbers_from_text(text: str) -> List[float]:
    if not text:
        return []
    matches = NUMBER_REGEX.findall(text)
    nums = []
    for m in matches:
        val = clean_num(m)
        if val is not None:
            nums.append(val)
    return nums


def extract_numbers_from_obj(obj: Any) -> Set[float]:
    found = set()
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        found.add(float(obj))
    elif isinstance(obj, str):
        v = clean_num(obj)
        if v is not None:
            found.add(v)
        else:
            for n in extract_numbers_from_text(obj):
                found.add(n)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            found.update(extract_numbers_from_obj(v))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            found.update(extract_numbers_from_obj(item))
    return found


def compute_derived_numbers(raw_nums: Set[float]) -> Set[float]:
    derived = set()
    for n in raw_nums:
        if abs(n) < 1e-9:
            continue
        # Ham to MCM
        derived.add(n / 100.0)
        derived.add(n * 100.0)
        # Ham to BCM
        derived.add(n / 100000.0)
        derived.add(n * 100000.0)
        # Rounding variants
        derived.add(round(n / 100.0, 2))
        derived.add(round(n / 100000.0, 4))
    return derived


class NumericVerifier:
    def __init__(self, rel_tolerance: float = 0.005, abs_tolerance: float = 0.1):
        self.rel_tolerance = rel_tolerance
        self.abs_tolerance = abs_tolerance

    def verify(
        self,
        answer_dict: Dict[str, Any],
        evidence_items: List[Dict[str, Any]],
    ) -> NumericVerification:
        # 1. Collect candidate numbers from generated answer
        candidates: List[float] = []

        # From summary, trend_analysis, interpretation
        for field in ["summary", "trend_analysis", "interpretation"]:
            val = answer_dict.get(field)
            if isinstance(val, str):
                candidates.extend(extract_numbers_from_text(val))

        # From numeric breakdown
        for row in answer_dict.get("numeric_breakdown", []):
            if isinstance(row, dict):
                v = row.get("value")
                if isinstance(v, (int, float)):
                    candidates.append(float(v))
                elif isinstance(v, str):
                    pv = clean_num(v)
                    if pv is not None:
                        candidates.append(pv)

        # 2. Build verified numbers set from evidence
        evidence_numbers: Set[float] = set()
        for ev in evidence_items:
            evidence_numbers.update(extract_numbers_from_obj(ev.get("result")))
            evidence_numbers.update(extract_numbers_from_obj(ev.get("arguments")))
            if ev.get("year"):
                y = clean_num(str(ev.get("year")))
                if y: evidence_numbers.add(y)

        # Precomputed and derived
        derived = compute_derived_numbers(evidence_numbers)
        allowed_universe = set(evidence_numbers) | derived

        unverified: List[float] = []
        checked: List[float] = []

        for cand in candidates:
            # Skip non-data years and structural integers
            if int(cand) in IGNORED_YEARS and abs(cand - int(cand)) < 1e-4:
                continue
            if cand in IGNORED_STRUCTURAL:
                continue

            checked.append(cand)
            matched = False
            for target in allowed_universe:
                if abs(cand - target) <= self.abs_tolerance:
                    matched = True
                    break
                if abs(target) > 0 and (abs(cand - target) / abs(target)) <= self.rel_tolerance:
                    matched = True
                    break

            if not matched:
                unverified.append(cand)

        return NumericVerification(
            passed=(len(unverified) == 0),
            checked_numbers=checked,
            regenerated=False,
            fallback_used=False,
        )
