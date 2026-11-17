"""
Comprehensive test suite for Natural LLM Conversation Routing, Chat UI logic,
and Multi-turn context resolution as requested in IMPROVEMENT TASK.
"""
import pytest
from sqlalchemy.orm import Session
from app.database.connection import get_sync_db
from app.nlp.intent_classifier import classify_intent
from app.nlp.query_parser import parse_question
from app.agent.session_manager import SessionManager
from app.agent.planner import QueryPlanner
from app.main import chat_endpoint, natural_language_query
from app.schemas.schemas import ChatRequest, QueryRequest


@pytest.fixture
def db_session():
    db = get_sync_db()
    try:
        yield db
    finally:
        db.close()


class TestMandatoryConversationQueries:
    """Tests the 10 mandatory inputs specified in the prompt."""

    def test_01_greeting_hii(self, db_session: Session):
        """1. 'hii' must be classified as greeting and handled conversationally without DB."""
        parsed = parse_question("hii")
        assert parsed["intent"] == "greeting"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="hii", session_id="test_sess_01")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert "Groundwater AI" in res.answer
        assert res.selected_function is None
        # Must NEVER return database-unavailable error
        assert "Verified data for this location" not in res.answer

    def test_02_greeting_hello(self, db_session: Session):
        """2. 'hello' must be handled conversationally."""
        parsed = parse_question("hello")
        assert parsed["intent"] == "greeting"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="hello", session_id="test_sess_02")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function is None
        assert "Verified data for this location" not in res.answer

    def test_03_small_talk_how_are_you(self, db_session: Session):
        """3. 'how are you?' must be handled conversationally."""
        parsed = parse_question("how are you?")
        assert parsed["intent"] == "general_conversation"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="how are you?", session_id="test_sess_03")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function is None
        assert "Verified data for this location" not in res.answer

    def test_04_small_talk_thank_you(self, db_session: Session):
        """4. 'thank you' must be handled politely and conversationally."""
        parsed = parse_question("thank you")
        assert parsed["intent"] == "general_conversation"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="thank you", session_id="test_sess_04")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function is None
        assert "welcome" in res.answer.lower()

    def test_05_capabilities_what_can_you_do(self, db_session: Session):
        """5. 'what can you do?' must explain capabilities without DB execution."""
        parsed = parse_question("what can you do?")
        assert parsed["intent"] == "general_conversation"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="what can you do?", session_id="test_sess_05")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function is None
        assert "Verified Database" in res.answer or "recharge" in res.answer.lower()

    def test_06_education_aquifer(self, db_session: Session):
        """6. 'what is an aquifer?' must provide hydrogeological education without DB call."""
        parsed = parse_question("what is an aquifer?")
        assert parsed["intent"] == "groundwater_education"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="what is an aquifer?", session_id="test_sess_06")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function is None
        assert "water-bearing" in res.answer.lower() or "permeable" in res.answer.lower()

    def test_07_education_recharge(self, db_session: Session):
        """7. 'explain groundwater recharge' must explain recharge mechanisms without DB call."""
        parsed = parse_question("explain groundwater recharge")
        assert parsed["intent"] == "groundwater_education"
        assert parsed["is_conversational"] is True

        req = ChatRequest(question="explain groundwater recharge", session_id="test_sess_07")
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function is None
        assert "monsoon" in res.answer.lower() or "infiltration" in res.answer.lower()

    def test_08_database_patna_2022_extraction(self, db_session: Session):
        """8. 'what is groundwater extraction in Patna in 2022?' must retrieve verified data."""
        sess_id = "test_multi_turn_session"
        req = ChatRequest(question="what is groundwater extraction in Patna in 2022?", session_id=sess_id)
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function == "get_groundwater_extraction"
        assert "174,600" in res.answer or "174600" in res.answer
        assert res.active_context.get("last_state") == "Bihar"
        assert res.active_context.get("last_district") == "Patna"
        assert res.active_context.get("last_year") == "2022"
        assert res.active_context.get("last_parameter") == "extraction"

    def test_09_followup_what_about_2025(self, db_session: Session):
        """9. 'what about 2025?' must retain Patna & extraction, and retrieve verified 2025 data."""
        sess_id = "test_multi_turn_session"
        # Turn 2: Follow-up with year 2025
        req = ChatRequest(question="what about 2025?", session_id=sess_id)
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function == "get_groundwater_extraction"
        # Must return the verified Patna 2025 extraction (59,747.83 Ham)
        assert "59,747.83" in res.answer or "59747.83" in res.answer
        assert res.active_context.get("last_year") == "2025"
        assert "2022" in res.active_context.get("recent_years", [])
        assert "2025" in res.active_context.get("recent_years", [])

    def test_10_followup_compare_both(self, db_session: Session):
        """10. 'compare both' must compare verified 2022 and 2025 records for Patna."""
        sess_id = "test_multi_turn_session"
        # Turn 3: Compare both years
        req = ChatRequest(question="compare both", session_id=sess_id)
        res = chat_endpoint(req, db_session)
        assert res.status == "success"
        assert res.selected_function == "compare_assessment_years"
        # Both years' figures must appear in comparison
        assert "2022" in res.answer
        assert "2025" in res.answer
        assert "Patna" in res.answer

    def test_11_mixed_query_education_plus_database(self, db_session: Session):
        """Mode C: Mixed question explaining concept and retrieving verified value."""
        q = "What is groundwater extraction, and what was its value in Patna in 2025?"
        req = QueryRequest(question=q)
        res = natural_language_query(req, db_session)
        assert res.status == "success"
        # Answer must contain both the conceptual explanation and the numerical record
        assert "extraction" in res.answer.lower()
        assert "59,747.83" in res.answer or "59747.83" in res.answer
        assert res.selected_function == "get_groundwater_extraction"

    def test_12_unverified_records_blocked(self, db_session: Session):
        """Blocked queries for unverified or unavailable records."""
        blocked_queries = [
            "What was the groundwater extraction in Patna in 2026?",
            "What was the extraction in Ludhiana in 2024?",
            "What was the extraction in Jalandhar in 2025?",
            "Show groundwater extraction for Bihar in 2021",
        ]
        for bq in blocked_queries:
            req = QueryRequest(question=bq)
            res = natural_language_query(req, db_session)
            assert "Verified data for this location, parameter and assessment year is not currently available" in res.answer

