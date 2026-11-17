"""
Conversational Session Manager — handles multi-turn conversation memory,
context retention (follow-up queries like 'What about 2025?', 'Compare both', 'What about Punjab?'),
and groundwater domain knowledge explanations.
"""
import uuid
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from ..database.models import ConversationSession, ConversationMessage
from ..nlp.gemini_agent import get_gemini_agent


DOMAIN_KNOWLEDGE: Dict[str, str] = {
    "aquifer": (
        "An **aquifer** is an underground layer of water-bearing permeable rock, rock fractures, "
        "or unconsolidated materials (gravel, sand, or silt) from which groundwater can be "
        "extracted using a water well or borewell.\n\n"
        "In India, major aquifer systems include:\n"
        "• **Alluvial Aquifers:** Indo-Gangetic and Brahmaputra plains with high storage and yield.\n"
        "• **Hard-Rock Aquifers:** Peninsular shield (Basalt/Deccan Traps, Granite, Gneiss) where water occurs in fractures."
    ),
    "recharge": (
        "**Groundwater recharge** is the hydrologic process by which surface water moves downward "
        "into saturated aquifer reservoirs.\n\n"
        "Under the GEC-2015 methodology, Annual Groundwater Recharge is assessed across two seasons:\n"
        "1. **Monsoon Season Recharge:** Rainfall infiltration plus other sources (canal seepage, return flow from irrigation, water harvesting structures).\n"
        "2. **Non-Monsoon Season Recharge:** Rainfall infiltration and other return flows during dry months.\n"
        "Subtracting natural discharges gives the **Annual Extractable Groundwater Resource**."
    ),
    "depletion": (
        "**Groundwater depletion** occurs when groundwater extraction persistently exceeds natural recharge rates.\n\n"
        "In simple terms, it is like withdrawing money from a bank account faster than it is deposited. "
        "Major consequences include:\n"
        "• Falling water table levels and dry borewells.\n"
        "• Escalating pumping costs and energy demands.\n"
        "• Water quality degradation (fluoride, arsenic, or salinity ingress).\n"
        "• Diminished baseflow in connected river systems and drying wetlands."
    ),
    "recharge_vs_extraction": (
        "**Groundwater Recharge vs. Extraction:**\n\n"
        "• **Recharge** is the annual replenishment of aquifers from rainfall, canal seepage, and irrigation return flows.\n"
        "• **Extraction** is the gross withdrawal of groundwater for human use (irrigation, domestic, and industrial).\n\n"
        "The balance between the two determines groundwater sustainability. The ratio of extraction to extractable recharge defines the **Stage of Groundwater Extraction (SOE %)**."
    ),
    "extraction": (
        "**Groundwater extraction** refers to the total volume of groundwater pumped from aquifers "
        "for socioeconomic uses. In CGWB assessments, it is accounted under three distinct sectors:\n"
        "1. **Irrigation Extraction:** Agriculture and crop irrigation (typically >85% of total in India).\n"
        "2. **Domestic Extraction:** Drinking and household supply.\n"
        "3. **Industrial Extraction:** Manufacturing, commercial operations, and mining."
    ),
    "importance": (
        "**Why is groundwater important?**\n\n"
        "Groundwater is India's most critical freshwater lifeline:\n"
        "• **Agriculture:** Sustains over 60% of irrigated agriculture and underpins national food security.\n"
        "• **Drinking Water:** Supplies more than 85% of rural drinking water and nearly 50% of urban municipal requirements.\n"
        "• **Drought Buffer:** Acts as a vital buffer against climate variability and monsoon delays."
    ),
    "stage_of_extraction": (
        "The **Stage of Groundwater Extraction (SOE)** is defined by GEC methodology as:\n\n"
        "$$\\text{SOE (\\%)} = \\left( \\frac{\\text{Total Annual Groundwater Extraction}}{\\text{Annual Extractable Groundwater Resource}} \\right) \\times 100$$\n\n"
        "CGWB categorizes assessment units based on SOE:\n"
        "• **Safe:** $\\le 70\\%$\n"
        "• **Semi-Critical:** $> 70\\%$ and $\\le 90\\%$\n"
        "• **Critical:** $> 90\\%$ and $\\le 100\\%$\n"
        "• **Over-Exploited:** $> 100\\%$"
    ),
    "over_exploited": (
        "An assessment unit (district, block, or taluk) is categorized as **Over-Exploited** "
        "when the Stage of Groundwater Extraction exceeds 100%, meaning withdrawal is higher than annual replenishment. "
        "In these areas, long-term water levels exhibit significant declining trends, requiring urgent regulatory interventions."
    ),
    "critical": (
        "An assessment unit is categorized as **Critical** when the Stage of Groundwater Extraction "
        "is between 90% and 100%. Water withdrawal is approaching the full extractable potential, necessitating conservation."
    ),
    "semi_critical": (
        "An assessment unit is categorized as **Semi-Critical** when the Stage of Groundwater Extraction "
        "is between 70% and 90%. Precautionary measures and artificial recharge are advised."
    ),
    "safe": (
        "An assessment unit is categorized as **Safe** when the Stage of Groundwater Extraction is "
        "70% or less, with no significant long-term decline in water levels."
    ),
    "ingres": (
        "**IN-GRES** (India Groundwater Resource Estimation System) is the official digital web platform "
        "developed by the Central Ground Water Board (CGWB), Department of Water Resources, Ministry of Jal Shakti, "
        "in collaboration with IIT Hyderabad. It standardizes dynamic groundwater assessment using GEC-2015 methodology."
    ),
    "ham": (
        "**Ham** stands for **Hectare Meter** (1 Ham = 10,000 cubic meters = 10 million liters). "
        "It is the standard volumetric unit used by CGWB and IN-GRES for regional and district water accounting."
    ),
    "capabilities": (
        "I am **Groundwater AI**, an intelligent conversational assistant specialized in Indian groundwater resources.\n\n"
        "Here is what I can do:\n"
        "• **Verified Database Inquiries:** Query verified groundwater extraction, recharge, extractable resources, and categorization for districts and states.\n"
        "• **Historical & Cycle Comparisons:** Compare assessments across cycles (e.g. 2022 vs. 2025) with provenance.\n"
        "• **Source Transparency:** View exact CGWB source documents, publications, and verification audit trails.\n"
        "• **Hydrogeological Concepts:** Explain aquifers, recharge, depletion, stage of extraction, and GEC methodologies."
    ),
    "how_are_you": (
        "I'm doing well, thank you for asking! I'm ready to assist you with India's groundwater resource assessments, "
        "hydrogeological data, or general concepts. What would you like to explore today?"
    ),
    "thank_you": (
        "You're very welcome! If you have any more questions about groundwater recharge, extraction, historical records, "
        "or hydrogeology, feel free to ask anytime."
    ),
    "greeting": (
        "Hi! I'm Groundwater AI. How can I help you today? You can ask me about groundwater resources, "
        "recharge, extraction, historical assessments, or general groundwater concepts."
    ),
}


class SessionManager:
    """Manages multi-turn conversation sessions and context resolution."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, session_id: Optional[str] = None) -> ConversationSession:
        """Retrieve existing session or create a new one."""
        if session_id:
            session = self.db.query(ConversationSession).filter(
                ConversationSession.session_id == session_id
            ).first()
            if session:
                return session

        new_id = session_id or str(uuid.uuid4())
        session = ConversationSession(
            session_id=new_id,
            active_context=json.dumps({
                "last_state": None,
                "last_district": None,
                "last_year": "2022",
                "last_parameter": None,
                "last_intent": None,
                "recent_years": [],
            }),
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_context(self, session: ConversationSession) -> Dict[str, Any]:
        """Load active context dictionary."""
        if not session.active_context:
            return {}
        try:
            return json.loads(session.active_context)
        except Exception:
            return {}

    def update_context(self, session: ConversationSession, updates: Dict[str, Any]):
        """Update and persist active context dictionary."""
        ctx = self.get_context(session)
        ctx.update(updates)

        # Track recent years for comparison
        yr = updates.get("last_year")
        if yr:
            recent_years = ctx.get("recent_years", [])
            if yr not in recent_years:
                recent_years.append(yr)
            ctx["recent_years"] = recent_years[-3:]  # Keep last 3

        session.active_context = json.dumps(ctx)
        if "last_state" in updates:
            session.active_state = updates["last_state"]
        if "last_district" in updates:
            session.active_district = updates["last_district"]
        if "last_year" in updates:
            session.active_year = str(updates["last_year"])
        if "last_parameter" in updates:
            session.active_parameter = updates["last_parameter"]
        if "last_intent" in updates:
            session.last_intent = updates["last_intent"]
        if "last_function" in updates:
            session.last_function = updates["last_function"]
        if "last_result_summary" in updates:
            session.last_result_summary = updates["last_result_summary"]
        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def resolve_conversational_query(
        self, question: str, session: ConversationSession
    ) -> Optional[Dict[str, Any]]:
        """
        Check if the question is an educational concept, small talk, greeting, or follow-up explanation.
        Returns a response dict if handled conversationally, or None if it's a data query.
        """
        q = question.lower().strip()

        # 1. Greetings (e.g. "hii", "hello", "hi", "good morning")
        if re.match(r"^(hi|hello|hii+|hey+|heyy+|greetings|good\s+(morning|afternoon|evening)|howdy|namaste|sup)[\s\.,!]*$", q):
            return {
                "type": "greeting",
                "intent": "greeting",
                "answer": DOMAIN_KNOWLEDGE["greeting"],
                "requires_database": False,
            }

        # 2. General conversation / small talk
        if any(re.search(pat, q) for pat in [r"\bhow\s+are\s+you\b", r"\bhow\s+are\s+you\s+doing\b"]):
            return {
                "type": "general_conversation",
                "intent": "general_conversation",
                "answer": DOMAIN_KNOWLEDGE["how_are_you"],
                "requires_database": False,
            }

        if any(re.search(pat, q) for pat in [r"\bthank\s+you\b", r"\bthanks\b", r"\bappreciate\s+it\b"]):
            return {
                "type": "general_conversation",
                "intent": "general_conversation",
                "answer": DOMAIN_KNOWLEDGE["thank_you"],
                "requires_database": False,
            }

        if any(re.search(pat, q) for pat in [
            r"\bwhat\s+can\s+you\s+do\b",
            r"\btell\s+me\s+about\s+yourself\b",
            r"\bwho\s+are\s+you\b",
            r"\bexplain\s+your\s+capabilities\b",
            r"\byour\s+capabilities\b",
            r"\bwhat\s+are\s+your\s+features\b"
        ]):
            return {
                "type": "general_conversation",
                "intent": "general_conversation",
                "answer": DOMAIN_KNOWLEDGE["capabilities"],
                "requires_database": False,
            }

        # 3. Follow-up: Explain previous result (e.g. "explain that result", "explain this figure")
        if any(phrase in q for phrase in [
            "explain that result", "explain this result", "explain that figure", "explain this figure",
            "explain the result", "explain the figure", "why did it change", "what does this number mean",
            "tell me more about this result", "explain that"
        ]):
            ctx = self.get_context(session)
            last_dist = ctx.get("last_district")
            last_st = ctx.get("last_state")
            last_yr = ctx.get("last_year")
            last_param = ctx.get("last_parameter")
            last_sum = ctx.get("last_result_summary")

            loc_str = f"{last_dist}, {last_st}" if last_dist and last_st else (last_dist or last_st or "the requested location")
            yr_str = str(last_yr) if last_yr else "the recent assessment"

            if last_param == "recharge" or "recharge" in str(last_sum).lower():
                ans = (
                    f"**Explanation of Groundwater Recharge Assessment for {loc_str} ({yr_str}):**\n\n"
                    f"Under the Central Ground Water Board (CGWB) **GEC-2015 Methodology**, Annual Groundwater Recharge "
                    f"quantifies the volume of water naturally and artificially replenished into the aquifer reservoirs.\n\n"
                    f"**Key Hydrological Components:**\n"
                    f"1. **Monsoon Rainfall Infiltration:** The predominant recharge source in the Gangetic plain, where porous alluvial formations enable high infiltration during heavy rainfall events.\n"
                    f"2. **Non-Monsoon Recharge:** Rainfall replenishment occurring outside the monsoon season.\n"
                    f"3. **Other Sources:** Subsurface seepage from irrigation canals, return flow from applied surface and groundwater irrigation, and percolation from water conservation structures.\n\n"
                    f"**Resource Significance:** Total annual recharge represents the gross replenishment. Deducting natural discharges gives the **Annual Extractable Groundwater Resource**, which serves as the ceiling for safe withdrawal."
                )
            elif last_param == "extraction" or "extraction" in str(last_sum).lower():
                ans = (
                    f"**Explanation of Groundwater Extraction Assessment for {loc_str} ({yr_str}):**\n\n"
                    f"In official CGWB and IN-GRES compilations, groundwater extraction accounts for the total volume "
                    f"of water pumped from aquifer units across three distinct sectors:\n\n"
                    f"1. **Irrigation Extraction:** Agriculture and crop irrigation, which accounts for the vast majority of water withdrawal.\n"
                    f"2. **Domestic Extraction:** Drinking water and municipal supply requirements for urban and rural populations.\n"
                    f"3. **Industrial Extraction:** Pumping for industrial production, commercial activities, and manufacturing.\n\n"
                    f"The ratio of this total extraction to the annual extractable resource defines the **Stage of Groundwater Extraction (SOE %)**, determining whether the unit is categorized as Safe (≤70%), Semi-Critical (70-90%), Critical (90-100%), or Over-Exploited (>100%)."
                )
            elif "compare" in str(last_sum).lower() or ctx.get("last_intent") == "compare_assessment_years":
                ans = (
                    f"**Explanation of Historical Comparison for {loc_str}:**\n\n"
                    f"The observed change across assessment cycles reflects dynamic changes in both hydrologic conditions and socioeconomic demand:\n"
                    f"• **Rainfall Variability:** Variations in monsoon intensity and temporal distribution directly influence natural recharge volumes.\n"
                    f"• **Extraction Demand:** Changes in cropping patterns, irrigation efficiency, and urban domestic pumping alter gross withdrawal rates.\n"
                    f"• **Methodology Refinement:** GEC-2015 updates and improved telemetry/monitoring stations enhance measurement precision over time."
                )
            else:
                ans = (
                    f"**Explanation of Assessment Result for {loc_str}:**\n\n"
                    f"This figure represents verified dynamic groundwater resource data compiled under the GEC-2015 methodology. "
                    f"It incorporates both seasonal field observation well measurements and surface hydrologic modeling approved by the Central Ground Water Board (CGWB)."
                )

            return {
                "type": "groundwater_education",
                "intent": "followup_explain",
                "answer": ans,
                "requires_database": False,
            }

        # 3. Domain Knowledge Education (Educational concepts)
        if "aquifer" in q and not any(w in q for w in ["in patna", "in bihar", "in punjab", "in 2022", "in 2025"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["aquifer"],
                "requires_database": False,
            }

        if "depletion" in q:
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["depletion"],
                "requires_database": False,
            }

        if "recharge" in q and "extraction" in q and any(w in q for w in ["difference", "diff", "versus", "vs", "between"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["recharge_vs_extraction"],
                "requires_database": False,
            }

        if "importance" in q or ("why is" in q and "groundwater" in q and "important" in q):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["importance"],
                "requires_database": False,
            }

        if any(phrase in q for phrase in ["what is groundwater recharge", "explain groundwater recharge", "define groundwater recharge"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["recharge"],
                "requires_database": False,
            }

        if any(phrase in q for phrase in ["what is groundwater extraction", "explain groundwater extraction", "define groundwater extraction"]) and not any(yr in q for yr in ["2020", "2022", "2024", "2025", "2026"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["extraction"],
                "requires_database": False,
            }

        if "stage of extraction" in q and any(w in q for w in ["what is", "explain", "meaning", "define", "how is it calculated"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["stage_of_extraction"],
                "requires_database": False,
            }

        if "over-exploited" in q or "overexploited" in q:
            if any(w in q for w in ["what does", "what is", "meaning", "define", "explain"]):
                return {
                    "type": "groundwater_education",
                    "intent": "groundwater_education",
                    "answer": DOMAIN_KNOWLEDGE["over_exploited"],
                    "requires_database": False,
                }

        if "critical" in q and any(w in q for w in ["what does", "meaning", "define", "explain"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["critical"],
                "requires_database": False,
            }

        if "semi-critical" in q and any(w in q for w in ["what does", "meaning", "define", "explain"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["semi_critical"],
                "requires_database": False,
            }

        if "safe" in q and any(w in q for w in ["what does safe mean", "meaning of safe", "define safe category"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["safe"],
                "requires_database": False,
            }

        if "ingres" in q or "in-gres" in q:
            if any(w in q for w in ["what is", "about", "explain", "tell me"]):
                return {
                    "type": "groundwater_education",
                    "intent": "groundwater_education",
                    "answer": DOMAIN_KNOWLEDGE["ingres"],
                    "requires_database": False,
                }

        if "ham" in q and any(w in q for w in ["what is", "unit", "mean", "stand for"]):
            return {
                "type": "groundwater_education",
                "intent": "groundwater_education",
                "answer": DOMAIN_KNOWLEDGE["ham"],
                "requires_database": False,
            }

        # Follow-up educational questions
        if any(w in q for w in ["why is it important", "why is this important", "tell me more about it"]):
            ctx = self.get_context(session)
            last_intent = ctx.get("last_intent")
            if last_intent in ["groundwater_education", "recharge", "aquifer", "depletion"]:
                return {
                    "type": "groundwater_education",
                    "intent": "groundwater_education",
                    "answer": DOMAIN_KNOWLEDGE["importance"],
                    "requires_database": False,
                }

        return None

    def apply_context_to_query(
        self, parsed_query: Dict[str, Any], session: ConversationSession
    ) -> Dict[str, Any]:
        """
        Merge conversation context into follow-up queries.
        Handles:
        - 'What about 2025?' -> updates assessment_year, retains district/state/intent/parameter
        - 'Compare both' -> transforms into compare_assessment_years intent with recent years
        - 'What about recharge?' -> updates parameter/intent, retains district/state/year
        - 'What about Punjab?' -> updates state, retains parameter/intent
        """
        ctx = self.get_context(session)
        q = parsed_query["original_question"].lower().strip()

        # Never apply location context to pure greetings or small talk
        if parsed_query.get("is_conversational") and parsed_query.get("intent") in ["greeting", "general_conversation"]:
            return parsed_query

        # 1. Handle 'Compare both' or 'compare these years'
        if (
            parsed_query.get("sub_topic") == "followup_compare"
            or any(phrase in q for phrase in ["compare both", "compare these", "compare them", "difference between both"])
        ):
            recent_years = ctx.get("recent_years", [])
            if len(recent_years) >= 2:
                y1, y2 = recent_years[-2], recent_years[-1]
            else:
                y1, y2 = "2022", ctx.get("last_year", "2025")

            parsed_query["intent"] = "compare_assessment_years"
            parsed_query["state"] = ctx.get("last_state", "Bihar")
            parsed_query["district"] = ctx.get("last_district")
            parsed_query["year1"] = y1
            parsed_query["year2"] = y2
            parsed_query["parameter"] = ctx.get("last_parameter", "extraction")
            parsed_query["requires_clarification"] = False
            parsed_query["is_conversational"] = False
            return parsed_query

        # 2. Parameter Follow-up: "What about recharge?", "show recharge", "recharge?"
        from ..nlp.intent_classifier import FOLLOWUP_PARAM_PATTERN
        pm = FOLLOWUP_PARAM_PATTERN.match(q)
        if pm or parsed_query.get("sub_topic") == "followup_parameter":
            param_raw = (pm.group(2) if pm else parsed_query.get("extracted_parameter") or "recharge").lower()
            if "recharge" in param_raw:
                fine_intent = "get_groundwater_recharge"
                fine_param = "recharge"
            elif "extractable" in param_raw:
                fine_intent = "get_extractable_groundwater"
                fine_param = "extractable"
            elif "stage" in param_raw:
                fine_intent = "get_stage_of_extraction"
                fine_param = "stage"
            elif "categor" in param_raw:
                fine_intent = "get_assessment_category"
                fine_param = "category"
            else:
                fine_intent = "get_groundwater_extraction"
                fine_param = "extraction"

            parsed_query["intent"] = fine_intent
            parsed_query["parameter"] = fine_param
            if ctx.get("last_district"):
                parsed_query["district"] = ctx.get("last_district")
            if ctx.get("last_state"):
                parsed_query["state"] = ctx.get("last_state")

            # Check if there's a verified record for this location and parameter
            from ..database import repository as repo
            latest_rec = repo.get_latest_verified_record(
                self.db,
                state=parsed_query.get("state"),
                district=parsed_query.get("district"),
                parameter=fine_param,
            )
            if latest_rec:
                parsed_query["assessment_year"] = latest_rec["latest_year"]
            elif ctx.get("last_year"):
                parsed_query["assessment_year"] = ctx.get("last_year")
            else:
                parsed_query["assessment_year"] = "2022"

            parsed_query["requires_clarification"] = False
            parsed_query["is_conversational"] = False
            return parsed_query

        # 3. Follow-up with year only: "What about 2025?", "How about 2020?", "And 2026?", "in 2022?"
        year_match = re.search(r"\b(20\d{2})\b", q)
        is_year_followup = (
            year_match and
            not parsed_query.get("state") and
            not parsed_query.get("district") and
            (
                parsed_query.get("sub_topic") == "followup_year" or
                any(w in q for w in ["what about", "how about", "and", "for", "in", "20"])
            )
        )
        if is_year_followup:
            target_year = year_match.group(1)
            parsed_query["assessment_year"] = target_year
            if ctx.get("last_district"):
                parsed_query["district"] = ctx.get("last_district")
            if ctx.get("last_state"):
                parsed_query["state"] = ctx.get("last_state")
            if ctx.get("last_parameter"):
                parsed_query["parameter"] = ctx.get("last_parameter")

            # Determine intent for single year query
            if ctx.get("last_parameter") == "recharge":
                parsed_query["intent"] = "get_groundwater_recharge"
            elif ctx.get("last_parameter") in ["extractable", "annual_extractable_groundwater"]:
                parsed_query["intent"] = "get_extractable_groundwater"
            elif ctx.get("last_parameter") in ["stage", "stage_of_extraction"]:
                parsed_query["intent"] = "get_stage_of_extraction"
            elif ctx.get("last_parameter") in ["category", "assessment_category"]:
                parsed_query["intent"] = "get_assessment_category"
            elif ctx.get("last_intent") and ctx.get("last_intent") not in [
                "ambiguous", "greeting", "general_conversation", "conversational_followup", "compare_assessment_years", "compare_locations"
            ]:
                parsed_query["intent"] = ctx.get("last_intent")
            else:
                parsed_query["intent"] = "get_groundwater_extraction"

            parsed_query["requires_clarification"] = False
            parsed_query["is_conversational"] = False
            return parsed_query

        # 4. Follow-up with location only: "What about Punjab?", "How about Gaya?"
        is_location_followup = (
            parsed_query.get("sub_topic") == "followup_location" or
            ((parsed_query.get("state") or parsed_query.get("district")) and not parsed_query.get("parameter"))
        )
        if is_location_followup:
            # If state specified and no district, clear previous district
            if parsed_query.get("state") and not parsed_query.get("district"):
                parsed_query["district"] = None
                parsed_query["aggregation"] = "state"

            if ctx.get("last_parameter"):
                parsed_query["parameter"] = ctx.get("last_parameter")

            if parsed_query.get("parameter") == "recharge":
                parsed_query["intent"] = "get_groundwater_recharge"
            elif parsed_query.get("parameter") == "extraction":
                parsed_query["intent"] = "get_groundwater_extraction"
            elif ctx.get("last_intent") and ctx.get("last_intent") not in ["ambiguous", "greeting", "general_conversation", "conversational_followup"]:
                parsed_query["intent"] = ctx.get("last_intent")
            else:
                parsed_query["intent"] = "get_groundwater_recharge" if parsed_query.get("parameter") == "recharge" else "get_groundwater_extraction"

            if not parsed_query.get("assessment_year"):
                if ctx.get("last_year"):
                    parsed_query["assessment_year"] = ctx.get("last_year")
                else:
                    parsed_query["assessment_year"] = "2022"

            parsed_query["requires_clarification"] = False
            parsed_query["is_conversational"] = False
            return parsed_query

        return parsed_query

    def record_turn(
        self,
        session: ConversationSession,
        question: str,
        answer: str,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None,
        function_name: Optional[str] = None,
        parameters: Optional[Dict] = None,
        result_data: Optional[Dict] = None,
        trace: Optional[List] = None,
        execution_time_ms: float = 0.0,
    ):
        """Save user question and agent response to conversation history."""
        user_msg = ConversationMessage(
            session_id=session.session_id,
            role="user",
            content=question,
        )
        self.db.add(user_msg)

        asst_msg = ConversationMessage(
            session_id=session.session_id,
            role="assistant",
            content=answer,
            intent=intent,
            entities_json=json.dumps(entities) if entities else None,
            function_called=function_name,
            parameters_json=json.dumps(parameters) if parameters else None,
            result_json=json.dumps(result_data) if result_data else None,
            execution_trace_json=json.dumps(trace) if trace else None,
        )
        self.db.add(asst_msg)
        self.db.commit()
