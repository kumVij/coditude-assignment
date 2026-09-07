from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import db_models, schemas
from app.services.agent_builder import build_agent_config
from app.services.hunar_client import HunarAPIError, HunarClient
from app.services.hunar_dep import get_hunar_client
from app.services.security import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=schemas.JobOut)
def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    job = db_models.Job(**payload.model_dump(), owner_id=user.id if user else None)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[schemas.JobOut])
def list_jobs(db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    query = db.query(db_models.Job)
    if user:
        query = query.filter((db_models.Job.owner_id == user.id) | (db_models.Job.owner_id.is_(None)))
    return query.order_by(db_models.Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    job = db.get(db_models.Job, job_id)
    if not job or (user and job.owner_id != user.id):
        raise HTTPException(404, "Job not found")
    return job


@router.post("/{job_id}/provision-agent", response_model=schemas.JobOut)
def provision_agent(
    job_id: str,
    db: Session = Depends(get_db),
    hunar: HunarClient = Depends(get_hunar_client),
    user: db_models.User | None = Depends(get_current_user),
    round_number: int = 1,
):
    """Create (or re-create) the Hunar voice agent for this job's screening call."""
    job = db.get(db_models.Job, job_id)
    if not job or (user and job.owner_id != user.id):
        raise HTTPException(404, "Job not found")

    cfg = build_agent_config(job, round_number)
    try:
        if job.hunar_agent_id:
            agent = hunar.update_agent(
                job.hunar_agent_id,
                name=f"Screener - {job.title}"[:64],
                language=job.language,
                voice_persona=job.voice_persona,
                persona_name="Riya",
                **cfg,
            )
        else:
            agent = hunar.create_agent(
                name=f"Screener - {job.title}"[:64],
                language=job.language,
                voice_persona=job.voice_persona,
                persona_name="Riya",
                **cfg,
            )
    except HunarAPIError as e:
        raise HTTPException(e.status_code, f"Hunar API error: {e.message}")

    job.hunar_agent_id = agent["id"]
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    job = db.get(db_models.Job, job_id)
    if not job or (user and job.owner_id != user.id):
        raise HTTPException(404, "Job not found")
    db.delete(job)
    db.commit()
    return {"ok": True}
