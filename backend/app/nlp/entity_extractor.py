"""
NLP Entity Extractor — extracts state, district, block, assessment year,
parameter type and aggregation level from a natural-language question.
"""
import re
from typing import Dict, Optional, List


# ──────────────────────── Geography Dictionaries ─────────────────────────────

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

STATE_ALIASES = {
    "up": "Uttar Pradesh",
    "u.p.": "Uttar Pradesh",
    "u.p": "Uttar Pradesh",
    "mp": "Madhya Pradesh",
    "m.p.": "Madhya Pradesh",
    "wb": "West Bengal",
    "ap": "Andhra Pradesh",
    "hp": "Himachal Pradesh",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "uk": "Uttarakhand",
    "uttarakhand": "Uttarakhand",
    "jharkhand": "Jharkhand",
    "chattisgarh": "Chhattisgarh",
    "chhattisgarh": "Chhattisgarh",
    "tamilnadu": "Tamil Nadu",
    "tamil_nadu": "Tamil Nadu",
}

# Districts grouped by state (from our dataset)
STATE_DISTRICTS: Dict[str, List[str]] = {
    "Bihar": [
        "Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga", "Nalanda",
        "Vaishali", "Saran", "Sitamarhi", "Madhubani", "Samastipur", "Begusarai",
        "Rohtas", "Bhojpur", "Aurangabad", "Nawada", "Jehanabad", "Arwal",
        "Kaimur", "Buxar", "Gopalganj", "Siwan", "Motihari", "East Champaran",
        "Bettiah", "West Champaran", "Sheohar", "Supaul", "Araria", "Kishanganj",
        "Purnia", "Katihar", "Khagaria", "Madhepura", "Saharsa", "Munger",
        "Lakhisarai", "Sheikhpura", "Jamui", "Banka",
    ],
    "Uttar Pradesh": [
        "Lucknow", "Agra", "Varanasi", "Allahabad", "Prayagraj", "Kanpur",
        "Meerut", "Bareilly", "Aligarh", "Muzaffarnagar", "Mathura", "Jhansi",
        "Mau", "Deoria", "Gorakhpur",
    ],
    "Rajasthan": ["Jaipur", "Jodhpur", "Bikaner", "Udaipur", "Ajmer", "Kota", "Alwar", "Bharatpur"],
    "Maharashtra": ["Mumbai", "Pune", "Nashik", "Aurangabad", "Nagpur", "Latur", "Solapur"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Kutch", "Gandhinagar"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Sagar", "Rewa", "Ujjain"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tirunelveli", "Salem"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli-Dharwad", "Belgaum", "Gulbarga"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati"],
    "Telangana": ["Hyderabad", "Warangal", "Khammam"],
    "West Bengal": ["Kolkata", "Howrah", "Asansol", "Murshidabad"],
    "Punjab": ["Amritsar", "Ludhiana", "Jalandhar", "Patiala", "Bathinda"],
    "Haryana": ["Gurugram", "Faridabad", "Rohtak", "Karnal", "Panipat"],
    "Delhi": ["South Delhi", "North Delhi", "East Delhi", "West Delhi"],
    "Jharkhand": ["Ranchi", "Dhanbad", "Jamshedpur", "East Singhbhum"],
    "Odisha": ["Bhubaneswar", "Khurda", "Cuttack"],
    "Himachal Pradesh": ["Shimla", "Kangra"],
    "Uttarakhand": ["Dehradun", "Haridwar"],
    "Assam": ["Guwahati", "Kamrup", "Dibrugarh"],
    "Kerala": ["Thiruvananthapuram", "Kochi", "Ernakulam"],
    "Goa": ["North Goa", "South Goa"],
    "Chhattisgarh": ["Raipur", "Bilaspur"],
    "Jammu and Kashmir": ["Jammu", "Srinagar"],
    "Ladakh": ["Leh"],
}

# Build a flat district→state mapping for reverse lookup
DISTRICT_TO_STATE: Dict[str, str] = {}
for state, dists in STATE_DISTRICTS.items():
    for d in dists:
        DISTRICT_TO_STATE[d.lower()] = state

PARAMETER_KEYWORDS = {
    "recharge": ["recharge", "recharg"],
    "extraction": ["extract", "utiliz", "how much groundwater", "groundwater use", "groundwater used"],
    "extractable": ["extractable", "net availability", "available for future", "future availability"],
    "stage": ["stage of extraction", "stage", "percent extract"],
    "category": ["category", "categor", "classif", "safe", "semi-critical", "critical", "over-exploit"],
    "level": ["level", "depth", "water table", "well depth"],
}

YEAR_PATTERN = re.compile(r'\b(20\d{2})\b')


def extract_entities(question: str) -> Dict:
    """
    Extract: state, district, block, assessment_year, parameter, aggregation_level.
    Returns a dict with all extracted fields (None if not found).
    """
    q = question.strip()
    q_lower = q.lower()

    entities: Dict = {
        "state": None,
        "district": None,
        "block": None,
        "assessment_year": None,
        "parameter": None,
        "aggregation": "district",
        "comparison_locations": [],
    }

    # ── Year ──────────────────────────────────────────────────────────────────
    year_matches = YEAR_PATTERN.findall(q)
    if year_matches:
        entities["assessment_year"] = year_matches[0]
        if len(year_matches) >= 2:
            entities["year1"] = year_matches[0]
            entities["year2"] = year_matches[1]
    else:
        entities["year1"] = None
        entities["year2"] = None

    # ── State ─────────────────────────────────────────────────────────────────
    for state in sorted(STATES, key=len, reverse=True):
        if re.search(r'\b' + re.escape(state) + r'\b', q, re.IGNORECASE):
            entities["state"] = state
            break
    if not entities["state"]:
        for alias, canonical in STATE_ALIASES.items():
            if re.search(r'\b' + re.escape(alias) + r'\b', q_lower):
                entities["state"] = canonical
                break

    # ── District ──────────────────────────────────────────────────────────────
    # Build combined district list sorted by length desc to avoid partial matches
    all_districts = sorted(
        [(d, s) for s, dlist in STATE_DISTRICTS.items() for d in dlist],
        key=lambda x: len(x[0]), reverse=True
    )
    for dist, state in all_districts:
        if re.search(r'\b' + re.escape(dist) + r'\b', q, re.IGNORECASE):
            entities["district"] = dist
            if not entities["state"]:
                entities["state"] = state
            break

    # ── Aggregation ───────────────────────────────────────────────────────────
    if entities["district"]:
        entities["aggregation"] = "district"
    elif entities["state"]:
        entities["aggregation"] = "state"
    else:
        entities["aggregation"] = "national"

    # ── Parameter ─────────────────────────────────────────────────────────────
    for param, keywords in PARAMETER_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            entities["parameter"] = param
            break

    # ── Comparison locations ──────────────────────────────────────────────────
    if "compare" in q_lower or " and " in q_lower or " vs " in q_lower:
        found_dists = []
        for dist, state in all_districts:
            if re.search(r'\b' + re.escape(dist) + r'\b', q, re.IGNORECASE):
                found_dists.append({"district": dist, "state": state})
        entities["comparison_locations"] = found_dists[:2]

    return entities

