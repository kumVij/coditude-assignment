import json
import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import db_models
from app.services.hunar_client import verify_hunar_webhook_signature

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger("webhooks")


@router.post("/hunar")
async def hunar_webhook(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    raw_body = await request.body()

    ok = verify_hunar_webhook_signature(
        signature_header=request.headers.get("X-Hunar-Signature"),
        timestamp_header=request.headers.get("X-Hunar-Timestamp"),
        request_body=raw_body,
        trusted_api_keys=settings.trusted_webhook_keys,
    )
    if not ok:
        logger.warning("Rejected Hunar webhook: invalid signature")
        return Response(status_code=401)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response(status_code=400)

    call_id = payload.get("call_id")
    if not call_id:
        return Response(status_code=400)

    event_key = payload.get("event_id") or f"{call_id}:{payload.get('event_type')}:{payload.get('updated_at', payload.get('timestamp', ''))}"
    db.add(db_models.WebhookEvent(event_key=event_key, event_type=payload.get("event_type")))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"ok": True, "duplicate": True}

    call = db.query(db_models.ScreeningCall).filter(db_models.ScreeningCall.hunar_call_id == call_id).first()
    if call:
        call.status = payload.get("status", call.status)
        call.lifecycle_status = payload.get("lifecycle_status", call.lifecycle_status)
        call.recording_url = payload.get("recording_url", call.recording_url)
        if payload.get("result") is not None:
            call.result = payload["result"]
        if payload.get("duration_minutes") is not None:
            call.duration_minutes = payload["duration_minutes"]
        db.commit()
    else:
        logger.info("Webhook for unknown call_id=%s (event=%s)", call_id, payload.get("event_type"))

    return {"ok": True, "event_type": payload.get("event_type")}
