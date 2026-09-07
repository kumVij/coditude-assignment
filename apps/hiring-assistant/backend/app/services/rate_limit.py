from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request

from app.config import get_settings

_requests: dict[str, deque[float]] = defaultdict(deque)


def enforce_rate_limit(request: Request) -> None:
    raw_limit, _, raw_window = get_settings().rate_limit.partition("/")
    try:
        limit = int(raw_limit)
        window = 60.0 if raw_window == "minute" else 3600.0
    except ValueError:
        limit, window = 30, 60.0
    key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
    now = monotonic()
    bucket = _requests[key]
    while bucket and now - bucket[0] >= window:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(429, "Rate limit exceeded; try again later")
    bucket.append(now)