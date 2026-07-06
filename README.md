# Suryagrid AI — Real-Data Solar Forecasting & DSM Risk Engine (Phase 1.5)

A multi-agent platform that turns **real** weather/irradiance data into a solar
generation forecast (physics **and** ML), compares it against the scheduled generation,
and classifies **Deviation Settlement Mechanism (DSM)** risk with an estimated charge —
backed by a **source registry** so every formula, threshold and dataset is traceable.

> Phase 1.5 is real-data solar forecasting + DSM risk engine + dashboard. It does **not**
> include blockchain, energy trading, RL optimization, SCADA/hardware control, or payment
> settlement. (Pre-existing Phase 1 RL/settlement modules are retained, not extended.)

## What it does

1. **Real weather** — hourly GHI/DNI/DHI, temperature, humidity, cloud, wind, pressure,
   precipitation from **Open-Meteo** (free, key-less), cached in Redis, persisted in the DB.
2. **ML + physics forecasting** — `formula` (pvlib), `ml` (scikit-learn trained on the
   Kaggle solar dataset), or `hybrid`. Falls back to formula when no model — reported, never faked.
3. **Advanced DSM** — configurable rule profiles (region · regulator · denominator · slab
   bands); KERC/BESCOM and CERC frameworks seeded, with source status.
4. **Fuzzy risk** — genuine fuzzy inference (LOW/MEDIUM/HIGH/CRITICAL).
5. **Locations & substations** — OpenStreetMap substations + operator CSV, nearest-substation
   mapping, and per-site data-coverage.
6. **Sourced** — every value classified & cited (`docs/SOURCE_REGISTRY.md`).
7. **Dashboard** — real operational UI; shows a clear "Backend Offline" banner instead of
   faking data.

## Quick start (Docker — full stack)

```bash
cp .env.example .env        # optional; sensible defaults work out of the box
docker compose up --build
```

- **Frontend:**  http://localhost:3000
- **Backend Swagger:**  http://localhost:8000/docs
- **Backend health:**  http://localhost:8000/api/v1/health

Services: `frontend` (:3000), `backend` (:8000), `postgres` (:5432), `redis` (:6379).
See [docs/DOCKER_ARCHITECTURE.md](docs/DOCKER_ARCHITECTURE.md).

## Load the Kaggle dataset

The ML model trains on the Kaggle **Solar Radiation Prediction** dataset (NASA HI-SEAS,
`dronio/SolarEnergy`). Two options:

- **Kaggle API** — set credentials (never commit `kaggle.json`), then ingest:
  ```bash
  export KAGGLE_USERNAME=you KAGGLE_KEY=xxxx   # or put them in .env
  curl -X POST http://localhost:8000/api/v1/ml/datasets/ingest-kaggle
  ```
- **Manual** — drop the CSV into `backend/data/raw/kaggle/` (this folder is mounted into
  the container). If neither is present, the API reports **"Kaggle dataset not loaded"** —
  it never silently substitutes data.

## Configure the live weather provider

Open-Meteo is the default and needs **no key**. It is modular — set `WEATHER_PROVIDER`
(and `WEATHER_API_BASE_URL`) in `.env`; Solcast/NASA POWER slots are reserved. Check status:
```bash
curl http://localhost:8000/api/v1/weather/providers/status
```

## Import substation data

```bash
# From OpenStreetMap (Overpass, ODbL) around a point:
curl -X POST http://localhost:8000/api/v1/substations/import \
  -H "Content-Type: application/json" \
  -d '{"latitude":12.97,"longitude":77.59,"radius_km":25}'

# Or from an operator CSV (name,voltage_level,operator,latitude,longitude,district,state,country):
curl -X POST http://localhost:8000/api/v1/substations/import \
  -H "Content-Type: application/json" -d '{"csv_text":"name,latitude,longitude\nX SS,12.9,77.6\n"}'
```
See [docs/LOCATION_AND_SUBSTATION_DATA.md](docs/LOCATION_AND_SUBSTATION_DATA.md).

## Train a model

```bash
curl -X POST "http://localhost:8000/api/v1/ml/datasets/build-augmented?source=kaggle"
curl -X POST "http://localhost:8000/api/v1/ml/train?model_name=auto"
curl http://localhost:8000/api/v1/ml/model/status
```
If Kaggle isn't loaded, build from `source=weather` or `source=synthetic` instead
(labelled accordingly). See [docs/ML_PIPELINE.md](docs/ML_PIPELINE.md).

## Run a prediction

```bash
# Full end-to-end prediction for a site (weather -> forecast -> DSM -> fuzzy risk -> sources)
curl "http://localhost:8000/api/v1/predict/primary-site?latitude=14.10&longitude=77.28&capacity_mw=2050&mode=auto&regulator=KERC/BESCOM"

# Advanced DSM check
curl -X POST http://localhost:8000/api/v1/dsm/advanced-check -H "Content-Type: application/json" \
  -d '{"scheduled_generation_mw":1600,"predicted_generation_mw":1450,"installed_capacity_mw":2050,"regulator":"KERC/BESCOM"}'
```
Full response schema + all endpoints: [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

## Local development (without Docker)

```bash
# Backend (SQLite default, no server needed)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev   # http://localhost:3000
```

## Tests & lint

```bash
cd backend && python -m pytest tests/ -q       # 77 tests, offline (no network)
ruff check app tests && ruff format --check app tests
cd frontend && npm run build                    # type-check + build
```

## Agents

12 deterministic coordinators (no LLM in the numeric path): SourceRegistry, KaggleData,
LiveWeather, LocationData, FeatureEngineering, Forecast, DSMEngine, FuzzyRisk, Explanation,
Orchestrator, APIManagement, Persistence. See [docs/AGENT_WORKFLOWS.md](docs/AGENT_WORKFLOWS.md).

## Tech stack

Python 3.12 · FastAPI · pvlib · scikit-learn · pandas/numpy · SQLAlchemy (SQLite/PostgreSQL) ·
Redis · Next.js 14 / React / Tailwind / Recharts · Docker Compose.

## Documentation

[Real-Data Phase 1.5](docs/REAL_DATA_PHASE1_5.md) ·
[Source Registry](docs/SOURCE_REGISTRY.md) ·
[Formula Sources](docs/FORMULA_SOURCES.md) ·
[DSM Rule Sources](docs/DSM_RULE_SOURCES.md) ·
[Data Source Catalog](docs/DATA_SOURCE_CATALOG.md) ·
[ML Pipeline](docs/ML_PIPELINE.md) ·
[Locations & Substations](docs/LOCATION_AND_SUBSTATION_DATA.md) ·
[Agent Workflows](docs/AGENT_WORKFLOWS.md) ·
[API Reference](docs/API_REFERENCE.md) ·
[Docker Architecture](docs/DOCKER_ARCHITECTURE.md)

## Honesty & limitations

Decision-support estimates, not a settlement of record. Kaggle HI-SEAS data is
irradiance-only (Hawaii); the model predicts irradiance and converts via pvlib. "Actual
injection" is the nowcast until a metered SLDC feed is connected. DSM figures depend on
the live regulatory order for the region/regulator/period and are marked pending until
verified. Synthetic data is a labelled fallback only.
