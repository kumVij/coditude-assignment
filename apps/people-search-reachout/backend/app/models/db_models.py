import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class SearchRequest(Base):
    """One 'paste a JD, search for people' session."""

    __tablename__ = "search_requests"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_title = Column(String, nullable=False)
    job_description = Column(Text, nullable=False)
    location_query = Column(String, default="")
    parsed_titles = Column(JSON, default=list)  # candidate job-title keywords derived from JD
    parsed_skills = Column(JSON, default=list)
    hunar_agent_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidates = relationship(
        "SourcedCandidate", back_populates="search", cascade="all, delete-orphan"
    )


class SourcedCandidate(Base):
    """A person returned by the people-search API for a given search request."""

    __tablename__ = "sourced_candidates"

    id = Column(String, primary_key=True, default=gen_uuid)
    search_id = Column(String, ForeignKey("search_requests.id"), nullable=False)
    full_name = Column(String, nullable=False)
    job_title = Column(String, default="")
    company = Column(String, default="")
    location = Column(String, default="")
    linkedin_url = Column(String, default="")
    email = Column(String, default="")
    mobile_number = Column(String, default="")  # E.164; may be blank if source has no phone
    source = Column(String, default="mock")  # "pdl" | "mock"
    raw_data = Column(JSON, default=dict)
    selected_for_reachout = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    search = relationship("SearchRequest", back_populates="candidates")
    calls = relationship("ReachoutCall", back_populates="candidate", cascade="all, delete-orphan")


class ReachoutCall(Base):
    __tablename__ = "reachout_calls"

    id = Column(String, primary_key=True, default=gen_uuid)
    hunar_call_id = Column(String, nullable=True, index=True)
    candidate_id = Column(String, ForeignKey("sourced_candidates.id"), nullable=False)
    search_id = Column(String, ForeignKey("search_requests.id"), nullable=False)
    status = Column(String, default="NOT_STARTED")
    lifecycle_status = Column(String, default="NOT_STARTED")
    recording_url = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    engagement_status = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("SourcedCandidate", back_populates="calls")
