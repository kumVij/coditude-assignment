from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SearchCreate(BaseModel):
    job_title: str
    job_description: str
    location_query: str = ""


class SourcedCandidateOut(BaseModel):
    id: str
    full_name: str
    job_title: str
    company: str
    location: str
    linkedin_url: str
    email: str
    mobile_number: str
    source: str
    selected_for_reachout: bool

    class Config:
        from_attributes = True


class SearchOut(BaseModel):
    id: str
    job_title: str
    job_description: str
    location_query: str
    parsed_titles: list[str]
    parsed_skills: list[str]
    hunar_agent_id: Optional[str]
    created_at: datetime
    candidates: list[SourcedCandidateOut] = []

    class Config:
        from_attributes = True


class ReachoutCallOut(BaseModel):
    id: str
    hunar_call_id: Optional[str]
    candidate: SourcedCandidateOut
    status: str
    lifecycle_status: str
    recording_url: Optional[str]
    result: Optional[dict]
    duration_minutes: Optional[float]
    engagement_status: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class StartReachoutRequest(BaseModel):
    candidate_ids: list[str]
    max_retry_count: int = 1
    retry_interval_hours: int = 6
