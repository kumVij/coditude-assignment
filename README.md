# AI Recruiting Platform

Two full-stack recruiting applications built with FastAPI, Next.js, SQLite, and Hunar.AI voice
agents. This repository started as a take-home assignment and has been extended into a practical
portfolio project focused on consent-aware calling, asynchronous processing, PII protection, and
recruiting workflow automation.

## Applications

### Hiring Assistant

Creates a role, stores candidates, accepts PDF/DOCX resumes, extracts structured skills and
experience, provisions a Hunar screening agent, and places consent-gated screening calls. The
dashboard polls call status and displays recordings, recommendations, summaries, and extracted
results.

### People Search & Reachout

Accepts a job description, parses search criteria, sources people through People Data Labs or a
mock provider, lets a recruiter select candidates, and uses Hunar for an initial outreach call.
The backend also includes optional Anthropic JD parsing, adaptive outreach prompts, and a Google
Calendar free/busy adapter.

### Part 3 Design

[`docs/part3-attendance-design.md`](docs/part3-attendance-design.md) describes an attendance
system for 1,000 people across 100 locations in a world without smartphones or mobile apps.

## Technology

- Backend: Python 3.13, FastAPI, SQLAlchemy, Pydantic Settings, Uvicorn
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide icons
- Storage: SQLite locally; PostgreSQL is the production migration path
- Voice: Hunar.AI Voice Agents API
- Sourcing: People Data Labs with a mock-data fallback
- Queue: Celery + Redis in production, bounded local worker fallback for development
- Security: JWT, Argon2 password hashing, Fernet PII encryption, consent checks, rate limiting
- Migrations: Alembic
- Observability: structured JSON logs and optional Sentry integration

## Architecture

```text
Next.js dashboard
       |
       v
FastAPI API ---- SQLite/PostgreSQL
       |
       +---- Hunar.AI agents and calls
       +---- People Data Labs (App 2)
       +---- Anthropic (optional JD/prompt generation)
       +---- Google Calendar (optional recruiter availability)

Hunar webhook ---- signature verification ---- idempotent event update ---- database

Screen request ---- ScreeningBatch ---- Celery/Redis worker ---- Hunar bulk calls
                                      |
                                      +---- ScreeningCall rows
                                      +---- DeadLetter rows on failure
```

## Important Request Flows

### Hiring call flow

1. Recruiter creates a job.
2. Recruiter adds a candidate and confirms consent.
3. Optional resume upload extracts skills and experience.
4. Recruiter provisions a round 1 or round 2 agent.
5. Recruiter clicks **Call** for one candidate or **Call all candidates**.
6. The API creates a `ScreeningBatch` and returns `202 Accepted` with a `batch_id`.
7. A local worker or Celery worker calls Hunar.
8. The returned Hunar call ID is persisted as a `ScreeningCall`.
9. Hunar updates arrive through a signed webhook, or the dashboard polls Hunar with
   `?refresh=true` when no public webhook URL is available.
10. The dashboard shows `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `NOT_CONNECTED`, or `FAILED`.

The API never silently places a call without recorded consent. Use only real numbers controlled by
you or candidates who explicitly agreed to be contacted.

### Reliability flow

- Webhook events use a unique event key. Duplicate deliveries return success without applying the
  event twice.
- Screening is asynchronous. The browser does not wait for the entire Hunar bulk request.
- Hunar/provider failures are recorded in `dead_letters` and captured by Sentry when configured.
- Celery workers retry transient failures with backoff.
- Unmapped Hunar responses are dead-lettered instead of disappearing silently.
- `GET /api/jobs/{job_id}/screening-batches/{batch_id}` exposes batch state.

## Project Structure

```text
coditude-assignment/
├── apps/
│   ├── hiring-assistant/
│   │   ├── backend/
│   │   │   ├── app/
│   │   │   │   ├── models/          # SQLAlchemy models and Pydantic schemas
│   │   │   │   ├── routers/         # jobs, candidates, screening, auth, webhooks
│   │   │   │   ├── services/        # Hunar, queue, security, resume, LLM adapters
│   │   │   │   └── main.py
│   │   │   ├── alembic/              # database migrations
│   │   │   ├── requirements.txt
│   │   │   └── .env.example
│   │   └── frontend/
│   │       └── src/app/              # dashboard and job detail pages
│   └── people-search-reachout/
│       ├── backend/
│       │   ├── app/                  # search, reachout, PDL, JD, LLM, Calendar
│       │   └── requirements.txt
│       └── frontend/
├── docs/
└── shared/
```

## Local Setup on Windows

Open separate PowerShell terminals for each process.

### Hiring backend

```powershell
cd "C:\Users\Hp\Documents\resume\New folder\coditude-assignment\coditude-assignment\apps\hiring-assistant\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set at least `HUNAR_API_KEY` in `.env`. For the existing local demo, use the checked local
development values for `AUTH_REQUIRED`, `QUEUE_BACKEND`, and `AUTO_CREATE_SCHEMA` only. Never use
those development secrets in production.

Apply migrations:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

Open Swagger at http://localhost:8001/docs.

### Hiring frontend

```powershell
cd "C:\Users\Hp\Documents\resume\New folder\coditude-assignment\coditude-assignment\apps\hiring-assistant\frontend"
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000. If port `3000` is occupied, Next.js may use `3001`; update
`CORS_ORIGINS` in the backend `.env` and restart the backend. The local backend accepts both
ports by default.

### People Search backend/frontend

Use the same commands from the corresponding App 2 directories, with backend port `8002`.
`PDL_MOCK_MODE=true` allows the search flow to run without a People Data Labs key.

## Environment Variables

### Hiring backend

```env
HUNAR_API_KEY=
DATABASE_URL=sqlite:///./hiring_assistant.db
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
PUBLIC_BASE_URL=

# Security
AUTH_REQUIRED=true
JWT_SECRET_KEY=
PII_ENCRYPTION_KEY=
RATE_LIMIT=30/minute

# Reliability
QUEUE_BACKEND=celery
REDIS_URL=redis://localhost:6379/0
SENTRY_DSN=
AUTO_CREATE_SCHEMA=false

# Optional adaptive prompt generation
ANTHROPIC_API_KEY=
LLM_MODEL=claude-3-5-sonnet-20241022
```

### People Search backend

```env
HUNAR_API_KEY=
PDL_API_KEY=
PDL_MOCK_MODE=true
DATABASE_URL=sqlite:///./people_search.db
CORS_ORIGINS=http://localhost:3000
PUBLIC_BASE_URL=
ANTHROPIC_API_KEY=
LLM_MODEL=claude-3-5-sonnet-20241022
GOOGLE_SERVICE_ACCOUNT_JSON=
GOOGLE_CALENDAR_ID=primary
```

Never commit `.env`, `.env.local`, API keys, service-account JSON, SQLite databases, or
`node_modules`. Only `.env.example` files belong in Git.

## API Workflows

### Authentication

```text
POST /api/auth/register
POST /api/auth/login
```

Both return a bearer JWT. Set `Authorization: Bearer <token>` when `AUTH_REQUIRED=true`.

### Hiring

```text
POST /api/jobs
GET  /api/jobs
POST /api/jobs/{job_id}/provision-agent?round_number=1
POST /api/jobs/{job_id}/provision-agent?round_number=2
POST /api/jobs/{job_id}/candidates
POST /api/jobs/{job_id}/candidates/{candidate_id}/consent
POST /api/jobs/{job_id}/candidates/{candidate_id}/resume
POST /api/jobs/{job_id}/screen
GET  /api/jobs/{job_id}/screening-batches/{batch_id}
GET  /api/jobs/{job_id}/calls?refresh=true
```

Example screening request:

```json
{
  "candidate_ids": ["candidate-id"],
  "round_number": 1,
  "max_retry_count": 1,
  "retry_interval_hours": 6
}
```

### Resume upload

The resume endpoint accepts `multipart/form-data` with a PDF or DOCX file. It extracts text,
normalizes known skills, estimates explicit years of experience, and stores the full extracted text
encrypted at rest.

## Running the Production Queue

Start Redis, configure:

```env
QUEUE_BACKEND=celery
REDIS_URL=redis://<redis-host>:6379/0
```

Run the API and a separate worker:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
celery -A app.services.screening_queue.celery_app worker --loglevel=INFO
```

For Render, use one web service for FastAPI and a separate worker service for Celery. Run
`alembic upgrade head` as a deploy/pre-start command; do not rely on `create_all()` in production.

## Deployment Checklist

1. Push the repository only after checking `git status` and confirming no real `.env` is staged.
2. Deploy each backend as a separate Render/Railway service.
3. Configure the backend root directory and run `pip install -r requirements.txt`.
4. Run Alembic migrations before the service starts.
5. Configure Hunar, database, JWT, Fernet, Redis, CORS, and Sentry environment variables.
6. Deploy each frontend as a separate Vercel project.
7. Set `NEXT_PUBLIC_API_BASE_URL` to the matching backend URL.
8. Add each deployed frontend URL to the backend `CORS_ORIGINS` and redeploy.
9. Set `PUBLIC_BASE_URL` so Hunar can reach the signed webhook endpoint.
10. Run one consented live smoke test and verify status, recording, result, and webhook/polling.

## Troubleshooting

### `Consent is required before placing screening calls`

The candidate has `consent_obtained=false`. Use **Record consent** only after the person has agreed
to receive the call, then retry the individual **Call** action.

### CORS error from port 3001

Add `http://localhost:3001` to `CORS_ORIGINS` and restart Uvicorn. Stop stale reload processes if
the old middleware is still serving port `8001`.

### Batch says queued forever

Check `QUEUE_BACKEND`. Local mode uses an in-process worker and is lost on restart. Celery mode
requires a reachable Redis server and a running worker process.

### Call remains `SCHEDULED`

The Hunar API accepted the request but has not reported a connection. Poll
`GET /api/jobs/{job_id}/calls?refresh=true`; do not click Call again because that creates another
phone call.

### Hunar key errors

Rotate expired or exposed keys. Keep the replacement only in environment variables, never source
code, Git, screenshots, or browser-visible configuration.

## Interview Preparation

### One-minute project explanation

> I built two recruiting workflows around Hunar.AI voice agents. The Hiring Assistant manages
> roles, consented candidates, resume extraction, round-aware screening, and live call results.
> The People Search app parses a JD, sources candidates through PDL or mock data, and performs
> respectful outreach. The important engineering work is around reliability and safety: calls are
> asynchronous through a queue, webhook delivery is idempotent, failures go to dead letters,
> candidate contact data is encrypted, ownership and JWT authentication are supported, and the
> dashboard falls back to polling when local webhooks cannot reach the machine.

### Why use a queue?

Bulk calling can take longer than an HTTP request should remain open. A `ScreeningBatch` gives the
client an immediate tracking ID, while Celery provides retries, worker isolation, and horizontal
scaling. Redis is the broker/result backend; dead letters preserve failures for investigation.

### Why use polling as well as webhooks?

Webhooks are efficient in production but require a public HTTPS URL. Local development usually has
no reachable callback address, so polling Hunar for non-terminal calls makes the dashboard useful in
both environments. Webhooks remain the lower-latency production path.

### How is webhook duplication handled?

Each event receives a unique key based on Hunar's event ID when available, otherwise a stable call,
event, and timestamp combination. A unique database index makes concurrent duplicate deliveries
safe; an integrity conflict is treated as an already-processed event.

### How is PII protected?

Candidate phone numbers, emails, and extracted resume text are encrypted with Fernet at rest. A
one-way normalized phone hash supports duplicate detection without using plaintext as the identity
key. Decryption occurs only at the API or Hunar integration boundary.

### How would this scale further?

Move SQLite to PostgreSQL, use Redis for distributed rate limiting, add object storage for resumes,
separate call provisioning and status reconciliation workers, add metrics/tracing, introduce a
proper OAuth calendar flow, and add contract tests against a Hunar sandbox.

## Known Limitations

- The local queue fallback is not durable; production should run Celery and Redis.
- Anthropic and Google integrations are opt-in and require provider credentials/configuration.
- Google Calendar currently provides a free/busy adapter; OAuth consent and automatic slot-offer
  messaging still need product-specific setup.
- App 2 retains its original simpler persistence/auth surface and should receive the App 1 security
  model before production use.
- SQLite is suitable for local demos, not concurrent production workloads.

## Git Safety

Before publishing:

```powershell
git status --short --untracked-files=all
git check-ignore -v apps/hiring-assistant/backend/.env
git log -p --all -- '**/.env'
```

Rotate any key that has appeared in chat, logs, screenshots, or commits. Do not commit or push
secrets.

## Part 3

See [`docs/part3-attendance-design.md`](docs/part3-attendance-design.md).
