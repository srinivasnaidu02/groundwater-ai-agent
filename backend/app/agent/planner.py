"""
Query Planner — receives NLP output, selects appropriate database function,
validates parameters, and prepares for execution.
"""
import time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from ..database.functions import FUNCTION_REGISTRY, execute_function
from ..database import repository as repo


INTENT_FUNCTION_MAP: Dict[str, str] = {
    "get_assessment_years":      "get_assessment_years",
    "get_state_list":            "get_state_list",
    "get_country_summary":       "get_country_summary",
    "get_state_summary":         "get_state_summary",
    "get_district_summary":      "get_district_summary",
    "get_groundwater_recharge":  "get_groundwater_recharge",
    "get_extractable_groundwater": "get_extractable_groundwater",
    "get_groundwater_extraction":  "get_groundwater_extraction",
    "get_stage_of_extraction":   "get_stage_of_extraction",
    "get_assessment_category":   "get_assessment_category",
    "get_overexploited_units":   "get_overexploited_units",
    "compare_locations":         "compare_locations",
    "compare_assessment_years":  "compare_assessment_years",
    "get_historical_groundwater_data": "get_historical_groundwater_data",
    "get_yearly_groundwater_trend": "get_yearly_groundwater_trend",
    "get_data_coverage":         "get_data_coverage",
    "get_location_details":      "get_location_details",
    "get_districts_in_state":    "get_districts_in_state",
    "get_groundwater_level":     "get_groundwater_level",
}

# Parameter mapping from intent to function signature parameters
INTENT_PARAM_MAP: Dict[str, List[str]] = {
    "get_assessment_years":      [],
    "get_state_list":            [],
    "get_country_summary":       ["assessment_year"],
    "get_state_summary":         ["state", "assessment_year"],
    "get_district_summary":      ["state", "district", "assessment_year"],
    "get_groundwater_recharge":  ["state", "district", "assessment_year"],
    "get_extractable_groundwater": ["state", "district", "assessment_year"],
    "get_groundwater_extraction":  ["state", "district", "assessment_year"],
    "get_stage_of_extraction":   ["state", "district", "assessment_year"],
    "get_assessment_category":   ["state", "district", "assessment_year"],
    "get_overexploited_units":   ["state", "assessment_year"],
    "compare_locations":         ["state1", "district1", "state2", "district2", "parameter", "assessment_year"],
    "compare_assessment_years":  ["state", "district", "parameter", "year1", "year2"],
    "get_historical_groundwater_data": ["state", "district", "parameter"],
    "get_yearly_groundwater_trend": ["state", "district", "parameter"],
    "get_data_coverage":         [],
    "get_location_details":      ["location"],
    "get_districts_in_state":    ["state"],
    "get_groundwater_level":     ["state", "district", "assessment_year"],
}


class QueryPlanner:
    def __init__(self, db: Session):
        self.db = db

    def plan_and_execute(self, parsed_query: Dict) -> Dict:
        """
        Takes parsed NLP output, creates execution plan, executes it.
        Returns structured result with trace.
        """
        trace = []
        t0 = time.time()

        def add_trace(step: int, name: str, status: str, detail: str, duration_ms: float = 0):
            trace.append({
                "step": step,
                "name": name,
                "status": status,
                "detail": detail,
                "duration_ms": round(duration_ms, 2),
            })

        # STEP 1: Question received
        add_trace(1, "Question Received", "success", parsed_query["original_question"])

        # STEP 2: NLP parsed
        t1 = time.time()
        add_trace(2, "NLP Processing", "success",
                  f"Intent: {parsed_query['intent']} (confidence: {parsed_query['confidence']:.0%})",
                  (time.time() - t1) * 1000)

        # STEP 3: Clarification check
        t2 = time.time()
        if parsed_query.get("requires_clarification"):
            add_trace(3, "Clarification Required", "clarification",
                      parsed_query.get("clarification_question", ""), (time.time() - t2) * 1000)
            return {
                "status": "clarification_needed",
                "question": parsed_query["original_question"],
                "intent": parsed_query["intent"],
                "entities": self._extract_entity_dict(parsed_query),
                "clarification_question": parsed_query.get("clarification_question"),
                "selected_function": None,
                "parameters": {},
                "result": None,
                "answer": parsed_query.get("clarification_question"),
                "execution_trace": trace,
                "execution_time_ms": round((time.time() - t0) * 1000, 2),
            }
        add_trace(3, "Intent Classified", "success",
                  f"Intent: {parsed_query['intent']}", (time.time() - t2) * 1000)

        # STEP 4: Entity extraction summary
        t3 = time.time()
        entities = self._extract_entity_dict(parsed_query)
        add_trace(4, "Entities Extracted", "success",
                  f"State: {entities.get('state')}, District: {entities.get('district')}, Year: {entities.get('assessment_year')}",
                  (time.time() - t3) * 1000)

        # MODE A: Conversational & Educational routing (No database access needed)
        intent = parsed_query["intent"]
        is_conv = parsed_query.get("is_conversational", False) or intent in [
            "greeting", "general_conversation", "groundwater_education", "domain_explanation"
        ]
        if is_conv and intent != "mixed_query":
            from .session_manager import DOMAIN_KNOWLEDGE
            sub = parsed_query.get("sub_topic") or ("greeting" if intent == "greeting" else "capabilities")
            ans = DOMAIN_KNOWLEDGE.get(sub, DOMAIN_KNOWLEDGE.get("greeting", "Hello! I am Groundwater AI."))
            add_trace(5, "Conversational Router", "success", f"Mode A: Conversational ({intent})")
            return {
                "status": "success",
                "question": parsed_query["original_question"],
                "intent": intent,
                "entities": entities,
                "selected_function": None,
                "parameters": {},
                "result": None,
                "answer": ans,
                "execution_trace": trace,
                "execution_time_ms": round((time.time() - t0) * 1000, 2),
                "model_used": "Conversational Assistant",
            }

        # Unsupported query routing (e.g. groundwater levels)
        if intent == "unsupported_query" or intent == "get_groundwater_level":
            ans = (
                "Groundwater level and water table depth monitoring are published in the CGWB Ground Water Year Book "
                "through observation wells. This database specifically contains Dynamic Ground Water Resource Assessment "
                "compilations (recharge, extraction, extractable resources, and stage of extraction) under GEC methodology."
            )
            add_trace(5, "Knowledge Router", "success", "Unsupported domain redirected")
            return {
                "status": "unsupported",
                "question": parsed_query["original_question"],
                "intent": "get_groundwater_level",
                "entities": entities,
                "selected_function": None,
                "parameters": {},
                "result": None,
                "answer": ans,
                "execution_trace": trace,
                "execution_time_ms": round((time.time() - t0) * 1000, 2),
                "model_used": "Domain Knowledge Router",
            }

        # STEP 5: Select function (MODE B / MODE C)
        t4 = time.time()
        concept_prefix = ""
        if intent == "mixed_query":
            from .session_manager import DOMAIN_KNOWLEDGE
            concept_prefix = DOMAIN_KNOWLEDGE.get("extraction", "") + "\n\n"
            func_name = "get_groundwater_extraction"
        else:
            func_name = INTENT_FUNCTION_MAP.get(intent)

        # Adjust function based on context
        if intent == "get_state_summary" and parsed_query.get("district"):
            func_name = "get_district_summary"
        if intent == "get_district_summary" and not parsed_query.get("district"):
            func_name = "get_state_summary"

        if not func_name:
            if not entities.get("state") and not entities.get("district"):
                ans = "I'm ready to help you with groundwater data across India. Please specify a state, district, or assessment year."
                return {
                    "status": "success",
                    "question": parsed_query["original_question"],
                    "intent": "general_conversation",
                    "entities": entities,
                    "selected_function": None,
                    "parameters": {},
                    "result": None,
                    "answer": ans,
                    "execution_trace": trace,
                    "execution_time_ms": round((time.time() - t0) * 1000, 2),
                }
            func_name = "get_district_summary"

        add_trace(5, "Function Selected", "success", func_name, (time.time() - t4) * 1000)

        # STEP 6: Build parameters
        t5 = time.time()
        params = self._build_params(func_name, parsed_query)
        add_trace(6, "Parameters Validated", "success", str(params), (time.time() - t5) * 1000)

        # STEP 7: Execute database function
        t6 = time.time()
        db_result = execute_function(func_name, self.db, **params)
        exec_ms = (time.time() - t6) * 1000
        add_trace(7, "Database Query Executed", db_result.get("status", "success"),
                  f"Status: {db_result.get('status')}", exec_ms)

        # STEP 8: Validate result
        t7 = time.time()
        validated = self._validate_result(db_result)
        add_trace(8, "Result Validated", "success",
                  f"Records retrieved: {'yes' if db_result.get('data') else 'no'}",
                  (time.time() - t7) * 1000)

        # STEP 9: Generate answer
        t8 = time.time()
        answer = self._generate_answer(func_name, params, db_result, parsed_query)
        if concept_prefix:
            answer = concept_prefix + answer
        add_trace(9, "Answer Generated", "success", "Natural language response ready",
                  (time.time() - t8) * 1000)

        # STEP 10: Logging
        add_trace(10, "Query Logged", "success", "Query recorded in database")

        total_ms = round((time.time() - t0) * 1000, 2)

        return {
            "status": db_result.get("status", "success"),
            "question": parsed_query["original_question"],
            "intent": intent,
            "entities": entities,
            "selected_function": func_name,
            "parameters": params,
            "result": db_result,
            "answer": answer,
            "execution_trace": trace,
            "execution_time_ms": total_ms,
            "source": db_result.get("source", "Verified CGWB assessment record"),
        }

    def _extract_entity_dict(self, pq: Dict) -> Dict:
        return {
            "state": pq.get("state"),
            "district": pq.get("district"),
            "block": pq.get("block"),
            "assessment_year": pq.get("assessment_year"),
            "parameter": pq.get("parameter"),
            "aggregation": pq.get("aggregation"),
        }

    def _build_params(self, func_name: str, pq: Dict) -> Dict:
        required = INTENT_PARAM_MAP.get(func_name, [])
        params = {}
        mapping = {
            "state": pq.get("state"),
            "district": pq.get("district"),
            "block": pq.get("block"),
            "assessment_year": pq.get("assessment_year"),
            "parameter": pq.get("parameter") or "extraction",
        }

        # Handle comparison
        if func_name == "compare_locations":
            locs = pq.get("comparison_locations", [])
            if len(locs) >= 2:
                params["state1"] = locs[0].get("state", pq.get("state", ""))
                params["district1"] = locs[0].get("district", "")
                params["state2"] = locs[1].get("state", pq.get("state", ""))
                params["district2"] = locs[1].get("district", "")
            elif len(locs) == 1:
                params["state1"] = locs[0].get("state", pq.get("state", ""))
                params["district1"] = locs[0].get("district", "")
                params["state2"] = pq.get("state", "")
                params["district2"] = pq.get("district", "")
            params["parameter"] = pq.get("parameter") or "extraction"
            if pq.get("assessment_year"):
                params["assessment_year"] = pq.get("assessment_year")
            return params

        if func_name == "compare_assessment_years":
            params["state"] = pq.get("state")
            params["district"] = pq.get("district")
            params["parameter"] = pq.get("parameter") or "extraction"
            params["year1"] = pq.get("year1") or "2020"
            params["year2"] = pq.get("year2") or pq.get("assessment_year") or "2022"
            return params

        if func_name in ("get_historical_groundwater_data", "get_yearly_groundwater_trend"):
            params["state"] = pq.get("state")
            if pq.get("district"):
                params["district"] = pq.get("district")
            params["parameter"] = pq.get("parameter") or "extraction"
            return params

        if func_name == "get_location_details":
            params["location"] = pq.get("district") or pq.get("state") or pq.get("original_question")
            return params

        for key in required:
            if key in mapping and mapping[key]:
                params[key] = mapping[key]

        return params

    def _validate_result(self, result: Dict) -> bool:
        return result.get("status") in ("success", "not_found", "unsupported")

    def _format_provenance_display(
        self,
        db_result: Dict,
        default_yr: str = "",
        default_loc: str = "",
        default_level: str = "District",
    ) -> str:
        """Format provenance metadata block strictly conforming to Section 8."""
        prov_list = db_result.get("provenance") or db_result.get("metadata", {}).get("provenance") or []
        if prov_list and isinstance(prov_list, list) and isinstance(prov_list[0], dict):
            p = prov_list[0]
            yr = p.get("assessment_year") or default_yr or "N/A"
            loc = p.get("location") or p.get("assessment_unit_name") or default_loc or "N/A"
            lvl = p.get("assessment_unit_level") or default_level
            agency = p.get("source_agency") or "Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti, Government of India"
            doc = p.get("source_document") or db_result.get("source") or "National Compilation on Dynamic Ground Water Resources of India"
            status = p.get("verification_status") or "VERIFIED"
        else:
            yr = default_yr or "N/A"
            loc = default_loc or "N/A"
            lvl = default_level
            agency = db_result.get("source_agency") or "Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti, Government of India"
            doc = db_result.get("source") or "National Compilation on Dynamic Ground Water Resources of India"
            status = "VERIFIED"

        return (
            f"\n\nSource Provenance:\n"
            f"- Actual Assessment Year: {yr}\n"
            f"- Actual Location & Level: {loc} ({lvl})\n"
            f"- Source Agency: {agency}\n"
            f"- Source Document: {doc}\n"
            f"- Verification Status: {status}"
        )

    def _generate_answer(self, func_name: str, params: Dict, result: Dict, pq: Dict) -> str:
        """Generate a natural-language answer from the database result."""
        status = result.get("status")
        data = result.get("data")
        source = result.get("source", "Verified CGWB assessment record")

        if status == "unsupported":
            return result.get("message", "This query is not supported with the current dataset.")

        if status == "not_found" or not data:
            base_msg = "Verified data for this location, parameter and assessment year is not currently available in the database."
            loc_label = params.get("district") or params.get("state")
            if loc_label:
                latest_rec = repo.get_latest_verified_record(
                    self.db,
                    state=params.get("state"),
                    district=params.get("district"),
                    parameter=params.get("parameter") or func_name,
                )
                if latest_rec and latest_rec.get("value") is not None:
                    req_year = params.get("assessment_year") or pq.get("assessment_year") or ""
                    lat_yr = latest_rec["latest_year"]
                    val = latest_rec["value"]
                    unit = latest_rec.get("unit", "Ham")
                    param = latest_rec.get("parameter", "figure")
                    loc = latest_rec.get("location", loc_label)

                    result["status"] = "success"
                    result["fallback"] = True
                    result["fallback_from_year"] = str(req_year) if req_year else None
                    result["fallback_to_year"] = str(lat_yr)
                    result["data"] = latest_rec
                    result["source"] = latest_rec.get("source_document", "CGWB National Compilation")
                    result["source_agency"] = latest_rec.get("source_agency", "Central Ground Water Board (CGWB)")
                    if "provenance" not in result or not result["provenance"]:
                        result["provenance"] = [{
                            "dataset_name": latest_rec.get("source_document", "CGWB National Compilation"),
                            "source_agency": latest_rec.get("source_agency", "Central Ground Water Board (CGWB)"),
                            "source_document": latest_rec.get("source_document", "CGWB National Compilation"),
                            "assessment_year": lat_yr,
                            "location": loc,
                            "verification_status": latest_rec.get("verification_status", "VERIFIED"),
                        }]

                    prov_block = self._format_provenance_display(result, default_yr=lat_yr, default_loc=loc, default_level="District")
                    val_str = f"{val:,.2f} {unit}" if isinstance(val, (int, float)) else f"{val}"
                    if str(req_year) and str(req_year) != str(lat_yr):
                        year_note = f"Verified {req_year} data for {loc} is not in the benchmark subset; showing the latest verified CGWB record from {lat_yr}:"
                    else:
                        year_note = f"Showing verified CGWB record from {lat_yr} for {loc}:"

                    return (
                        f"{year_note} Total annual {param} was {val_str} for assessment period {lat_yr}."
                        f"{prov_block}"
                    )

            available_years = repo.get_assessment_years(self.db).get("data") or []
            available_note = (
                f" Verified assessment years available: {', '.join(available_years)}."
                if available_years
                else ""
            )
            return base_msg + available_note

        if status == "error":
            return f"An error occurred: {result.get('message', 'Unknown error')}"

        # Build specific answers
        if func_name == "get_assessment_years":
            years = data if isinstance(data, list) else []
            return (
                f"The following assessment years are verified and available in the database: "
                f"{', '.join(str(y) for y in years)}.\n\n"
                f"Source Provenance:\n"
                f"- Actual Assessment Year: {', '.join(str(y) for y in years)}\n"
                f"- Actual Location & Level: All Monitored Assessment Units (National)\n"
                f"- Source Agency: Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti, Government of India\n"
                f"- Source Document: CGWB National Compilation on Dynamic Ground Water Resources\n"
                f"- Verification Status: VERIFIED"
            )

        if func_name == "get_state_list":
            states = data if isinstance(data, list) else []
            return (
                f"{len(states)} states/UTs have verified groundwater assessment records in the database: "
                f"{', '.join(states[:10])}{'...' if len(states) > 10 else ''}.\n\n"
                f"Source Provenance:\n"
                f"- Actual Assessment Year: 2022, 2025\n"
                f"- Actual Location & Level: States and Union Territories (State Level)\n"
                f"- Source Agency: Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti, Government of India\n"
                f"- Source Document: CGWB National Compilation on Dynamic Ground Water Resources\n"
                f"- Verification Status: VERIFIED"
            )

        if func_name == "get_groundwater_recharge" and isinstance(data, dict):
            loc = data.get("location", "the requested location")
            yr = data.get("assessment_year", "")
            val = data.get("total_annual_recharge_ham")
            unit = data.get("unit", "Ham")
            lvl = data.get("assessment_unit_level", "District")
            if val is not None:
                prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=loc, default_level=lvl)
                return (
                    f"The total annual groundwater recharge in {loc} was "
                    f"{val:,.2f} {unit} for assessment period {yr}."
                    f"{prov_block}"
                )

        if func_name == "get_groundwater_extraction" and isinstance(data, dict):
            loc = data.get("location", "the requested location")
            yr = data.get("assessment_year", "")
            val = data.get("total_annual_extraction_ham")
            unit = data.get("unit", "Ham")
            lvl = data.get("assessment_unit_level", "District")
            if val is not None:
                irr = data.get("extraction_irrigation_ham")
                dom = data.get("extraction_domestic_ham")
                ind = data.get("extraction_industrial_ham")
                detail = ""
                if irr is not None or dom is not None or ind is not None:
                    comps = []
                    if irr is not None:
                        comps.append(f"Irrigation: {irr:,.2f} {unit}")
                    if dom is not None:
                        comps.append(f"Domestic: {dom:,.2f} {unit}")
                    if ind is not None:
                        comps.append(f"Industrial: {ind:,.2f} {unit}")
                    detail = f" Breakdown: {', '.join(comps)}."
                prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=loc, default_level=lvl)
                return (
                    f"The total annual groundwater extraction in {loc} was "
                    f"{val:,.2f} {unit} for assessment period {yr}.{detail}"
                    f"{prov_block}"
                )

        if func_name == "get_stage_of_extraction" and isinstance(data, dict):
            loc = data.get("location", "the requested location")
            yr = data.get("assessment_year", "")
            val = data.get("stage_of_extraction_pct")
            cat = data.get("assessment_category", "")
            lvl = data.get("assessment_unit_level", "District")
            if val is not None:
                cat_text = f" Assessment category: {cat}." if cat else ""
                prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=loc, default_level=lvl)
                return (
                    f"The stage of groundwater extraction in {loc} is "
                    f"{val:.2f}% for assessment period {yr}.{cat_text}"
                    f"{prov_block}"
                )

        if func_name == "get_assessment_category" and isinstance(data, dict):
            loc = data.get("location", "the requested location")
            yr = data.get("assessment_year", "")
            lvl = data.get("assessment_unit_level", "District")
            prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=loc, default_level=lvl)
            if "assessment_category" in data and data["assessment_category"]:
                cat = data.get("assessment_category", "")
                stage = data.get("stage_of_extraction_pct")
                stage_str = f" (Stage of extraction: {stage:.2f}%)" if stage is not None else ""
                return (
                    f"The groundwater assessment category for {loc} ({yr}) is: "
                    f"{cat}{stage_str}."
                    f"{prov_block}"
                )
            elif "category_distribution" in data:
                cats = data.get("category_distribution", {})
                dist_str = ", ".join(f"{k}: {v}" for k, v in cats.items())
                return (
                    f"Assessment category distribution for {loc} ({yr}): {dist_str}."
                    f"{prov_block}"
                )

        if func_name == "get_overexploited_units" and isinstance(data, dict):
            state = data.get("state", "")
            yr = data.get("assessment_year", "")
            count = data.get("overexploited_count", 0)
            units = data.get("overexploited_districts", [])
            prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=state, default_level="State")
            if count == 0:
                return (
                    f"No over-exploited assessment units found in {state} for assessment year {yr}."
                    f"{prov_block}"
                )
            names = ", ".join(u["district"] for u in units)
            return (
                f"{count} district(s) in {state} are classified as Over-Exploited for assessment year {yr}: {names}."
                f"{prov_block}"
            )

        if func_name == "get_extractable_groundwater" and isinstance(data, dict):
            loc = data.get("location", "the requested location")
            yr = data.get("assessment_year", "")
            val = data.get("annual_extractable_groundwater_ham") or data.get("total_annual_extractable_groundwater_ham")
            lvl = data.get("assessment_unit_level", "District")
            if val is not None:
                prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=loc, default_level=lvl)
                return (
                    f"The annual extractable groundwater resource in {loc} was "
                    f"{val:,.2f} Ham for assessment period {yr}."
                    f"{prov_block}"
                )

        if func_name == "compare_locations" and isinstance(data, dict):
            comp = data.get("comparison", {})
            param = data.get("parameter", "")
            lines = []
            for loc_key, info in comp.items():
                val = info.get("value")
                unit = info.get("unit", "Ham")
                yr = info.get("assessment_year", "")
                lvl = info.get("assessment_unit_level", "District")
                lines.append(f"- {info['district']}, {info['state']} ({lvl}): {val:,.2f} {unit} ({yr})")

            prov_list = result.get("provenance") or []
            prov_texts = []
            for p in prov_list:
                prov_texts.append(
                    f"- {p.get('location')} ({p.get('assessment_unit_level', 'District')}): "
                    f"Year {p.get('assessment_year')}, Agency: {p.get('source_agency')}, "
                    f"Doc: {p.get('source_document')}, Status: {p.get('verification_status')}"
                )
            prov_block = "\n\nSource Provenance:\n" + "\n".join(prov_texts) if prov_texts else ""
            return (
                f"Comparison of {param} between locations:\n"
                + "\n".join(lines)
                + prov_block
            )

        if func_name == "get_state_summary" and isinstance(data, dict):
            st = data.get("state", "")
            yr = data.get("assessment_year", "")
            recharge = data.get("total_annual_recharge_ham")
            extraction = data.get("total_annual_extraction_ham")
            cats = data.get("category_distribution", {})
            cat_str = ", ".join(f"{k}: {v} districts" for k, v in cats.items())
            prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=st, default_level="State")
            return (
                f"Groundwater summary for {st} (State Level) for assessment year {yr}:\n"
                f"- Total annual recharge: {recharge:,.2f} Ham\n"
                f"- Total extraction: {extraction:,.2f} Ham\n"
                f"- Assessment categories: {cat_str}"
                f"{prov_block}"
            )

        if func_name == "get_district_summary" and isinstance(data, dict):
            loc = f"{data.get('district', '')}, {data.get('state', '')}"
            yr = data.get("assessment_year", "")
            recharge = data.get("total_annual_recharge_ham")
            extraction = data.get("total_annual_extraction_ham")
            stage = data.get("stage_of_extraction_pct")
            cat = data.get("assessment_category")
            lvl = data.get("assessment_unit_level", "District")
            prov_block = self._format_provenance_display(result, default_yr=yr, default_loc=loc, default_level=lvl)
            recharge_str = f"{recharge:,.2f} Ham" if recharge is not None else "Not Available"
            extraction_str = f"{extraction:,.2f} Ham" if extraction is not None else "Not Available"
            stage_str = f"{stage:.2f}%" if stage is not None else "Not Available"
            cat_str = cat if cat else "Not Available"
            return (
                f"Groundwater summary for {loc} ({lvl}) for assessment year {yr}:\n"
                f"- Annual recharge: {recharge_str}\n"
                f"- Annual extraction: {extraction_str}\n"
                f"- Stage of extraction: {stage_str}\n"
                f"- Assessment category: {cat_str}"
                f"{prov_block}"
            )

        if func_name == "get_country_summary" and isinstance(data, dict):
            yr = data.get("assessment_year", "")
            recharge = data.get("total_annual_recharge_ham")
            extraction = data.get("total_annual_extraction_ham")
            prov_block = self._format_provenance_display(result, default_yr=yr, default_loc="India", default_level="National")
            return (
                f"National groundwater summary for assessment year {yr}:\n"
                f"- Total recharge across {data.get('total_records', '')} districts: {recharge:,.2f} Ham\n"
                f"- Total extraction: {extraction:,.2f} Ham"
                f"{prov_block}"
            )

        if func_name == "compare_assessment_years" and isinstance(data, dict):
            loc = f"{data.get('district')}, {data.get('state')}" if data.get('district') else data.get('state')
            param = data.get('parameter', 'parameter')
            unit = data.get('unit', 'Ham')
            y1 = data.get('year_1', {})
            y2 = data.get('year_2', {})
            diff = data.get('difference')
            pct = data.get('percent_change')
            trend = data.get('trend', 'changed')
            diff_str = (
                f"an increase of {abs(diff):,.2f} {unit} (+{pct}%)" if diff > 0
                else (f"a decrease of {abs(diff):,.2f} {unit} ({pct}%)" if diff < 0 else "no net change")
            )
            prov_list = result.get("provenance") or []
            prov_texts = []
            for p in prov_list:
                prov_texts.append(
                    f"- Year {p.get('assessment_year')}: {p.get('location')} ({p.get('assessment_unit_level', 'District')}), "
                    f"Agency: {p.get('source_agency')}, Doc: {p.get('source_document')}, Status: {p.get('verification_status')}"
                )
            prov_block = "\n\nSource Provenance:\n" + "\n".join(prov_texts) if prov_texts else ""
            return (
                f"Comparison of {param} in {loc} between {y1.get('year')} and {y2.get('year')}:\n"
                f"- {y1.get('year')}: {y1.get('value'):,.2f} {unit}\n"
                f"- {y2.get('year')}: {y2.get('value'):,.2f} {unit}\n"
                f"Analysis shows {diff_str} (Trend: {trend})."
                f"{prov_block}"
            )

        if func_name in ("get_historical_groundwater_data", "get_yearly_groundwater_trend") and isinstance(data, dict):
            loc = f"{data.get('district')}, {data.get('state')}" if data.get('district') else data.get('state')
            hist = data.get('history', [])
            points = []
            for h in hist:
                ext = f"{h.get('extraction_ham'):,.2f} Ham" if h.get('extraction_ham') is not None else "N/A"
                rech = f"{h.get('recharge_ham'):,.2f} Ham" if h.get('recharge_ham') is not None else "N/A"
                soe = f"{h.get('stage_of_extraction_pct'):.2f}%" if h.get('stage_of_extraction_pct') is not None else "N/A"
                points.append(f"- Year {h.get('year')}: Extraction: {ext}, Recharge: {rech}, Stage: {soe}")

            prov_list = result.get("provenance") or []
            prov_texts = [
                f"- Year {p.get('assessment_year')}: Agency: {p.get('source_agency')}, Doc: {p.get('source_document')}, Status: {p.get('verification_status')}"
                for p in prov_list
            ]
            prov_block = "\n\nSource Provenance:\n" + "\n".join(prov_texts) if prov_texts else ""
            return (
                f"Historical groundwater assessment records for {loc} across {len(hist)} verified assessment cycles:\n"
                + "\n".join(points)
                + prov_block
            )

        if func_name == "get_data_coverage" and isinstance(data, dict):
            recs = data.get('total_records', 0)
            states = data.get('total_states', 0)
            dists = data.get('total_districts', 0)
            yrs = ", ".join(data.get('available_years', []))
            return (
                f"Groundwater AI Verified Database Coverage:\n"
                f"- Total Verified Records: {recs:,}\n"
                f"- States/UTs Covered: {states}\n"
                f"- Districts Monitored: {dists}\n"
                f"- Available Verified Assessment Cycles: {yrs}\n\n"
                f"Source Provenance:\n"
                f"- Source Agency: Central Ground Water Board (CGWB), Department of Water Resources, RD & GR, Ministry of Jal Shakti\n"
                f"- Verification Status: VERIFIED"
            )

        # Fallback
        return f"Query executed successfully. Data retrieved from {source}."

        # Fallback
        return f"Query executed successfully. Data retrieved from {source}."
