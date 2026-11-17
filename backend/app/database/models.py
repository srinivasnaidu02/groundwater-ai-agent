"""SQLAlchemy database models for Groundwater AI Agent."""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


class State(Base):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    districts = relationship("District", back_populates="state")


class District(Base):
    __tablename__ = "districts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    state = relationship("State", back_populates="districts")
    groundwater_records = relationship("GroundwaterResource", back_populates="district")


class Block(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AssessmentYear(Base):
    __tablename__ = "assessment_years"
    id = Column(Integer, primary_key=True, index=True)
    year = Column(String(20), unique=True, nullable=False, index=True)
    period_description = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SourceDataset(Base):
    __tablename__ = "source_datasets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    source_url = Column(Text, nullable=True)
    download_date = Column(DateTime, nullable=True)
    assessment_period = Column(String(50), nullable=True)
    publication_year = Column(String(4), nullable=True)
    data_year = Column(String(4), nullable=True)
    source_agency = Column(String(200), nullable=True)
    original_filename = Column(String(200), nullable=True)
    data_format = Column(String(50), nullable=True)
    unit = Column(String(20), nullable=True)
    geographic_coverage = Column(String(200), nullable=True)
    num_records = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    verification_status = Column(String(20), default="UNVERIFIED", nullable=False)
    verification_evidence = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GeographicMaster(Base):
    """Dynamic geographical knowledge base mapping variations, aliases, and state bindings."""
    __tablename__ = "geographic_master"
    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String(150), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False) # 'state', 'district', 'block'
    state_name = Column(String(100), nullable=False, index=True)
    aliases = Column(Text, nullable=True) # Comma-separated alternative spellings
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GroundwaterResource(Base):
    __tablename__ = "groundwater_resources"
    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    block_id = Column(Integer, ForeignKey("blocks.id"), nullable=True)
    assessment_year_id = Column(Integer, ForeignKey("assessment_years.id"), nullable=False)
    source_dataset_id = Column(Integer, ForeignKey("source_datasets.id"), nullable=True)

    # Recharge fields (in Ham)
    monsoon_recharge_rainfall = Column(Float, nullable=True)
    monsoon_recharge_other = Column(Float, nullable=True)
    non_monsoon_recharge_rainfall = Column(Float, nullable=True)
    non_monsoon_recharge_other = Column(Float, nullable=True)
    total_annual_recharge = Column(Float, nullable=True)
    total_natural_discharges = Column(Float, nullable=True)

    # Extractable resources
    annual_extractable_groundwater = Column(Float, nullable=True)

    # Extraction fields
    annual_extraction_irrigation = Column(Float, nullable=True)
    annual_extraction_industrial = Column(Float, nullable=True)
    annual_extraction_domestic = Column(Float, nullable=True)
    total_annual_extraction = Column(Float, nullable=True)

    # Net availability
    gw_allocation_domestic_future = Column(Float, nullable=True)
    net_gw_availability_future = Column(Float, nullable=True)
    stage_of_extraction_pct = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_status = Column(String(20), default="UNVERIFIED", nullable=False)  # 'VERIFIED', 'UNVERIFIED', 'REJECTED', 'SYNTHETIC'
    verification_evidence = Column(Text, nullable=True)
    source_page_table = Column(String(200), nullable=True)
    assessment_unit_name = Column(String(150), nullable=True)
    assessment_unit_level = Column(String(50), default="District", nullable=True)

    # Category
    assessment_category = Column(String(50), nullable=True)
    unit = Column(String(20), default="Ham")

    # Authoritative Source & Provenance
    source_agency = Column(String(200), default="CGWB", nullable=True)
    source_document = Column(String(250), nullable=True)
    source_url = Column(Text, nullable=True)
    original_filename = Column(String(250), nullable=True)
    sha256_checksum = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    state = relationship("State")
    district = relationship("District", back_populates="groundwater_records")
    assessment_year = relationship("AssessmentYear")
    source_dataset = relationship("SourceDataset")


class AssessmentUnit(Base):
    """Sub-district administrative assessment entity (Taluk, Block, Mandal, Firka, Watershed)."""
    __tablename__ = "assessment_units"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    unit_type = Column(String(50), default="Assessment Unit", nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    state = relationship("State")
    district = relationship("District")


class AssessmentUnitCategory(Base):
    """Categorisation of individual assessment units (Safe, Semi-Critical, Critical, Over-Exploited, Saline)."""
    __tablename__ = "assessment_unit_categories"
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    assessment_unit_id = Column(Integer, ForeignKey("assessment_units.id"), nullable=True)
    unit_name = Column(String(150), nullable=False, index=True)
    district_name = Column(String(150), nullable=True, index=True)
    state_name = Column(String(100), nullable=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    source_file = Column(String(250), nullable=True)
    source_url = Column(Text, nullable=True)
    verification_status = Column(String(50), default="UNVERIFIED", nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    state = relationship("State")
    district = relationship("District")
    assessment_unit = relationship("AssessmentUnit")


class StateGroundwaterResource(Base):
    """State-level macro volumetric groundwater resource compilations (in Bcm)."""
    __tablename__ = "state_groundwater_resources"
    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=True)
    state_name = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    annual_recharge_bcm = Column(Float, nullable=True)
    natural_discharges_bcm = Column(Float, nullable=True)
    extractable_resources_bcm = Column(Float, nullable=True)
    irrigation_extraction_bcm = Column(Float, nullable=True)
    industrial_extraction_bcm = Column(Float, nullable=True)
    domestic_extraction_bcm = Column(Float, nullable=True)
    total_extraction_bcm = Column(Float, nullable=True)
    net_future_availability_bcm = Column(Float, nullable=True)
    stage_of_extraction_pct = Column(Float, nullable=True)
    unit = Column(String(20), default="Bcm")
    source_agency = Column(String(200), default="CGWB / IN-GRES", nullable=True)
    source_file = Column(String(250), nullable=True)
    source_url = Column(Text, nullable=True)
    verification_status = Column(String(50), default="UNVERIFIED", nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    state = relationship("State")


class SourceDocument(Base):
    """Primary publications, reports, and downloaded archives with checksum tracking."""
    __tablename__ = "source_documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(250), nullable=False)
    agency = Column(String(200), default="CGWB", nullable=True)
    publication_year = Column(Integer, nullable=True)
    assessment_year = Column(Integer, nullable=True)
    document_url = Column(Text, nullable=True)
    pdf_url = Column(Text, nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    verification_status = Column(String(50), default="UNVERIFIED", nullable=False)
    verification_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ImportAuditLog(Base):
    """Audit ledger recording batch ingestion runs, counts, and validation checks."""
    __tablename__ = "import_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    dataset_name = Column(String(200), nullable=False)
    source_file = Column(String(250), nullable=True)
    sha256 = Column(String(64), nullable=True)
    assessment_year = Column(Integer, nullable=True)
    total_records = Column(Integer, default=0)
    verified_records = Column(Integer, default=0)
    unverified_records = Column(Integer, default=0)
    rejected_records = Column(Integer, default=0)
    synthetic_records = Column(Integer, default=0)
    audit_report_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConversationSession(Base):
    """Session entity tracking conversational context across turns."""
    __tablename__ = "conversation_sessions"
    session_id = Column(String(100), primary_key=True, index=True)
    active_context = Column(Text, nullable=True)
    active_state = Column(String(100), nullable=True)
    active_district = Column(String(150), nullable=True)
    active_year = Column(String(20), nullable=True)
    active_parameter = Column(String(100), nullable=True)
    last_intent = Column(String(100), nullable=True)
    last_function = Column(String(100), nullable=True)
    last_result_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")


class ConversationMessage(Base):
    """Audit log of individual chat exchanges inside a session."""
    __tablename__ = "conversation_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), ForeignKey("conversation_sessions.session_id"), nullable=False, index=True)
    role = Column(String(20), nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    entities_json = Column(Text, nullable=True)
    function_called = Column(String(100), nullable=True)
    parameters_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    execution_trace_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session = relationship("ConversationSession", back_populates="messages")


class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    intent = Column(String(100), nullable=True)
    entities = Column(Text, nullable=True)
    function_called = Column(String(100), nullable=True)
    parameters = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    response_text = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(String(50), nullable=False)
    input_question = Column(Text, nullable=False)
    expected_intent = Column(String(100), nullable=True)
    actual_intent = Column(String(100), nullable=True)
    intent_correct = Column(Boolean, nullable=True)
    expected_function = Column(String(100), nullable=True)
    actual_function = Column(String(100), nullable=True)
    function_correct = Column(Boolean, nullable=True)
    expected_status = Column(String(50), nullable=True)
    actual_status = Column(String(50), nullable=True)
    status_correct = Column(Boolean, nullable=True)
    entity_extraction_score = Column(Float, nullable=True)
    end_to_end_correct = Column(Boolean, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    error_category = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
