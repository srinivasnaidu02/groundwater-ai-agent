"""
Query Parser — ties together intent classification, entity extraction,
and conversational routing.
Supports Rule-based, ML baseline (TF-IDF + Logistic Regression), Gemini 2.5 Flash,
and Hybrid Ensemble modes.
"""
from typing import Dict, Optional
from .intent_classifier import classify_intent
from .entity_extractor import extract_entities
from .ml_classifier import get_ml_classifier
from .gemini_agent import get_gemini_agent
from .geo_resolver import resolve_geography


def parse_question(question: str, mode: str = "hybrid") -> Dict:
    """
    Parse a natural-language question into a structured query object.
    Modes:
      - 'rule_based': Uses deterministic pattern matching and entity dicts.
      - 'ml': Uses Scikit-Learn TF-IDF + Logistic Regression classifier.
      - 'gemini': Uses Gemini LLM structured extraction (falls back to hybrid if unavailable).
      - 'hybrid': Combines rules for deterministic safety with ML and Gemini when applicable.
    """
    rule_intent = classify_intent(question)
    entities = extract_entities(question)

    # Enhance geography with dynamic resolver
    geo_res = resolve_geography(question)
    if not entities["state"] and geo_res.get("state"):
        entities["state"] = geo_res["state"]
    if not entities["district"] and geo_res.get("district"):
        entities["district"] = geo_res["district"]
        if not entities["state"] and geo_res.get("state"):
            entities["state"] = geo_res["state"]

    selected_intent = rule_intent["intent"]
    broad_category = rule_intent.get("broad_category", "groundwater_database_query")
    is_conversational = rule_intent.get("is_conversational", False)
    sub_topic = rule_intent.get("sub_topic")
    confidence = rule_intent["confidence"]
    requires_clarification = rule_intent["requires_clarification"]
    clarification_question = rule_intent.get("clarification_question")
    model_used = "Rule-Based Engine"

    # If already identified as conversational / greeting / education / follow-up, preserve it
    if is_conversational or broad_category == "conversational_followup":
        model_used = "Conversational Intent Router"

    elif mode == "ml":
        ml_clf = get_ml_classifier()
        ml_res = ml_clf.predict(question)
        selected_intent = ml_res["intent"]
        confidence = ml_res["confidence"]
        requires_clarification = False
        model_used = "Scikit-Learn (TF-IDF + Logistic Regression)"

    elif mode == "gemini":
        gemini_agent = get_gemini_agent()
        gemini_res = gemini_agent.parse_query(question) if gemini_agent.is_available else None
        if gemini_res:
            selected_intent = gemini_res.get("intent", selected_intent)
            confidence = gemini_res.get("confidence", 0.95)
            requires_clarification = gemini_res.get("requires_clarification", False)
            clarification_question = gemini_res.get("clarification_question")
            if gemini_res.get("state"):
                entities["state"] = gemini_res["state"]
            if gemini_res.get("district"):
                entities["district"] = gemini_res["district"]
            if gemini_res.get("assessment_year"):
                entities["assessment_year"] = gemini_res["assessment_year"]
            model_used = "Gemini 2.5 Flash"
        else:
            # Fall back to ML or Rule
            ml_clf = get_ml_classifier()
            ml_res = ml_clf.predict(question)
            selected_intent = ml_res["intent"]
            confidence = ml_res["confidence"]
            model_used = "Scikit-Learn (Fallback)"

    elif mode == "hybrid":
        # If rule confidence is high (> 0.85), use rules for predictable zero-latency safety
        if rule_intent["confidence"] >= 0.85 and not rule_intent["requires_clarification"]:
            selected_intent = rule_intent["intent"]
            confidence = rule_intent["confidence"]
            model_used = "Rule-Based (High Confidence)"
        else:
            # Check ML classifier
            ml_clf = get_ml_classifier()
            ml_res = ml_clf.predict(question)
            if ml_res["confidence"] >= 0.60:
                selected_intent = ml_res["intent"]
                confidence = ml_res["confidence"]
                requires_clarification = False
                model_used = "Scikit-Learn TF-IDF"

    if rule_intent.get("extracted_year") and not entities.get("assessment_year"):
        entities["assessment_year"] = rule_intent["extracted_year"]
    if rule_intent.get("extracted_parameter") and not entities.get("parameter"):
        entities["parameter"] = rule_intent["extracted_parameter"]
    if rule_intent.get("extracted_state") and not entities.get("state"):
        entities["state"] = rule_intent["extracted_state"]
    if rule_intent.get("extracted_district") and not entities.get("district"):
        entities["district"] = rule_intent["extracted_district"]

    return {
        "original_question": question,
        "intent": selected_intent,
        "broad_category": broad_category,
        "is_conversational": is_conversational,
        "sub_topic": sub_topic,
        "confidence": confidence,
        "requires_clarification": requires_clarification,
        "clarification_question": clarification_question,
        "model_used": model_used,
        "state": entities["state"],
        "district": entities["district"],
        "block": entities["block"],
        "assessment_year": entities["assessment_year"],
        "year1": entities.get("year1"),
        "year2": entities.get("year2"),
        "parameter": entities["parameter"],
        "aggregation": entities["aggregation"],
        "comparison_locations": entities["comparison_locations"],
    }
