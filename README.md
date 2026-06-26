# Suryagrid AI

**Solar Irradiance Nowcasting + DSM Penalty Prediction**

A multi-agent platform that turns real weather/irradiance data into a solar
generation nowcast, compares it against the scheduled (declared) generation, and
classifies Deviation Settlement Mechanism (DSM) penalty risk with estimated cost.

## What it does

1. Pulls **real hourly irradiance** (GHI / DNI / DHI), temperature, cloud cover and
   wind for any site from **Open-Meteo** (free, no API key).
2. Computes **physics-based AC generation** with **pvlib** (solar position →
   plane-of-array transposition → cell temperature → PVWatts DC → inverter AC).
3. Derives the **day-ahead committed schedule** from a clear-sky model — the
   realistic baseline a generator declares to the grid.
4. Runs **DSM classification**: deviation vs the allowed band → `NO_PENALTY` /
   `PENALTY_RISK` / `INVALID_SCHEDULE`, with an estimated charge on the deviated energy.
5. Scores **operational risk** (LOW / MEDIUM / HIGH / CRITICAL) and produces a
   human-readable explanation.
6. Serves a **24h+ timeline** (time, generation, energy, expected DSM values) and a
   day summary, rendered in a Next.js dashboard.

All numbers are deterministic and reproducible — pvlib does the math, no LLM in the
numeric path.

## Architecture

```
Open-Meteo (real GHI/DNI/DHI, temp, cloud, wind)
      │
      ▼
ForecastAgent (pvlib)  ── clear-sky baseline ──┐
      │ nowcast (cloud-affected)               │ scheduled MW
      ▼                                         ▼
DSMClassifierAgent  ── deviation vs band ──► penalty / cost
      │
      ▼
RiskAgent ──► ExplanationAgent ──► FastAPI ──► Next.js dashboard
(OrchestratorAgent sequences the per-interval pipeline; ForecastService runs the timeline.)
```

## Agents

| Agent | Responsibility |
|-------|---------------|
| ForecastAgent | pvlib physics: irradiance → POA → cell temp → AC power (MW) + confidence |
| DSMClassifierAgent | Deviation vs allowed band, penalty status and chargeable cost |
| RiskAgent | Deterministic 0–100 risk score and LOW/MEDIUM/HIGH/CRITICAL level |
| ExplanationAgent | Plain-language interval summary |
| OrchestratorAgent | Sequences the agents for a single interval |

## Data provider

`app/providers/` defines a `WeatherProvider` interface; `OpenMeteoProvider` is the
default real source. New sources (Solcast, NASA POWER) implement the same interface
and the pvlib pipeline runs unchanged.

## Run

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Live demo (real data, no server needed)
```bash
cd backend
python run_all_demo.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard: http://localhost:3000

> Note: the dashboard is served at the root path `/` in all environments.

### Docker Compose (full stack)
```bash
docker-compose up --build
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/sites` | Register a solar site |
| GET | `/api/v1/sites` / `/sites/{id}` | List / get sites |
| GET | `/api/v1/weather/{site_id}` | Real hourly irradiance/weather |
| POST | `/api/v1/predict` | Single-interval DSM evaluation from explicit irradiance |
| POST | `/api/v1/dsm/check` | Standalone DSM classification |
| GET | `/api/v1/timeline/{site_id}` | Hourly nowcast + DSM timeline + summary |
| GET | `/api/v1/summary/{site_id}` | Day summary |

`timeline`/`summary`/`weather` accept query params (`latitude`, `longitude`,
`capacity_mw`, `tilt`, `azimuth`, `scheduled_mw`, `threshold_percent`,
`penalty_rate`, `forecast_days`) so any location works without pre-registering a site.

## Test
```bash
cd backend
python -m pytest tests/ -q
```
Tests use a deterministic offline provider, so they never depend on the network.

Lint/format (matches CI):
```bash
cd backend
ruff check app tests
ruff format --check app tests
```

## CI/CD

- **CI** (`.github/workflows/ci.yml`) runs on every push and PR to `main`: ruff
  lint/format, backend pytest, and the Next.js build (with artifact validation).
  Dependencies are cached.
- **CD** (`.github/workflows/deploy.yml`) publishes the frontend to GitHub Pages
  **only after CI succeeds** (or via manual dispatch). It validates the Pages
  prerequisite, detects the base path from the actual Pages config (no hosting
  assumptions), validates the build artifact, and verifies the live URL returns 200.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for details.

## Tech stack

- **Backend**: Python 3.11+, FastAPI, Pydantic, pvlib, pandas/numpy, httpx
- **Data**: Open-Meteo (real, free, key-less)
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Optional**: PostgreSQL + Redis (degrade gracefully if absent)
- **Deploy**: Docker Compose

## Notes & next steps

- Site registry is in-memory; SQLAlchemy models exist in `app/db` for PostgreSQL
  persistence in a clustered deployment.
- JWT auth and per-route rate limiting are scaffolded but not enforced yet.
- An RL policy for adaptive penalty/discount rates (see `PROJECT_PLAN.md`) is the
  planned next phase; the deterministic forecast + DSM core it depends on is done.
