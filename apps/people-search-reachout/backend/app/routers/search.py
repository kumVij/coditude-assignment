from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import db_models, schemas
from app.services.jd_parser import parse_job_description
from app.services.pdl_client import PeopleSearchError, normalize_person, search_people

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=schemas.SearchOut)
def create_search(payload: schemas.SearchCreate, db: Session = Depends(get_db)):
    settings = get_settings()
    criteria = parse_job_description(payload.job_title, payload.job_description)

    search = db_models.SearchRequest(
        job_title=payload.job_title,
        job_description=payload.job_description,
        location_query=payload.location_query,
        parsed_titles=criteria["titles"],
        parsed_skills=criteria["skills"],
    )
    db.add(search)
    db.commit()
    db.refresh(search)

    try:
        raw_people = search_people(
            api_key=settings.pdl_api_key,
            mock_mode=settings.effective_mock_mode,
            titles=criteria["titles"],
            skills=criteria["skills"],
            location_query=payload.location_query,
            limit=10,
        )
    except PeopleSearchError as e:
        raise HTTPException(502, f"People search provider error: {e}")

    for raw in raw_people:
        normalized = normalize_person(raw)
        db.add(db_models.SourcedCandidate(search_id=search.id, **normalized))
    db.commit()
    db.refresh(search)
    return search


@router.get("/{search_id}", response_model=schemas.SearchOut)
def get_search(search_id: str, db: Session = Depends(get_db)):
    search = db.get(db_models.SearchRequest, search_id)
    if not search:
        raise HTTPException(404, "Search not found")
    return search


@router.get("", response_model=list[schemas.SearchOut])
def list_searches(db: Session = Depends(get_db)):
    return db.query(db_models.SearchRequest).order_by(db_models.SearchRequest.created_at.desc()).all()
