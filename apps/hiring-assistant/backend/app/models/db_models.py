import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    must_have_skills = Column(Text, default="")
    screening_questions = Column(Text, default="")  # newline separated, optional recruiter input
    language = Column(String, default="ENGLISH")
    voice_persona = Column(String, default="NEHA")
    hunar_agent_id = Column(String, nullable=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidates = relationship("Candidate", back_populates="job", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    name = Column(String, nullable=False)
    mobile_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    mobile_number_encrypted = Column(Text, nullable=True)
    mobile_number_hash = Column(String, nullable=True, index=True)
    email_encrypted = Column(Text, nullable=True)
    consent_obtained = Column(String, nullable=False, default="false")
    consent_at = Column(DateTime, nullable=True)
    resume_notes = Column(Text, default="")
    resume_text_encrypted = Column(Text, nullable=True)
    resume_skills = Column(JSON, nullable=True)
    resume_experience_years = Column(Float, nullable=True)
    identity_hash = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="candidates")
    calls = relationship("ScreeningCall", back_populates="candidate", cascade="all, delete-orphan")


class ScreeningCall(Base):
    __tablename__ = "screening_calls"

    id = Column(String, primary_key=True, default=gen_uuid)
    hunar_call_id = Column(String, nullable=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="NOT_STARTED")
    lifecycle_status = Column(String, default="NOT_STARTED")
    recording_url = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    engagement_status = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    round_number = Column(String, nullable=False, default="1")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="calls")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(String, nullable=False, default="true")
    created_at = Column(DateTime, default=datetime.utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    event_key = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow)


class ScreeningBatch(Base):
    __tablename__ = "screening_batches"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String, nullable=False, default="QUEUED")
    candidate_count = Column(String, nullable=False, default="0")
    candidate_ids = Column(Text, nullable=False, default="[]")
    round_number = Column(String, nullable=False, default="1")
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeadLetter(Base):
    __tablename__ = "dead_letters"

    id = Column(String, primary_key=True, default=gen_uuid)
    batch_id = Column(String, ForeignKey("screening_batches.id"), nullable=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=True, index=True)
    reason = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    attempts = Column(String, nullable=False, default="1")
    created_at = Column(DateTime, default=datetime.utcnow)
