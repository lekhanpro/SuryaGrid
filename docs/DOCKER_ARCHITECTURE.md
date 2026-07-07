# SuryaGrid AI — Docker Architecture

Full stack via `docker compose`: FastAPI backend, Next.js frontend, PostgreSQL, Redis.

```
                       ┌─────────────────────────────┐
  browser :3000 ─────▶ │ frontend (Next.js, next start)│
                       └──────────────┬──────────────┘
  browser/API :8000 ────────────────▶ │  (NEXT_PUBLIC_API_URL → :8000)
                       ┌──────────────▼──────────────┐
                       │ backend (FastAPI + uvicorn)  │
                       │  agents · ml · dsm · sources │
                       └───────┬───────────────┬──────┘
                    :5432      ▼               ▼   :6379
              ┌─────────────────────┐  ┌───────────────┐
              │ postgres (pgdata vol)│  │ redis (cache) │
              └─────────────────────┘  └───────────────┘
```

## Services

| Service | Image / build | Port | Healthcheck |
|---------|---------------|------|-------------|
| `backend` | `./backend` (python:3.12-slim) | 8000:8000 | python urllib → `/api/v1/health` |
| `frontend` | `./frontend` (node:20-alpine) | 3000:3000 | `wget --spider localhost:3000` |
| `postgres` | postgres:16 | 5432:5432 | `pg_isready` |
| `redis` | redis:7-alpine | 6379:6379 | `redis-cli ping` |

`backend` waits for `postgres` and `redis` to be **healthy** (`depends_on: condition: service_healthy`).

## Volumes & mounts

- `pgdata` — named volume for Postgres data (persists across restarts).
- `./backend/data:/app/data` — **mounted dataset folder**. Drop the Kaggle CSV into
  `backend/data/raw/kaggle/` on the host and the backend sees it. Built augmented
  datasets land in `backend/data/processed/`.
- `./backend/models:/app/models` — trained model artifacts persist here.

## Environment

The backend reads (compose `environment:`; override via a `.env` file — see `.env.example`):

```
DATABASE_URL=postgresql+asyncpg://suryagrid:suryagrid@postgres:5432/suryagrid
REDIS_URL=redis://redis:6379/0
WEATHER_PROVIDER=open-meteo
DSM_DEFAULT_REGION=Karnataka
DSM_DEFAULT_RULE_PROFILE=kerc-solar
KAGGLE_USERNAME=            # optional
KAGGLE_KEY=                 # optional
```

The frontend bakes `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api/v1`) at
build time via a build arg, because Next inlines `NEXT_PUBLIC_*` vars. The browser
calls the host-mapped backend port, hence `localhost`.

## Schema bootstrap

On startup the backend runs `Base.metadata.create_all` (idempotent) — so all tables,
including the Phase 1.5 tables (substations, locations, dsm_rule_profiles, …), are
created automatically on both SQLite (local) and PostgreSQL (Docker). Alembic migrations
are provided for managed Postgres change control but are not required at runtime. Default
DSM rule profiles are seeded on startup.

## Run

```bash
docker compose up --build
```

- Frontend:  http://localhost:3000
- Backend Swagger:  http://localhost:8000/docs
- Backend health:  http://localhost:8000/api/v1/health

## Static frontend (GitHub Pages)

`next.config.js` switches to static export only when `STATIC_EXPORT=true` (set by the
Pages deploy workflow). The Docker image builds a normal server bundle so `next start`
serves the live app that talks to the backend.

## Optional services (future)

A `worker` and a `scheduler` are natural extensions. The backend already contains an
opt-in APScheduler (`SCHEDULER_ENABLED=true`) for periodic ingestion; a dedicated worker
would require a task queue (e.g. Celery) which is out of Phase 1.5 scope. They are
intentionally omitted rather than shipped non-functional.
