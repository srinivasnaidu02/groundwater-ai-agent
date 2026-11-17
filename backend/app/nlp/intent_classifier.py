"""
NLP Intent Classifier — Rule-based and semantic patterns.
Classifies natural-language questions into the 8 core application categories:
  1. greeting
  2. general_conversation
  3. groundwater_education
  4. groundwater_database_query
  5. mixed_query
  6. conversational_followup
  7. clarification_required
  8. unsupported_query
Also provides fine-grained database intent identifiers for deterministic retrieval.
"""
import re
from typing import Dict, Any, Optional
from .geo_resolver import resolve_geography


# 1. Pure Greetings (Short, greeting-only tokens without year or data parameters)
GREETING_PATTERN = re.compile(
    r"^(hi|hello|hii+|hey+|heyy+|greetings|good\s+(morning|afternoon|evening)|howdy|namaste|sup|hola)[\s\.,!]*$",
    re.IGNORECASE,
)

# 2. General Conversation / Small Talk / Capabilities / Gratitude
GENERAL_CONVERSATION_PATTERNS = [
    (r"^(how\s+are\s+you|how\s+are\s+you\s+doing|how\'s\s+it\s+going)[\s\.,!\?]*$", "how_are_you"),
    (r"^(who\s+are\s+you|what\s+are\s+you|tell\s+me\s+about\s+yourself|introduce\s+yourself)[\s\.,!\?]*$", "capabilities"),
    (r"^(what\s+can\s+you\s+do|explain\s+your\s+capabilities|your\s+capabilities|how\s+can\s+you\s+help|what\s+do\s+you\s+know)[\s\.,!\?]*$", "capabilities"),
    (r"^(thank\s+you|thanks(\s+a\s+lot)?|appreciate\s+it|thx|many\s+thanks)[\s\.,!]*$", "thank_you"),
    (r"^(can\s+you\s+help(\s+me)?|need\s+help|assist\s+me)[\s\.,!\?]*$", "capabilities"),
    (r"^(bye|goodbye|see\s+you|have\s+a\s+good\s+day)[\s\.,!]*$", "general_conversation"),
]

# 3. Groundwater Domain Education / Concepts (Explanations without location/numbers)
DOMAIN_EDUCATION_PATTERNS = [
    (r"\b(what\s+is\s+an?\s+aquifer|explain\s+aquifers?|define\s+aquifers?|aquifer\s+types?)\b", "aquifer"),
    (r"\b(difference\s+between\s+(groundwater\s+)?recharge\s+and\s+(groundwater\s+)?extraction|recharge\s+(vs\.?|versus)\s+extraction)\b", "recharge_vs_extraction"),
    (r"\b(what\s+is\s+(groundwater\s+)?recharge|explain\s+(groundwater\s+)?recharge|how\s+does\s+recharge\s+work|define\s+recharge)\b", "recharge"),
    (r"\b(why\s+is\s+groundwater\s+important|importance\s+of\s+groundwater|role\s+of\s+groundwater)\b", "importance"),
    (r"\b(explain\s+(groundwater\s+)?depletion|what\s+is\s+(groundwater\s+)?depletion|depletion\s+in\s+simple\s+language|causes?\s+of\s+depletion)\b", "depletion"),
    (r"\b(what\s+is\s+stage\s+of\s+extraction|explain\s+stage\s+of\s+extraction|how\s+is\s+stage\s+of\s+extraction\s+calculated|meaning\s+of\s+stage\s+of\s+extraction)\b", "stage_of_extraction"),
    (r"\b(what\s+is\s+over[\s\-]?exploited|meaning\s+of\s+over[\s\-]?exploited|define\s+over[\s\-]?exploited|what\s+does\s+over[\s\-]?exploited\s+mean)\b", "over_exploited"),
    (r"\b(what\s+is\s+critical\s+category|meaning\s+of\s+critical|define\s+critical\s+category)\b", "critical"),
    (r"\b(what\s+is\s+semi[\s\-]?critical|define\s+semi[\s\-]?critical)\b", "semi_critical"),
    (r"\b(what\s+is\s+safe\s+category|define\s+safe\s+category|what\s+does\s+safe\s+mean)\b", "safe"),
    (r"\b(what\s+is\s+in[\s\-]?gres|about\s+in[\s\-]?gres|tell\s+me\s+about\s+in[\s\-]?gres)\b", "ingres"),
    (r"\b(what\s+is\s+ham|what\s+does\s+ham\s+stand\s+for|hectare\s+meter)\b", "ham"),
    (r"\b(can\s+you\s+help\s+me\s+understand\s+groundwater|help\s+me\s+understand\s+groundwater)\b", "general_education"),
]

# 4. Conversational Follow-up Patterns (Robust regex covering all follow-up variants)
FOLLOWUP_COMPARE_PATTERN = re.compile(
    r"\b(compare\s+(both|these|them|the\s+two)|difference\s+between\s+(both|these|them)|how\s+do\s+they\s+compare)\b",
    re.IGNORECASE,
)

FOLLOWUP_EXPLAIN_PATTERN = re.compile(
    r"\b(explain\s+(that|this|the\s+previous)\s+(result|figure|data|number|value)|why\s+did\s+it\s+(decrease|increase|change)|what\s+does\s+this\s+(mean|figure\s+mean)|tell\s+me\s+more\s+about\s+(this|that|the\s+figure))\b",
    re.IGNORECASE,
)

# Year Follow-up: captures "in 2022?", "what about 2025?", "what about in 2026?", "and 2026?", "for 2020", "2025?"
FOLLOWUP_YEAR_PATTERN = re.compile(
    r"^(what\s+about\s+(in\s+)?|how\s+about\s+(in\s+)?|and\s+(in\s+)?|in\s+|for\s+)?(20\d{2})\??$",
    re.IGNORECASE,
)

# Parameter Follow-up: captures "what about recharge?", "show recharge", "recharge?", "what about extraction?"
FOLLOWUP_PARAM_PATTERN = re.compile(
    r"^(what\s+about\s+|how\s+about\s+|and\s+|show\s+)?(recharge|extraction|extractable(\s+resources?)?|stage(\s+of\s+extraction)?|categor(y|ization))\??$",
    re.IGNORECASE,
)

# Location Follow-up: captures "what about Punjab?", "and Gaya?", "in Rajasthan?"
FOLLOWUP_LOCATION_PATTERN = re.compile(
    r"^(what\s+about\s+(in\s+)?|how\s+about\s+(in\s+)?|and\s+(in\s+)?|in\s+|for\s+)?([a-zA-Z\s]{3,30})\??$",
    re.IGNORECASE,
)

# 5. Database query patterns (Ordered from most specific to least specific)
DB_INTENT_PATTERNS = [
    # Assessment years metadata
    ("get_assessment_years",
     r"\b(assessment\s+years?|years?\s+available|available\s+years?|available\s+periods?|assessment\s+periods?|which\s+years?|what\s+years?)\b"),

    # Districts in state
    ("get_districts_in_state",
     r"\b(list\s+districts|districts\s+in\s+[a-zA-Z\s]+\s+with|districts\s+with\s+groundwater)\b"),

    # State list metadata
    ("get_state_list",
     r"\b(which\s+state[s]?\s+have|all\s+state[s]?|list\s+(of\s+)?state[s]?|state[s]?\s+available|state[s]?\s+have\s+data)\b"),

    # Over-exploited districts/units
    ("get_overexploited_units",
     r"\b(over[\s\-]?exploit[ed]*)\b"),

    # Historical Trends & Multi-year
    ("get_historical_groundwater_data",
     r"\b(historical\s+(data|trend|analysis)|multi[\s\-]?year|trend\s+of|yearly\s+trend|time\s+series|across\s+(all\s+)?years|over\s+time)\b"),

    # Compare Assessment Years
    ("compare_assessment_years",
     r"\b(compare\b.*\b(20\d{2})\b.*\b(20\d{2})\b|compare\s+(both|these)\s+years|between\s+(20\d{2})\s+and\s+(20\d{2}))\b"),

    # Comparison of locations
    ("compare_locations",
     r"\b(compare|versus|vs\.?)\b"),

    # Assessment category
    ("get_assessment_category",
     r"\b(assessment\s+categor\w*|categor(?:y|ies)|classification|classif\w*|safe\s+or\s+critical|critical\s+or\s+safe|is\s+[a-zA-Z\s]+\s+safe|is\s+[a-zA-Z\s]+\s+critical)\b"),

    # Stage of extraction
    ("get_stage_of_extraction",
     r"\b(stage\s+of|stage\s+.*extract|percent.*extract|what\s+percent)\b"),

    # Country/national summary
    ("get_country_summary",
     r"\b(national|country[\s\-]?wide|all[\s\-]india|across\s+india)\b"),

    # State summary
    ("get_state_summary",
     r"\b(statistics\s+for|state\s+summary|summary\s+of\s+groundwater|groundwater\s+summary\s+for|state\s+level\s+summary|overview\s+for|groundwater\s+overview)\b"),

    # District summary
    ("get_district_summary",
     r"\b(district\s+summary|complete\s+groundwater|all\s+groundwater\s+data|full\s+data|situation\s+in|groundwater\s+situation)\b"),

    # Recharge
    ("get_groundwater_recharge",
     r"\b(recharg[e]?)\b"),

    # Extractable resources
    ("get_extractable_groundwater",
     r"\b(extractable|net\s+availability|availability\s+for\s+future|future\s+availability)\b"),

    # Extraction
    ("get_groundwater_extraction",
     r"\b(extraction|utiliz(ation)?|how\s+much\s+groundwater|groundwater\s+(is\s+)?(use[d]?|utiliz))\b"),

    # Groundwater level (unsupported in dynamic compilation)
    ("get_groundwater_level",
     r"\b(groundwater\s+level|water\s+level|water\s+table|depth\s+to\s+water|well\s+depth|depth.*well)\b"),
]

AMBIGUOUS_PATTERN = re.compile(r"\bgroundwater\b", re.IGNORECASE)
NON_AMBIGUOUS_CLUES = re.compile(
    r"\b(recharge|extraction|extract|level|stage|categor|assess|year|state|national|utiliz|availab|exploit|compare|classif|depth|well|table|statistic|summary|situation|overview|district|aquifer|depletion|difference|between|how|what|why|who|explain)\b",
    re.IGNORECASE,
)


def classify_intent(question: str) -> Dict[str, Any]:
    """
    Classifies question into one of 8 broad categories and specific intent.
    Never misclassifies a follow-up query as a greeting.
    """
    q = question.lower().strip()

    # 1. Pure Greetings (only matches when strictly a greeting)
    if GREETING_PATTERN.match(q):
        return {
            "intent": "greeting",
            "broad_category": "greeting",
            "confidence": 0.99,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": True,
            "sub_topic": "greeting",
        }

    # 2. General Conversation / Small Talk / Gratitude
    for pat, sub in GENERAL_CONVERSATION_PATTERNS:
        if re.match(pat, q, re.IGNORECASE):
            return {
                "intent": "general_conversation",
                "broad_category": "general_conversation",
                "confidence": 0.95,
                "requires_clarification": False,
                "clarification_question": None,
                "is_conversational": True,
                "sub_topic": sub,
            }

    # 3. Conversational Follow-up: Comparison (e.g. "compare both", "difference between both")
    if FOLLOWUP_COMPARE_PATTERN.search(q):
        return {
            "intent": "compare_assessment_years",
            "broad_category": "conversational_followup",
            "confidence": 0.95,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": False,
            "sub_topic": "followup_compare",
        }

    # 4. Conversational Follow-up: Explain previous result (e.g. "explain that result", "why did it decrease?")
    if FOLLOWUP_EXPLAIN_PATTERN.search(q):
        return {
            "intent": "conversational_followup",
            "broad_category": "conversational_followup",
            "confidence": 0.95,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": True,
            "sub_topic": "followup_explain",
        }

    # 5. Conversational Follow-up: Year only (e.g. "in 2022?", "what about 2025?", "what about in 2026?", "and 2026?", "2025?")
    ym = FOLLOWUP_YEAR_PATTERN.match(q)
    if ym:
        target_yr = ym.group(5)
        return {
            "intent": "conversational_followup",
            "broad_category": "conversational_followup",
            "confidence": 0.95,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": False,
            "sub_topic": "followup_year",
            "extracted_year": target_yr,
        }

    # 6. Conversational Follow-up: Parameter only (e.g. "what about recharge?", "show recharge")
    pm = FOLLOWUP_PARAM_PATTERN.match(q)
    if pm:
        param_name = pm.group(2).lower()
        if "recharge" in param_name:
            fine_intent = "get_groundwater_recharge"
        elif "extractable" in param_name:
            fine_intent = "get_extractable_groundwater"
        elif "stage" in param_name:
            fine_intent = "get_stage_of_extraction"
        elif "categor" in param_name:
            fine_intent = "get_assessment_category"
        else:
            fine_intent = "get_groundwater_extraction"

        return {
            "intent": fine_intent,
            "broad_category": "conversational_followup",
            "confidence": 0.92,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": False,
            "sub_topic": "followup_parameter",
            "extracted_parameter": param_name,
        }

    # 7. Check for Mixed Query: Educational definition + Specific location/year numerical data
    has_edu_trigger = any(
        re.search(pat, q, re.IGNORECASE)
        for pat, _ in DOMAIN_EDUCATION_PATTERNS
    ) or ("what is groundwater extraction" in q or "explain groundwater extraction" in q)
    has_location_or_year = bool(
        re.search(r"\b(in|for|at)\s+([a-zA-Z\s]+)\b", q) and
        re.search(r"\b(20\d{2})\b", q)
    )
    if has_edu_trigger and has_location_or_year:
        return {
            "intent": "mixed_query",
            "broad_category": "mixed_query",
            "confidence": 0.92,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": False,
            "sub_topic": "concept_plus_data",
        }

    # 8. Check Groundwater Domain Education / Concepts (Definitions without specific district/year numbers)
    for pat, sub in DOMAIN_EDUCATION_PATTERNS:
        if re.search(pat, q, re.IGNORECASE):
            return {
                "intent": "groundwater_education",
                "broad_category": "groundwater_education",
                "confidence": 0.95,
                "requires_clarification": False,
                "clarification_question": None,
                "is_conversational": True,
                "sub_topic": sub,
            }

    # 9. Conversational Follow-up: Location only (e.g. "what about Punjab?", "and Gaya?", "in Haryana?")
    # Must not contain words like "groundwater" or query verbs which indicate full or ambiguous queries
    if "groundwater" not in q and not any(w in q for w in ["show", "give", "tell", "list", "how much", "how many"]):
        lm = FOLLOWUP_LOCATION_PATTERN.match(q)
        if lm:
            cand = lm.group(5).strip()
            geo = resolve_geography(cand)
            if geo.get("state") or geo.get("district"):
                return {
                    "intent": "conversational_followup",
                    "broad_category": "conversational_followup",
                    "confidence": 0.90,
                    "requires_clarification": False,
                    "clarification_question": None,
                    "is_conversational": False,
                    "sub_topic": "followup_location",
                    "extracted_state": geo.get("state"),
                    "extracted_district": geo.get("district"),
                }

    # 10. Check Database Query Patterns
    for db_intent, pattern in DB_INTENT_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            broad = "unsupported_query" if db_intent == "get_groundwater_level" else "groundwater_database_query"
            return {
                "intent": db_intent,
                "broad_category": broad,
                "confidence": 0.90,
                "requires_clarification": False,
                "clarification_question": None,
                "is_conversational": False,
                "sub_topic": None,
            }

    # 11. Ambiguity check: "groundwater" mentioned without any parameter or question intent
    if AMBIGUOUS_PATTERN.search(q) and not NON_AMBIGUOUS_CLUES.search(q):
        return {
            "intent": "ambiguous",
            "broad_category": "clarification_required",
            "confidence": 0.50,
            "requires_clarification": True,
            "clarification_question": (
                "Which groundwater parameter would you like to know? "
                "Please choose: recharge, extraction, extractable resources, "
                "stage of extraction, or assessment category."
            ),
            "is_conversational": False,
            "sub_topic": None,
        }

    # 12. Check if question contains geographic location clues (state or district)
    geo = resolve_geography(question)
    if geo.get("state") or geo.get("district"):
        return {
            "intent": "get_district_summary" if geo.get("district") else "get_state_summary",
            "broad_category": "groundwater_database_query",
            "confidence": 0.70,
            "requires_clarification": False,
            "clarification_question": None,
            "is_conversational": False,
            "sub_topic": None,
        }

    # 13. Fallback: Conversational assistance
    return {
        "intent": "general_conversation",
        "broad_category": "general_conversation",
        "confidence": 0.50,
        "requires_clarification": False,
        "clarification_question": None,
        "is_conversational": True,
        "sub_topic": "unrecognized_general",
    }
