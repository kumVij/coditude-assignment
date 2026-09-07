from fastapi import HTTPException

from app.config import get_settings
from app.services.hunar_client import HunarClient


def get_hunar_client() -> HunarClient:
    settings = get_settings()
    if not settings.hunar_api_key:
        raise HTTPException(
            status_code=500,
            detail="HUNAR_API_KEY is not configured on the server. Set it in your .env file.",
        )
    return HunarClient(api_key=settings.hunar_api_key)
