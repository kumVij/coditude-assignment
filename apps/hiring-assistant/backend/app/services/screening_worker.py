import json
import logging

import sentry_sdk
from app.database import SessionLocal
from app.models import db_models
from app.config import get_settings
from app.services.hunar_client import HunarAPIError, HunarClient, RetryConfig
from app.services.security import decrypt_pii
from app.services.screening_queue import celery_app

logger = logging.getLogger("screening_worker")


def _normalize(value: str | None) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def process_screening_batch(batch_id: str) -> None:
    db = SessionLocal()
    batch = db.get(db_models.ScreeningBatch, batch_id)
    if not batch:
        db.close()
        return
    batch.status = "RUNNING"
    db.commit()
    try:
        job = db.get(db_models.Job, batch.job_id)
        candidate_ids = json.loads(batch.candidate_ids or "[]")
        candidates = db.query(db_models.Candidate).filter(db_models.Candidate.id.in_(candidate_ids)).all()
        if not job or not job.hunar_agent_id:
            raise ValueError("Job or Hunar agent is unavailable")
        candidates = [candidate for candidate in candidates if candidate.consent_obtained == "true"]
        by_phone: dict[str, list[db_models.Candidate]] = {}
        bulk_data = []
        for candidate in candidates:
            phone = decrypt_pii(candidate.mobile_number_encrypted) or candidate.mobile_number
            by_phone.setdefault(_normalize(phone), []).append(candidate)
            bulk_data.append({"callee_name": candidate.name, "mobile_number": phone, "custom_data": {}})
        settings = get_settings()
        results = HunarClient(settings.hunar_api_key).create_bulk_calls(
            agent_id=job.hunar_agent_id,
            data=bulk_data,
            request_id=f"batch-{batch.id}",
            retry_config=RetryConfig(1, 6),
            timezone=settings.default_timezone,
        )
        for result in results:
            candidates_for_phone = by_phone.get(_normalize(result.get("mobile_number")), [])
            name = str(result.get("callee_name") or "").strip().casefold()
            matches = [candidate for candidate in candidates_for_phone if candidate.name.strip().casefold() == name]
            candidate = matches[0] if len(matches) == 1 else candidates_for_phone[0] if len(candidates_for_phone) == 1 else None
            if not candidate:
                db.add(db_models.DeadLetter(batch_id=batch.id, job_id=job.id, reason="UNMAPPED_HUNAR_RESULT", payload=result))
                continue
            db.add(db_models.ScreeningCall(
                hunar_call_id=result.get("id"), candidate_id=candidate.id, job_id=job.id,
                status=result.get("status", "NOT_STARTED"), lifecycle_status=result.get("lifecycle_status", result.get("status", "NOT_STARTED")),
                recording_url=result.get("recording_url"), result=result.get("result"),
                duration_minutes=result.get("duration_minutes"), engagement_status=result.get("engagement_status"),
                request_id=result.get("request_id"), round_number=batch.round_number,
            ))
        batch.status = "COMPLETED"
        db.commit()
    except (HunarAPIError, ValueError, OSError) as error:
        logger.exception("screening_batch_failed batch_id=%s", batch_id)
        sentry_sdk.capture_exception(error)
        batch.status = "DEAD_LETTER"
        batch.error = str(error)[:1000]
        db.add(db_models.DeadLetter(batch_id=batch.id, job_id=batch.job_id, reason=type(error).__name__, payload={"message": str(error)[:1000]}))
        db.commit()
        if get_settings().queue_backend.lower() == "celery":
            raise
    finally:
        db.close()


@celery_app.task(name="app.services.screening_worker.process_screening_batch", autoretry_for=(HunarAPIError, OSError), retry_backoff=True, max_retries=3)
def celery_process_screening_batch(batch_id: str) -> None:
    process_screening_batch(batch_id)
