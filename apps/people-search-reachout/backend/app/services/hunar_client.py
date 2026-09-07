"""
Hunar Voice Agents API client.

Thin, typed wrapper around https://api.voice.hunar.ai/external/v1/
Docs: https://api.voice.hunar.ai/docs/external/

Design notes:
- The API key is NEVER hardcoded here. It is read from the HUNAR_API_KEY
  environment variable at call time by the FastAPI dependency that
  constructs this client (see app/services/hunar.py in each backend).
- All network calls go through `httpx` with sane timeouts and are wrapped
  so callers get a normalized `HunarAPIError` instead of raw HTTP errors.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import httpx

BASE_URL = "https://api.voice.hunar.ai/external/v1"
WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300


class HunarAPIError(Exception):
    """Raised for any non-2xx response from the Hunar API."""

    def __init__(self, status_code: int, message: str, details: Any = None):
        self.status_code = status_code
        self.message = message
        self.details = details or []
        super().__init__(f"Hunar API error {status_code}: {message}")


@dataclass
class RetryConfig:
    max_retry_count: int = 0
    retry_interval_hours: int = 0

    def to_dict(self) -> dict:
        return {
            "max_retry_count": self.max_retry_count,
            "retry_interval_hours": self.retry_interval_hours,
        }


@dataclass
class Guardrails:
    allowed_days: list[str]
    earliest_call_time: str  # "HH:MM"
    last_call_time: str  # "HH:MM"

    def to_dict(self) -> dict:
        return {
            "allowed_days": self.allowed_days,
            "earliest_call_time": self.earliest_call_time,
            "last_call_time": self.last_call_time,
        }


class HunarClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL, timeout: float = 20.0):
        if not api_key:
            raise ValueError("Hunar API key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ---------------------------------------------------------------- core
    def _headers(self) -> dict:
        return {"X-API-Key": self._api_key, "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code >= 400:
            try:
                payload = resp.json()
                message = payload.get("message", resp.text)
                details = payload.get("details", [])
            except Exception:
                message = resp.text
                details = []
            raise HunarAPIError(resp.status_code, message, details)
        if resp.status_code == 200 and resp.content:
            return resp.json()
        return {}

    # -------------------------------------------------------------- agents
    def list_agents(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        params = {"page": page, "page_size": page_size, **filters}
        return self._request("GET", "/agents/", params=params)

    def get_agent(self, agent_id: str) -> dict:
        return self._request("GET", f"/agents/{agent_id}/")

    def create_agent(
        self,
        *,
        name: str,
        language: str,
        voice_persona: str,
        agent_prompt: str,
        objective: str,
        introduction: str,
        result_prompt: str,
        result_schema: dict,
        persona_name: Optional[str] = None,
    ) -> dict:
        body = {
            "name": name,
            "language": language,
            "voice_persona": voice_persona,
            "agent_prompt": agent_prompt,
            "objective": objective,
            "introduction": introduction,
            "result_prompt": result_prompt,
            "result_schema": result_schema,
        }
        if persona_name:
            body["persona_name"] = persona_name
        return self._request("POST", "/agents/", json=body)

    def update_agent(self, agent_id: str, **fields) -> dict:
        return self._request("PUT", f"/agents/{agent_id}/", json=fields)

    # --------------------------------------------------------------- calls
    def create_call(
        self,
        *,
        agent_id: str,
        callee_name: str,
        mobile_number: str,
        custom_data: Optional[dict] = None,
        from_phone_number: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        guardrails: Optional[Guardrails] = None,
        timezone: Optional[str] = None,
        callback_config: Optional[dict] = None,
    ) -> dict:
        body: dict[str, Any] = {
            "agent_id": agent_id,
            "callee_name": callee_name,
            "mobile_number": mobile_number,
            "custom_data": custom_data or {},
        }
        if from_phone_number:
            body["from_phone_number"] = from_phone_number
        if request_id:
            body["request_id"] = request_id
        if retry_config:
            body["retry_config"] = retry_config.to_dict()
        if guardrails:
            body["guardrails"] = guardrails.to_dict()
        if timezone:
            body["timezone"] = timezone
        if callback_config:
            body["callback_config"] = callback_config
        return self._request("POST", "/calls/", json=body)

    def create_bulk_calls(
        self,
        *,
        agent_id: str,
        data: list[dict],
        from_phone_number: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        guardrails: Optional[Guardrails] = None,
        timezone: Optional[str] = None,
        callback_config: Optional[dict] = None,
        remove_invalid_rows: bool = True,
        remove_duplicate_phone_numbers: bool = True,
    ) -> list[dict]:
        body: dict[str, Any] = {
            "agent_id": agent_id,
            "data": data,
            "remove_invalid_rows": remove_invalid_rows,
            "remove_duplicate_phone_numbers": remove_duplicate_phone_numbers,
        }
        if from_phone_number:
            body["from_phone_number"] = from_phone_number
        if request_id:
            body["request_id"] = request_id
        if retry_config:
            body["retry_config"] = retry_config.to_dict()
        if guardrails:
            body["guardrails"] = guardrails.to_dict()
        if timezone:
            body["timezone"] = timezone
        if callback_config:
            body["callback_config"] = callback_config
        result = self._request("POST", "/calls/bulk/", json=body)
        return result if isinstance(result, list) else result.get("results", [])

    def get_call(self, call_id: str) -> dict:
        return self._request("GET", f"/calls/{call_id}/")

    def list_calls(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[list[str]] = None,
        agent_id: Optional[list[str]] = None,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if status:
            params["status"] = ",".join(status)
        if agent_id:
            params["agent_id"] = ",".join(agent_id)
        return self._request("GET", "/calls/", params=params)

    # ------------------------------------------------------------ numbers
    def list_numbers(self, page: int = 1, page_size: int = 20) -> dict:
        return self._request("GET", "/numbers/", params={"page": page, "page_size": page_size})


# ----------------------------------------------------------------------
# Webhook signature verification (copied per Hunar docs, unchanged logic)
# ----------------------------------------------------------------------

def compute_hunar_signature(*, api_key: str, request_body: bytes, timestamp: str) -> str:
    message = f"{timestamp.strip()}.".encode("utf-8") + request_body
    digest = hmac.new(api_key.encode("utf-8"), message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_hunar_webhook_signature(
    *,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
    request_body: bytes,
    trusted_api_keys: Iterable[str],
    tolerance_seconds: int = WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS,
) -> bool:
    if not (signature_header and signature_header.strip()):
        return False
    if not (timestamp_header and timestamp_header.strip()):
        return False

    try:
        ts = int(timestamp_header.strip())
        if abs(time.time() - ts) > tolerance_seconds:
            return False
    except ValueError:
        return False

    signatures = [s.strip() for s in signature_header.split(",") if s.strip()]
    for api_key in trusted_api_keys:
        computed = compute_hunar_signature(
            api_key=api_key, request_body=request_body, timestamp=timestamp_header.strip()
        )
        for signature in signatures:
            if hmac.compare_digest(signature, computed):
                return True
    return False
