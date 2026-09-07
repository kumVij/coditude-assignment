import json
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, candidates, jobs, screening, webhooks

settings = get_settings()

if settings.auto_create_schema:
    Base.metadata.create_all(bind=engine)
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)

app = FastAPI(
    title="AI Hiring Assistant API",
    description="Voice-AI powered candidate screening, built on Hunar.AI Voice Agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(settings.cors_origin_list + ["http://localhost:3000", "http://localhost:3001"])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    logging.getLogger("http").info(
        "request_complete method=%s path=%s status=%s duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response

app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(screening.router)
app.include_router(webhooks.router)
app.include_router(auth.router)


@app.get("/")
def health():
    return {"status": "ok", "service": "ai-hiring-assistant"}
