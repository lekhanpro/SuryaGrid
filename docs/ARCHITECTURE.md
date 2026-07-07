# System Architecture

Technical architecture of SuryaGrid AI — a multi-agent solar forecasting and DSM
risk engine for the Indian power grid.

---

## Table of Contents

1. [System Diagram](#1-system-diagram)
2. [Component Architecture](#2-component-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Data Flow](#4-data-flow)
5. [Agent System](#5-agent-system)
6. [Database Schema](#6-database-schema)
7. [External Integrations](#7-external-integrations)
8. [Deployment Architecture](#8-deployment-architecture)
9. [Security Model](#9-security-model)

---

## 1. System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js 14)                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │Dashboard │ │Prediction│ │   DSM    │ │    ML    │ │Locations │ │Timeline │ │
│  │  Page    │ │   Page   │ │   Page   │ │   Page   │ │   Page   │ │  Page   │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │
│       └─────────────┴────────────┴─────────────┴────────────┴────────────┘      │
│                                    │ HTTP (axios)                                │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     │
                              ┌──────▼──────┐
                              │     ALB     │  (AWS) or localhost:8000 (dev)
                              └──────┬──────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                        │
│                                    │                                             │
│  ┌─────────────────────────────────▼──────────────────────────────────────────┐ │
│  │                         API Router Layer                                    │ │
│  │  routes_predict · routes_dsm · routes_weather · routes_ml · routes_forecast │ │
│  │  routes_locations · routes_energy · routes_settlement · routes_timeline     │ │
│  │  routes_agents · routes_sites · routes_sources · routes_system · routes_... │ │
│  └─────────────────────────────────┬──────────────────────────────────────────┘ │
│                                    │                                             │
│  ┌─────────────────────────────────▼──────────────────────────────────────────┐ │
│  │                         Agent Layer (Deterministic)                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │ │
│  │  │ Orchestrator │──│  Forecast    │──│  DSM Engine  │──│  Fuzzy Risk   │  │ │
│  │  │    Agent     │  │    Agent     │  │    Agent     │  │    Agent      │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────┘  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │ │
│  │  │ Live Weather │  │  Location    │  │ Explanation  │  │  Persistence  │  │ │
│  │  │    Agent     │  │  Data Agent  │  │    Agent     │  │    Agent      │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────┘  │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │ │
│  │  │ Source Reg.  │  │ Kaggle Data  │  │ Feature Eng. │  │  API Mgmt     │  │ │
│  │  │    Agent     │  │    Agent     │  │    Agent     │  │    Agent      │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └───────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                             │
│  ┌────────────────┐  ┌─────────────▼─────────────┐  ┌─────────────────────────┐│
│  │   ML Pipeline  │  │      Service Layer         │  │    DSM Rules Engine     ││
│  │ train · predict│  │ forecast · site · energy   │  │ profiles · slabs · eval ││
│  │ features · reg │  │                            │  │                         ││
│  └────────────────┘  └───────────────────────────┘  └─────────────────────────┘│
│                                    │                                             │
│  ┌─────────────────────────────────▼──────────────────────────────────────────┐ │
│  │                         Data Layer                                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │ │
│  │  │  SQLAlchemy  │  │    Redis     │  │ Data Sources │  │  Providers    │  │ │
│  │  │  (async)     │  │   (cache)    │  │  (registry)  │  │ (Open-Meteo)  │  │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘  └───────┬───────┘  │ │
│  └─────────┼─────────────────┼─────────────────────────────────────┼──────────┘ │
└────────────┼─────────────────┼─────────────────────────────────────┼────────────┘
             │                 │                                      │
      ┌──────▼──────┐  ┌──────▼──────┐                       ┌──────▼──────┐
      │ PostgreSQL  │  │    Redis    │                       │  Open-Meteo │
      │   16        │  │    7        │                       │  (free API) │
      └─────────────┘  └─────────────┘                       └─────────────┘
```

---

## 2. Component Architecture

### Backend Layers

| Layer | Directory | Responsibility |
|-------|-----------|---------------|
| **API** | `app/api/` | FastAPI route handlers, request validation, response formatting |
| **Agents** | `app/agents/` | Business logic coordinators (deterministic, no LLM) |
| **Services** | `app/services/` | Cross-cutting orchestration (forecast, site, energy) |
| **DSM** | `app/dsm/` | Rule profiles, slab engine, source attribution |
| **ML** | `app/ml/` | Training, prediction, feature engineering, provenance |
| **Data Sources** | `app/data_sources/` | Provider abstraction (weather, Kaggle, substations) |
| **Providers** | `app/providers/` | External API clients (Open-Meteo) |
| **Database** | `app/db/` | Models, repository, migrations (SQLAlchemy async) |
| **Core** | `app/core/` | Logging, rate limiting, scheduler, exceptions |
| **RL** | `app/rl/` | Phase 1 reinforcement learning (retained, not extended) |

### Frontend Structure

| Directory | Contents |
|-----------|----------|
| `app/` | Next.js app router pages (12 pages) |
| `components/` | Reusable UI components |
| `components/charts/` | Recharts visualizations (MiniTimeline, DeviationBar) |
| `components/cards/` | Data display cards (MetricCard, PenaltyStatusCard) |
| `components/svg/` | 3D SVG illustrations (SolarPanel, RiskGauge, EnergyFlow) |
| `components/layout/` | Sidebar, Topbar navigation |
| `lib/` | API client, types, utility functions |

---

## 3. Tech Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | FastAPI | ≥0.111 | Async REST API with auto-docs |
| Runtime | Python | 3.12 | Modern async/typing features |
| Solar Physics | pvlib | ≥0.11 | Solar position, irradiance transposition, PVWatts |
| ML | scikit-learn | ≥1.5 | Gradient boosting / random forest models |
| Data | pandas, numpy | ≥2.2, ≥2.1 | Numerical computation |
| ORM | SQLAlchemy | ≥2.0 (async) | Database abstraction |
| Migrations | Alembic | ≥1.13 | Schema versioning |
| DB (prod) | PostgreSQL | 16 | Primary persistence |
| DB (dev) | SQLite | via aiosqlite | Zero-config local development |
| Cache | Redis | 7 | Weather caching, rate limiting |
| HTTP Client | httpx | ≥0.27 | Async external API calls |
| Scheduling | APScheduler | ≥3.10 | Optional real-time ingestion |
| Validation | Pydantic | ≥2.9 | Request/response schemas |
| RL (legacy) | Gymnasium | ≥1.0 | Digital twin environment |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 14 | App router, SSR-capable |
| UI | React | 18 | Component-based UI |
| Styling | Tailwind CSS | 3.4 | Utility-first CSS |
| Charts | Recharts | 2.12 | Data visualization |
| HTTP | axios | 1.7 | API client |
| Types | TypeScript | 5.5 | Type safety |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containers | Docker Compose | Local full-stack development |
| Prod Backend | ECS Fargate + ALB | Serverless container hosting |
| Prod Frontend | S3 + CloudFront | Global static CDN |
| Prod DB | RDS PostgreSQL | Managed database |
| Prod Cache | ElastiCache Redis | Managed caching |
| CI | GitHub Actions | Lint, test, build on every push |
| CD | GitHub Actions | OIDC-based deploy to AWS |
| IaC | Terraform | Infrastructure provisioning |

---

## 4. Data Flow

### Weather Data Flow

```
Open-Meteo API (free, hourly)
       │
       ▼
LiveWeatherProvider (httpx client)
       │
       ▼
Redis Cache (1h TTL for forecast, 15min for current)
       │
       ▼
LiveWeatherAgent → WeatherPoint dataclass
       │
       ▼
ForecastAgent (consumes GHI/DNI/DHI/temp/cloud/wind)
```

### ML Training Data Flow

```
Kaggle Solar Dataset (NASA HI-SEAS)     Open-Meteo Historical
        │                                        │
        ▼                                        ▼
KaggleSolarProvider                    LiveWeatherProvider
        │                                        │
        └────────────────┬───────────────────────┘
                         │
                         ▼
              DatasetBuilder (build_ml_datasets.py)
                         │
                         ▼
              Feature Engineering (temporal, solar, weather)
                         │
                         ▼
              Model Training (scikit-learn)
                         │
                         ▼
              Model Registry (versioned .joblib files)
                         │
                         ▼
              Provenance Record (what data, what model, when)
```

### Prediction Data Flow

```
API Request (lat, lon, capacity, mode, regulator)
       │
       ▼
Site Resolution (DB lookup / create)
       │
       ├── Nearest Substation (PostGIS-style query)
       │
       ▼
Live Weather Fetch (Redis → Open-Meteo → Synthetic fallback)
       │
       ▼
Forecast (pvlib formula / ML model / hybrid)
       │
       ├── predicted_generation_mw
       └── clearsky_generation_mw (default schedule)
       │
       ▼
DSM Engine (resolve profile → compute deviation → apply slabs)
       │
       ├── deviation_percent, penalty_status, estimated_charge
       │
       ▼
Fuzzy Risk (breach + uncertainty + volatility → 0-100 score)
       │
       ▼
Explanation Agent (human-readable summary)
       │
       ▼
Source Registry (attach citations)
       │
       ▼
Persistence Agent (save to PostgreSQL)
       │
       ▼
API Response (complete JSON with all fields)
```

---

## 5. Agent System

### Design Philosophy

- **Deterministic**: No LLM in the numeric path. Agents are coordinating functions.
- **Composable**: Each agent has a single responsibility and can be tested in isolation.
- **Transparent**: Every value is traceable to a formula, dataset, or regulatory source.

### Agent Catalog

| Agent | File | Role | Key Method |
|-------|------|------|------------|
| **Orchestrator** | `orchestrator_agent.py` | Sequences all other agents | `run_full()`, `evaluate()` |
| **Forecast** | `forecast_agent.py` | pvlib physics + ML prediction | `forecast_timeline()` |
| **Live Weather** | `live_weather_agent.py` | Weather fetch with caching | `latest()`, `forecast()` |
| **DSM Engine** | `dsm_engine_agent.py` | Advanced DSM evaluation | `evaluate()`, `resolve_profile()` |
| **DSM Classifier** | `dsm_classifier_agent.py` | Simple threshold DSM | `classify()` |
| **Fuzzy Risk** | `fuzzy_risk_agent.py` | Fuzzy inference risk scoring | `score()` |
| **Explanation** | `explanation_agent.py` | Human-readable summaries | `explain()` |
| **Risk** | `risk_agent.py` | Simple linear risk (legacy) | `score()` |
| **Location Data** | `location_data_agent.py` | Substation + site data | `nearest()`, `coverage()` |
| **Kaggle Data** | `kaggle_data_agent.py` | Dataset ingestion | `ingest()` |
| **Feature Engineering** | `feature_engineering_agent.py` | ML feature pipeline | `build_features()` |
| **Source Registry** | `source_registry_agent.py` | Citation management | `cite()`, `register()` |
| **Persistence** | `persistence_agent.py` | DB writes | `save_forecast_point()` |
| **API Management** | `api_management_agent.py` | Provider status | `check_providers()` |
| **Reward** | `reward_agent.py` | RL reward computation | `compute()` |

### Orchestration Pattern

```python
# OrchestratorAgent.run_full() pseudocode:

site        = resolve_site(db, params)
substation  = nearest_substation(db, site.lat, site.lon)
weather     = LiveWeatherAgent.latest(site.lat, site.lon)
forecast    = ForecastAgent.forecast_timeline(site, weather, mode)
scheduled   = user_input OR forecast.clearsky
dsm_result  = DSMEngineAgent.evaluate(profile, scheduled, predicted, capacity)
fuzzy       = FuzzyRiskAgent.score(deviation, confidence, cloud_cover)
explanation = ExplanationAgent.explain(all_results)
sources     = SourceRegistry.cite(all_source_ids)
             PersistenceAgent.save(db, results)
return       complete_response
```

---

## 6. Database Schema

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `sites` | Registered solar sites | id, name, lat, lon, capacity_mw, timezone |
| `forecast_points` | Persisted predictions | site_id, timestamp, predicted_mw, scheduled_mw, confidence |
| `weather_readings` | Cached weather data | site_id, timestamp, ghi, dni, dhi, temp, cloud, wind |
| `dsm_results` | DSM evaluation history | site_id, profile_id, deviation_%, penalty_status, charge |
| `dsm_rule_profiles` | Configurable DSM rules | id, name, regulator, region, tolerance_%, denominator |
| `dsm_rule_bands` | Slab charge rates | profile_id, min_%, max_%, rate, direction |
| `substations` | Grid substations | id, name, lat, lon, voltage, operator, source |
| `ml_models` | Model registry | id, name, version, metrics, trained_at |
| `data_sources` | Provider catalog | id, name, type, status, last_fetched |

### Persistence Strategy

- **PostgreSQL** (production): Full ACID, async via asyncpg
- **SQLite** (development): Zero-config, async via aiosqlite
- **Redis**: Weather cache + rate limiting (not persistence)
- **File system**: ML models (.joblib), datasets (.parquet, .csv)

---

## 7. External Integrations

| Service | Purpose | Auth | Fallback |
|---------|---------|------|----------|
| **Open-Meteo** | Live hourly weather + forecast | None (free, key-less) | Synthetic provider (labeled) |
| **Kaggle** | Training dataset (NASA HI-SEAS) | Optional API key | Manual CSV placement |
| **OpenStreetMap Overpass** | Substation geospatial data | None (free, ODbL) | Operator CSV import |

### Open-Meteo Integration

```
GET https://api.open-meteo.com/v1/forecast
  ?latitude=14.1&longitude=77.28
  &hourly=shortwave_radiation,direct_normal_irradiance,
          diffuse_radiation,temperature_2m,
          cloudcover,windspeed_10m,relativehumidity_2m,
          surface_pressure,precipitation_probability
  &timezone=Asia/Kolkata
  &forecast_days=7
```

Cached in Redis by (lat, lon, hour bucket). 15-min TTL for "current", 1h for forecast.

---

## 8. Deployment Architecture

### Local Development

```bash
cd backend && uvicorn app.main:app --reload --port 8000  # SQLite, no Redis needed
cd frontend && npm run dev                                # localhost:3000
```

### Docker Compose (Full Stack)

```
docker compose up --build
  → postgres:5432 + redis:6379 + backend:8000 + frontend:3000
```

### AWS Production

```
┌──────────────────────────────────────────────────────────────────┐
│  CloudFront (CDN) ← S3 Bucket (frontend static export)          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  VPC (ap-south-1, Mumbai)                                        │
│                                                                  │
│  Public Subnets:                                                 │
│    ┌─── ALB (Application Load Balancer) ───┐                     │
│    │    Health check: /api/v1/health        │                     │
│    └───────────────────┬───────────────────┘                     │
│                        │                                         │
│  Private Subnets:      │                                         │
│    ┌───────────────────▼───────────────────┐                     │
│    │  ECS Fargate Service                  │                     │
│    │  (backend container, 0.5 vCPU, 1GB)   │                     │
│    └──────────┬────────────────┬───────────┘                     │
│               │                │                                 │
│    ┌──────────▼─────┐  ┌──────▼──────────┐                      │
│    │ RDS PostgreSQL │  │ ElastiCache Redis│                      │
│    │ (db.t4g.micro) │  │ (cache.t4g.micro)│                      │
│    └────────────────┘  └─────────────────┘                      │
│                                                                  │
│    NAT Gateway (outbound: Open-Meteo, Kaggle)                    │
└──────────────────────────────────────────────────────────────────┘
```

See [docs/DEPLOYMENT.md](DEPLOYMENT.md) for full deployment guide.

---

## 9. Security Model

### Current State (Phase 1.5)

| Layer | Implementation |
|-------|---------------|
| Auth | JWT placeholder (not enforced) |
| CORS | Restricted to frontend origin |
| Rate Limiting | Redis-backed per-IP throttle (60 req/min) |
| Data Isolation | Private subnets for DB/cache (AWS) |
| Secrets | Environment variables, never committed |
| Input Validation | Pydantic schemas on all endpoints |
| Container Security | ECR image scanning on push |

### Planned (Production Hardening)

- HTTPS (ACM certificate + ALB HTTPS listener)
- AWS Secrets Manager for DB credentials
- WAF on ALB (rate limiting, bot protection)
- IAM least-privilege for ECS tasks
- VPC endpoints (eliminate NAT for AWS services)
- Audit logging (CloudTrail)

---

## Key Design Principles

1. **Honesty over convenience** — never silently substitute data. Synthetic is labeled.
   Unverified DSM rates are marked. Backend-offline is shown, not hidden.

2. **Deterministic numeric path** — no LLM, no random seed in production. Same inputs
   always produce same outputs.

3. **Source traceability** — every formula, threshold, dataset, and rate links back to a
   citation. The source registry is a first-class subsystem.

4. **Graceful degradation** — works without Redis, without Kaggle, without ML models,
   without substations. Each missing piece reduces capability but doesn't crash.

5. **Regulation-aware** — DSM rules are not hardcoded. Profiles are database-backed,
   configurable per region/regulator, with slab-based charging.
