import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import db_models, schemas
from app.services.hunar_client import HunarAPIError, HunarClient
from app.services.hunar_dep import get_hunar_client
from app.services.security import get_current_user
from app.services.rate_limit import enforce_rate_limit
from app.services.screening_queue import enqueue_screening

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["screening"])
logger = logging.getLogger(__name__)


def normalize_phone(value: str | None) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def phone_key(value: str | None) -> str:
    digits = normalize_phone(value)
    return digits[-10:] if len(digits) >= 10 else digits


@router.post("/screen", response_model=schemas.ScreeningEnqueueOut, status_code=202)
def start_screening(
    job_id: str,
    payload: schemas.StartScreeningRequest,
    db: Session = Depends(get_db),
    hunar: HunarClient = Depends(get_hunar_client),
    user: db_models.User | None = Depends(get_current_user),
    _: None = Depends(enforce_rate_limit),
):
    job = db.get(db_models.Job, job_id)
    if not job or (user and job.owner_id != user.id):
        raise HTTPException(404, "Job not found")
    if not job.hunar_agent_id:
        raise HTTPException(400, "Provision the Hunar agent for this job first (POST /provision-agent)")

    query = db.query(db_models.Candidate).filter(db_models.Candidate.job_id == job_id)
    if payload.candidate_ids:
        query = query.filter(db_models.Candidate.id.in_(payload.candidate_ids))
    candidates = query.all()
    if not candidates:
        raise HTTPException(400, "No candidates to screen")
    if any(candidate.consent_obtained != "true" for candidate in candidates):
        raise HTTPException(400, "Consent is required before placing screening calls")

    batch = db_models.ScreeningBatch(
        job_id=job_id,
        owner_id=user.id if user else job.owner_id,
        candidate_count=str(len(candidates)),
        candidate_ids=json.dumps([candidate.id for candidate in candidates]),
        round_number=str(payload.round_number),
        status="QUEUED",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    try:
        enqueue_screening(batch.id)
    except Exception as error:
        logger.exception("screening_enqueue_failed batch_id=%s", batch.id)
        batch.status = "DEAD_LETTER"
        batch.error = str(error)[:1000]
        db.add(db_models.DeadLetter(batch_id=batch.id, job_id=job_id, reason="QUEUE_UNAVAILABLE", payload={"message": str(error)[:1000]}))
        db.commit()
        raise HTTPException(503, "Screening queue is unavailable")
    return schemas.ScreeningEnqueueOut(batch_id=batch.id, status=batch.status, candidate_count=len(candidates))


@router.get("/calls", response_model=list[schemas.ScreeningCallOut])
def list_calls(
    job_id: str,
    db: Session = Depends(get_db),
    hunar: HunarClient = Depends(get_hunar_client),
    refresh: bool = False,
    user: db_models.User | None = Depends(get_current_user),
):
    """List all screening calls for a job. Pass ?refresh=true to poll Hunar for
    live status on calls that haven't reached a terminal state yet (fallback
    for when webhooks aren't reachable, e.g. local dev without a public URL)."""
    job = db.get(db_models.Job, job_id)
    if not job or (user and job.owner_id != user.id):
        raise HTTPException(404, "Job not found")
    calls = db.query(db_models.ScreeningCall).filter(db_models.ScreeningCall.job_id == job_id).all()

    if refresh:
        terminal = {"COMPLETED", "NOT_CONNECTED", "FAILED", "CANCELLED"}
        for call in calls:
            if call.status in terminal or not call.hunar_call_id:
                continue
            try:
                remote = hunar.get_call(call.hunar_call_id)
            except HunarAPIError:
                continue
            call.status = remote.get("status", call.status)
            call.lifecycle_status = remote.get("lifecycle_status", call.lifecycle_status)
            call.recording_url = remote.get("recording_url")
            call.result = remote.get("result")
            call.duration_minutes = remote.get("duration_minutes")
            call.engagement_status = remote.get("engagement_status")
        db.commit()

    return calls


@router.get("/screening-batches/{batch_id}", response_model=schemas.ScreeningBatchOut)
def get_screening_batch(
    job_id: str,
    batch_id: str,
    db: Session = Depends(get_db),
    user: db_models.User | None = Depends(get_current_user),
):
    job = db.get(db_models.Job, job_id)
    batch = db.get(db_models.ScreeningBatch, batch_id)
    if not job or not batch or batch.job_id != job_id or (user and job.owner_id != user.id):
        raise HTTPException(404, "Screening batch not found")
    return batch
