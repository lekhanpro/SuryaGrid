# Suryagrid AI — Phase 1

**Solar Nowcasting + DSM Penalty Prediction + Fuzzy Risk Engine**

## What is Suryagrid AI Phase 1?

Suryagrid AI is a multi-agent solar energy monitoring platform. Phase 1 is the operational foundation that:

- Predicts solar generation from weather/irradiance conditions
- Compares predicted generation against scheduled/agreement MW
- Classifies DSM (Deviation Settlement Mechanism) threshold violations
- Assigns fuzzy risk levels (LOW / MEDIUM / HIGH / CRITICAL)
- Estimates penalty costs for grid deviations
- Provides timeline and summary views for operational monitoring

## Why Synthetic Data in Phase 1?

Phase 1 uses deterministic synthetic weather data to validate the complete prediction pipeline without external API dependencies. The system architecture supports future integration with Solcast, Open-Meteo, and NASA POWER through a provider abstraction layer. All formulas and logic are production-ready — only the data source changes in later phases.

## Architecture

```
Solar Irradiance + Weather/Cloud Data + Site Configuration
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  SyntheticDataAgent (Phase 1 local data provider)   │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  ForecastAgent (solar generation prediction)         │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  DSMClassifierAgent (deviation + penalty logic)      │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  FuzzyRiskAgent (risk scoring 0-100)                 │
└───────────────────────┬─────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────┐
│  ExplanationAgent (human-readable analysis)          │
└───────────────────────┬─────────────────────────────┘
                        ▼
          FastAPI REST API + Next.js Dashboard
```

## Agent Pipeline

| Agent | Responsibility |
|-------|---------------|
| SyntheticDataAgent | Generates simulated weather/irradiance/schedule data |
| ForecastAgent | Predicts solar generation using physics-based formula |
| DSMClassifierAgent | Compares predicted vs scheduled MW, flags penalty risk |
| FuzzyRiskAgent | Assigns risk level based on deviation + conditions |
| ExplanationAgent | Produces human-readable analysis text |
| OrchestratorAgent | Coordinates the full pipeline in sequence |

## Run Commands

### Backend (local)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API Docs: http://localhost:8000/docs

### Frontend (local)

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

### Docker Compose (full stack)

```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | System health check |
| POST | `/api/v1/sites` | Create solar site |
| GET | `/api/v1/sites` | List all sites |
| GET | `/api/v1/sites/{id}` | Get site details |
| POST | `/api/v1/synthetic-data/generate` | Generate weather data |
| GET | `/api/v1/synthetic-data/{site_id}` | Retrieve generated data |
| POST | `/api/v1/predict` | Run full prediction cycle |
| POST | `/api/v1/dsm/check` | Standalone DSM check |
| GET | `/api/v1/timeline/{site_id}` | 24h prediction timeline |
| GET | `/api/v1/summary/{site_id}` | Day summary statistics |

## Test Commands

```bash
cd backend
python tests/test_phase1_acceptance.py    # 12 acceptance tests
python tests/test_forecast_agent.py       # Forecast formula tests
python tests/test_dsm_classifier.py       # DSM logic tests
python tests/test_fuzzy_risk.py           # Risk scoring tests
python tests/test_orchestrator.py         # Pipeline tests
python tests/test_api.py                  # API integration tests
```

## Phase 1 Success Criteria

1. Backend starts successfully
2. Synthetic weather data generation works
3. Solar prediction formula is deterministic and tested
4. DSM penalty classification works correctly
5. Fuzzy risk scoring assigns correct levels
6. Explanation text is generated
7. Timeline API returns graph-ready data
8. Summary API returns correct totals
9. No divide-by-zero on invalid schedules
10. Prediction never exceeds solar capacity
11. API response schema is stable and timestamped
12. No external API keys required
13. All tests pass

## What is NOT Included in Phase 1

- Real weather API integrations (Solcast, Open-Meteo, NASA POWER)
- Reinforcement learning / reward engine
- Blockchain settlement
- SCADA / hardware integration
- Multi-tenant authentication (Auth0/Keycloak)
- Energy trading platform
- Cloud camera system
- Production deployment infrastructure

These are planned for later phases and the architecture supports their addition.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Agents**: Python classes (LangGraph-ready structure)
- **Testing**: pytest, httpx ASGI transport
- **Deployment**: Docker Compose
