from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import get_db
from app.models import db_models, schemas
from app.services.security import decrypt_pii, encrypt_pii, get_current_user, pii_hash
from app.services.resume_parser import extract_resume

router = APIRouter(prefix="/api/jobs/{job_id}/candidates", tags=["candidates"])


def _candidate_out(candidate: db_models.Candidate) -> schemas.CandidateOut:
    return schemas.CandidateOut(
        id=candidate.id,
        name=candidate.name,
        mobile_number=decrypt_pii(candidate.mobile_number_encrypted) or candidate.mobile_number,
        email=decrypt_pii(candidate.email_encrypted) if candidate.email_encrypted else candidate.email,
        resume_notes=candidate.resume_notes,
        consent_obtained=candidate.consent_obtained == "true",
    )


def _get_job_or_404(db: Session, job_id: str) -> db_models.Job:
    job = db.get(db_models.Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("", response_model=list[schemas.CandidateOut])
def add_candidates(job_id: str, payload: schemas.CandidateBulkCreate, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    job = _get_job_or_404(db, job_id)
    if user and job.owner_id != user.id:
        raise HTTPException(404, "Job not found")
    created = []
    for c in payload.candidates:
        data = c.model_dump()
        mobile = data.pop("mobile_number")
        email = data.pop("email", None)
        consent = data.pop("consent_obtained", False)
        normalized_identity = "".join(character for character in mobile if character.isdigit())[-10:]
        identity_hash = pii_hash(normalized_identity)
        duplicate = db.query(db_models.Candidate).filter(db_models.Candidate.identity_hash == identity_hash).first()
        if duplicate:
            raise HTTPException(409, "This candidate is already registered; use the existing candidate record")
        data["consent_obtained"] = "true" if consent else "false"
        data["consent_at"] = datetime.utcnow() if consent else None
        candidate = db_models.Candidate(
            job_id=job_id,
            mobile_number="",
            mobile_number_encrypted=encrypt_pii(mobile),
            mobile_number_hash=pii_hash(mobile),
            identity_hash=identity_hash,
            email=email,
            email_encrypted=encrypt_pii(email),
            **data,
        )
        db.add(candidate)
        created.append(candidate)
    db.commit()
    for c in created:
        db.refresh(c)
    return [_candidate_out(candidate) for candidate in created]


@router.get("", response_model=list[schemas.CandidateOut])
def list_candidates(job_id: str, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    job = _get_job_or_404(db, job_id)
    if user and job.owner_id != user.id:
        raise HTTPException(404, "Job not found")
    candidates = (
        db.query(db_models.Candidate)
        .filter(db_models.Candidate.job_id == job_id)
        .order_by(db_models.Candidate.created_at.desc())
        .all()
    )
    return [_candidate_out(candidate) for candidate in candidates]


@router.post("/{candidate_id}/resume", response_model=schemas.ResumeOut)
async def upload_resume(
    job_id: str,
    candidate_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: db_models.User | None = Depends(get_current_user),
):
    job = _get_job_or_404(db, job_id)
    candidate = db.get(db_models.Candidate, candidate_id)
    if not candidate or candidate.job_id != job_id or (user and job.owner_id != user.id):
        raise HTTPException(404, "Candidate not found")
    try:
        text, skills, experience = extract_resume(file.filename or "resume", await file.read())
    except ValueError as error:
        raise HTTPException(400, str(error))
    candidate.resume_text_encrypted = encrypt_pii(text)
    candidate.resume_skills = skills
    candidate.resume_experience_years = experience
    db.commit()
    return schemas.ResumeOut(candidate_id=candidate.id, skills=skills, experience_years=experience, extracted_text_length=len(text))


@router.post("/{candidate_id}/consent", response_model=schemas.CandidateOut)
def record_consent(job_id: str, candidate_id: str, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    job = _get_job_or_404(db, job_id)
    candidate = db.get(db_models.Candidate, candidate_id)
    if not candidate or candidate.job_id != job_id or (user and job.owner_id != user.id):
        raise HTTPException(404, "Candidate not found")
    candidate.consent_obtained = "true"
    candidate.consent_at = datetime.utcnow()
    db.commit()
    db.refresh(candidate)
    return _candidate_out(candidate)


@router.delete("/{candidate_id}")
def delete_candidate(job_id: str, candidate_id: str, db: Session = Depends(get_db), user: db_models.User | None = Depends(get_current_user)):
    candidate = db.get(db_models.Candidate, candidate_id)
    job = _get_job_or_404(db, job_id)
    if not candidate or candidate.job_id != job_id or (user and job.owner_id != user.id):
        raise HTTPException(404, "Candidate not found")
    db.delete(candidate)
    db.commit()
    return {"ok": True}
