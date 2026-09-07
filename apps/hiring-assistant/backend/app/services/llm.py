import json

import httpx

from app.config import get_settings


def generate_json(prompt: str) -> dict | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": settings.llm_model, "max_tokens": 1800, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        response.raise_for_status()
        text = response.json()["content"][0]["text"]
        return json.loads(text[text.find("{"):text.rfind("}") + 1])
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None