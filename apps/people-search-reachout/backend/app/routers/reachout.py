from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import db_models, schemas
from app.services.agent_builder import build_reachout_agent_config
from app.services.hunar_client import HunarAPIError, HunarClient, RetryConfig
from app.services.hunar_dep import get_hunar_client

router = APIRouter(prefix="/api/search/{search_id}", tags=["reachout"])


@router.post("/provision-agent", response_model=schemas.SearchOut)
def provision_agent(
    search_id: str,
    db: Session = Depends(get_db),
    hunar: HunarClient = Depends(get_hunar_client),
):
    search = db.get(db_models.SearchRequest, search_id)
    if not search:
        raise HTTPException(404, "Search not found")

    cfg = build_reachout_agent_config(search)
    try:
        if search.hunar_agent_id:
            agent = hunar.update_agent(
                search.hunar_agent_id,
                name=f"Sourcer - {search.job_title}"[:64],
                language=get_settings().default_language,
                voice_persona=get_settings().default_voice_persona,
                persona_name="Aditi",
                **cfg,
            )
        else:
            agent = hunar.create_agent(
                name=f"Sourcer - {search.job_title}"[:64],
                language=get_settings().default_language,
                voice_persona=get_settings().default_voice_persona,
                persona_name="Aditi",
                **cfg,
            )
    except HunarAPIError as e:
        raise HTTPException(e.status_code, f"Hunar API error: {e.message}")

    search.hunar_agent_id = agent["id"]
    db.commit()
    db.refresh(search)
    return search


@router.post("/reachout", response_model=list[schemas.ReachoutCallOut])
def start_reachout(
    search_id: str,
    payload: schemas.StartReachoutRequest,
    db: Session = Depends(get_db),
    hunar: HunarClient = Depends(get_hunar_client),
):
    settings = get_settings()
    search = db.get(db_models.SearchRequest, search_id)
    if not search:
        raise HTTPException(404, "Search not found")
    if not search.hunar_agent_id:
        raise HTTPException(400, "Provision the Hunar agent for this search first")

    candidates = (
        db.query(db_models.SourcedCandidate)
        .filter(db_models.SourcedCandidate.id.in_(payload.candidate_ids))
        .all()
    )
    candidates = [c for c in candidates if c.mobile_number]
    if not candidates:
        raise HTTPException(400, "None of the selected candidates have a callable mobile number")

    callback_config = None
    if settings.public_base_url:
        webhook_url = f"{settings.public_base_url.rstrip('/')}/api/webhooks/hunar"
        callback_config = {"call_summary_callback_url": webhook_url}

    bulk_data = [
        {
            "callee_name": c.full_name,
            "mobile_number": c.mobile_number,
            "custom_data": {"company": c.company or "your current company", "job_role": c.job_title or "your role"},
        }
        for c in candidates
    ]

    try:
        results = hunar.create_bulk_calls(
            agent_id=search.hunar_agent_id,
            data=bulk_data,
            request_id=f"search-{search_id[:8]}",
            retry_config=RetryConfig(payload.max_retry_count, payload.retry_interval_hours)
            if payload.max_retry_count
            else None,
            timezone=settings.default_timezone,
            callback_config=callback_config,
        )
    except HunarAPIError as e:
        raise HTTPException(e.status_code, f"Hunar API error: {e.message}")

    by_phone = {c.mobile_number: c for c in candidates}
    created = []
    for r in results:
        candidate = by_phone.get(r.get("mobile_number"))
        if not candidate:
            continue
        candidate.selected_for_reachout = True
        call = db_models.ReachoutCall(
            hunar_call_id=r["id"],
            candidate_id=candidate.id,
            search_id=search_id,
            status=r.get("status", "NOT_STARTED"),
            request_id=r.get("request_id"),
        )
        db.add(call)
        created.append(call)
    db.commit()
    for c in created:
        db.refresh(c)
    return created


@router.get("/calls", response_model=list[schemas.ReachoutCallOut])
def list_calls(
    search_id: str,
    db: Session = Depends(get_db),
    hunar: HunarClient = Depends(get_hunar_client),
    refresh: bool = False,
):
    calls = db.query(db_models.ReachoutCall).filter(db_models.ReachoutCall.search_id == search_id).all()

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
