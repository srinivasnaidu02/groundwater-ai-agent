"""
Dynamic Geographical Resolution Engine.
Resolves state and district entities, alternative spellings, aliases,
and common geographic variations across India.
"""
import re
from typing import Dict, Optional, Tuple, List
from sqlalchemy.orm import Session
from ..database.models import State, District, GeographicMaster

# Canonical alias mapping for rapid lookup
ALIAS_MAP: Dict[str, Tuple[str, str]] = {
    # District Alias -> (Canonical District, State)
    "patliputra": ("Patna", "Bihar"),
    "patna": ("Patna", "Bihar"),
    "bodhgaya": ("Gaya", "Bihar"),
    "bodh gaya": ("Gaya", "Bihar"),
    "gaya": ("Gaya", "Bihar"),
    "muzaffar pur": ("Muzaffarpur", "Bihar"),
    "muzaffarpur": ("Muzaffarpur", "Bihar"),
    "ludhiana": ("Ludhiana", "Punjab"),
    "jullundur": ("Jalandhar", "Punjab"),
    "jalandhar": ("Jalandhar", "Punjab"),
    "ambarsar": ("Amritsar", "Punjab"),
    "amritsar": ("Amritsar", "Punjab"),
    "hissar": ("Hisar", "Haryana"),
    "hisar": ("Hisar", "Haryana"),
    "gurgaon": ("Gurugram", "Haryana"),
    "gurugram": ("Gurugram", "Haryana"),
    "pink city": ("Jaipur", "Rajasthan"),
    "jaipur": ("Jaipur", "Rajasthan"),
    "jodhpur": ("Jodhpur", "Rajasthan"),
    "bikaner": ("Bikaner", "Rajasthan"),
    "poona": ("Pune", "Maharashtra"),
    "pune": ("Pune", "Maharashtra"),
    "nasik": ("Nashik", "Maharashtra"),
    "nashik": ("Nashik", "Maharashtra"),
    "bombay": ("Mumbai", "Maharashtra"),
    "mumbai": ("Mumbai", "Maharashtra"),
    "lucknow": ("Lucknow", "Uttar Pradesh"),
    "cawnpore": ("Kanpur", "Uttar Pradesh"),
    "kanpur": ("Kanpur", "Uttar Pradesh"),
    "allahabad": ("Allahabad (Prayagraj)", "Uttar Pradesh"),
    "prayagraj": ("Allahabad (Prayagraj)", "Uttar Pradesh"),
    "banaras": ("Varanasi", "Uttar Pradesh"),
    "kashi": ("Varanasi", "Uttar Pradesh"),
    "varanasi": ("Varanasi", "Uttar Pradesh"),
    "bengaluru": ("Bangalore (Urban)", "Karnataka"),
    "bangalore": ("Bangalore (Urban)", "Karnataka"),
    "mysuru": ("Mysore", "Karnataka"),
    "mysore": ("Mysore", "Karnataka"),
    "madras": ("Chennai", "Tamil Nadu"),
    "chennai": ("Chennai", "Tamil Nadu"),
    "kovai": ("Coimbatore", "Tamil Nadu"),
    "coimbatore": ("Coimbatore", "Tamil Nadu"),
    "amdavad": ("Ahmedabad", "Gujarat"),
    "ahmedabad": ("Ahmedabad", "Gujarat"),
    "surat": ("Surat", "Gujarat"),
    "calcutta": ("Kolkata", "West Bengal"),
    "kolkata": ("Kolkata", "West Bengal"),
    "delhi": ("South Delhi", "Delhi"),
    "new delhi": ("South Delhi", "Delhi"),
}

STATE_ALIASES: Dict[str, str] = {
    "up": "Uttar Pradesh",
    "u.p.": "Uttar Pradesh",
    "mp": "Madhya Pradesh",
    "m.p.": "Madhya Pradesh",
    "wb": "West Bengal",
    "ap": "Andhra Pradesh",
    "hp": "Himachal Pradesh",
    "j&k": "Jammu and Kashmir",
    "jk": "Jammu and Kashmir",
    "uk": "Uttarakhand",
    "tn": "Tamil Nadu",
    "pb": "Punjab",
    "hr": "Haryana",
    "rj": "Rajasthan",
    "mh": "Maharashtra",
    "gj": "Gujarat",
    "br": "Bihar",
    "ka": "Karnataka",
    "ts": "Telangana",
    "tg": "Telangana",
    "or": "Odisha",
    "od": "Odisha",
}

ALL_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
    "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
]


def resolve_geography(text: str, db: Optional[Session] = None) -> Dict:
    """
    Dynamically resolve state and district from text, matching
    canonical names, database records, and common aliases.
    """
    text_lower = text.lower()
    detected_state = None
    detected_district = None

    # Check for direct district aliases first
    for alias, (canonical_dist, canonical_state) in ALIAS_MAP.items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_lower):
            detected_district = canonical_dist
            detected_state = canonical_state
            break

    # If state not resolved yet, check direct state names
    if not detected_state:
        for st_name in ALL_STATES:
            if re.search(r"\b" + re.escape(st_name.lower()) + r"\b", text_lower):
                detected_state = st_name
                break

    # If state not resolved yet, check state aliases
    if not detected_state:
        for alias, canonical_state in STATE_ALIASES.items():
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, text_lower):
                detected_state = canonical_state
                break

    # Check database GeographicMaster if db provided and not fully resolved
    if db and (not detected_state or not detected_district):
        try:
            masters = db.query(GeographicMaster).all()
            for gm in masters:
                aliases = [gm.canonical_name.lower()]
                if gm.aliases:
                    aliases.extend([a.strip().lower() for a in gm.aliases.split(",")])
                for al in aliases:
                    if al and re.search(r"\b" + re.escape(al) + r"\b", text_lower):
                        detected_district = gm.canonical_name
                        detected_state = gm.state_name
                        break
                if detected_district:
                    break
        except Exception:
            pass

    # Check State entities
    if not detected_state and db:
        try:
            states = db.query(State).all()
            for st in states:
                if re.search(r"\b" + re.escape(st.name.lower()) + r"\b", text_lower):
                    detected_state = st.name
                    break
        except Exception:
            pass

    return {
        "state": detected_state,
        "district": detected_district,
    }

