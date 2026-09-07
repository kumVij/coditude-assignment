from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import reachout, search, webhooks

Base.metadata.create_all(bind=engine)

settings = get_settings()

app = FastAPI(
    title="People Search & Reachout API",
    description="Paste a JD, source candidates, and reach out via Hunar.AI Voice Agents.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(reachout.router)
app.include_router(webhooks.router)


@app.get("/")
def health():
    return {"status": "ok", "service": "people-search-reachout", "mock_mode": settings.effective_mock_mode}
