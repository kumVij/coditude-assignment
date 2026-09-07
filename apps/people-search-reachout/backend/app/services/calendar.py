import json
from datetime import datetime, timedelta, timezone

from app.config import get_settings


def recruiter_slots(hours: int = 72, slot_minutes: int = 30) -> list[dict]:
    """Return free Google Calendar slots when a service account is configured.

    Without credentials this returns an empty list so reachout remains usable in mock mode.
    """
    settings = get_settings()
    if not settings.google_service_account_json:
        return []
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_info(
        json.loads(settings.google_service_account_json), scopes=["https://www.googleapis.com/auth/calendar"]
    )
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=hours)
    busy = service.freebusy().query(body={"timeMin": start.isoformat(), "timeMax": end.isoformat(), "items": [{"id": settings.google_calendar_id}]}).execute()["calendars"][settings.google_calendar_id]["busy"]
    return [{"start": start.isoformat(), "duration_minutes": slot_minutes}] if not busy else []