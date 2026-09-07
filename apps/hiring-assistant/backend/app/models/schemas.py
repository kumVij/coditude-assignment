from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str
    description: str
    must_have_skills: str = ""
    screening_questions: str = ""  # one per line, e.g. "Notice period?\nCurrent CTC?"
    language: str = "ENGLISH"
    voice_persona: str = "NEHA"


class JobOut(BaseModel):
    id: str
    title: str
    description: str
    must_have_skills: str
    screening_questions: str
    language: str
    voice_persona: str
    hunar_agent_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateCreate(BaseModel):
    name: str
    mobile_number: str = Field(..., description="E.164 format, e.g. +919876543210")
    email: Optional[str] = None
    resume_notes: str = ""
    consent_obtained: bool = False


class ResumeOut(BaseModel):
    candidate_id: str
    skills: list[str]
    experience_years: Optional[float]
    extracted_text_length: int


class CandidateBulkCreate(BaseModel):
    candidates: list[CandidateCreate]


class CandidateOut(BaseModel):
    id: str
    name: str
    mobile_number: str
    email: Optional[str]
    resume_notes: str
    consent_obtained: bool

    class Config:
        from_attributes = True


class ScreeningCallOut(BaseModel):
    id: str
    hunar_call_id: Optional[str]
    candidate: CandidateOut
    status: str
    lifecycle_status: str
    recording_url: Optional[str]
    result: Optional[dict]
    duration_minutes: Optional[float]
    engagement_status: Optional[str]
    updated_at: datetime
    round_number: str

    class Config:
        from_attributes = True


class StartScreeningRequest(BaseModel):
    candidate_ids: Optional[list[str]] = None  # None => screen all candidates on the job
    max_retry_count: int = 1
    retry_interval_hours: int = 6
    round_number: int = Field(default=1, ge=1, le=2)


class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=12)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ScreeningBatchOut(BaseModel):
    id: str
    status: str
    candidate_count: str
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScreeningEnqueueOut(BaseModel):
    batch_id: str
    status: str
    candidate_count: int

