<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 190" width="100%" height="190" role="img" aria-label="Suryagrid AI Phase 1 banner">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#07192f"/>
      <stop offset="45%" stop-color="#0b3a67"/>
      <stop offset="100%" stop-color="#1f6feb"/>
    </linearGradient>
    <linearGradient id="sun" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ffe08a"/>
      <stop offset="100%" stop-color="#ff8c42"/>
    </linearGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#001" flood-opacity="0.22"/>
    </filter>
  </defs>
  <rect width="1100" height="190" rx="18" fill="url(#sky)"/>
  <circle cx="940" cy="65" r="48" fill="url(#sun)" opacity="0.98"/>
  <g stroke="#ffd166" stroke-width="4" stroke-linecap="round" opacity="0.8">
    <line x1="940" y1="2" x2="940" y2="19"/>
    <line x1="940" y1="111" x2="940" y2="128"/>
    <line x1="877" y1="65" x2="860" y2="65"/>
    <line x1="1003" y1="65" x2="1020" y2="65"/>
    <line x1="895" y1="20" x2="882" y2="8"/>
    <line x1="985" y1="20" x2="998" y2="8"/>
  </g>
  <g filter="url(#soft)">
    <rect x="45" y="118" width="90" height="48" rx="4" fill="#0b2545" stroke="#5fd3f3" stroke-width="2" transform="skewX(-8)"/>
    <rect x="150" y="118" width="90" height="48" rx="4" fill="#0b2545" stroke="#5fd3f3" stroke-width="2" transform="skewX(-8)"/>
    <rect x="255" y="118" width="90" height="48" rx="4" fill="#0b2545" stroke="#5fd3f3" stroke-width="2" transform="skewX(-8)"/>
  </g>
  <text x="44" y="55" font-family="Segoe UI, Arial, sans-serif" font-size="38" font-weight="800" fill="#ffffff">Suryagrid AI Phase 1</text>
  <text x="46" y="88" font-family="Segoe UI, Arial, sans-serif" font-size="18" fill="#b9ddff">Agentic Solar Nowcasting + DSM Penalty Prediction + Fuzzy Risk Engine</text>
  <text x="46" y="108" font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="#d4ecff">Toy-data MVP designed as the base layer for the full Solar Multi-Agent Platform</text>
</svg>

# Suryagrid AI Phase 1 — Advanced Implementation Markdown

**Document type:** Claude-ready implementation specification  
**Project:** Suryagrid AI / Solar Multi-Agent Platform  
**Phase:** Phase 1 MVP foundation  
**Data mode:** Toy/synthetic weather, cloud, irradiance, schedule and solar-generation data  
**Goal:** Build a real codebase foundation that later expands into Solcast/Open-Meteo/NASA POWER, pvlib production modelling, plant/SCADA connectors, RL reward engine and multi-tenant deployment.

---

## 0. How Claude Should Use This File

Claude Code / Kiro / Copilot should treat this file as the **single source of truth** for Phase 1 implementation.

### Mandatory rules for Claude

1. Build **Phase 1 only** first.
2. Use **toy data**, not real APIs.
3. Keep all math deterministic and testable.
4. Do not let an LLM calculate DSM values or solar power values.
5. Agents can start as Python classes, then later become LangGraph nodes.
6. Keep the same tech-stack direction as the larger platform.
7. Include security, API management, frontend, backend, data model, fuzzy logic and future extensibility from the beginning.
8. Write code so later phases can plug in Solcast, Open-Meteo, NASA POWER, SCADA, RL and real settlement logic without rewriting the system.

### Phase 1 one-line objective

> Build a toy-data based agentic solar nowcasting system that predicts solar generation, compares it with scheduled/agreement MW, calculates DSM deviation, assigns fuzzy risk, estimates penalty cost, explains the result and displays everything through FastAPI + Next.js.

---

## 1. Project Interpretation

The uploaded main project plan describes a three-level solar platform with:

- **Level 1:** Data foundation
- **Level 2:** Intelligence with six agents plus RL
- **Level 3:** Experience and integration

Phase 1 must become the base implementation of that platform, but with a reduced MVP scope.

### Phase 1 keeps these concepts

| Main project concept | Phase 1 implementation |
|---|---|
| Solcast / Open-Meteo / NASA POWER | Mock provider interface only; use toy data now |
| Six agents | Implement as Python classes and service modules |
| API agent | Implement API management, validation, rate limiting and mock-provider abstraction |
| Reward / penalty engine | Implement DSM penalty calculation only; keep reward/RL stub for later |
| RL | Not active in Phase 1; design extension point only |
| pvlib | Add dependency/future-ready service, but toy formula is default |
| Dashboard | Next.js dashboard with cards and charts |
| Security | JWT, role-based checks, input validation, audit logging |
| Time-series DB | PostgreSQL schema designed for future TimescaleDB |
| Plant/SCADA | Interface stub only, no real connector yet |

---

## 2. Phase 1 System Picture

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 360" width="100%" height="360" role="img" aria-label="Phase 1 system picture">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#1f6feb"/></marker>
    <style>
      .box{fill:#ffffff;stroke:#1f6feb;stroke-width:2;rx:12;filter:url(#shadow)}
      .title{font-family:Segoe UI,Arial,sans-serif;font-size:15px;font-weight:700;fill:#0b2545}
      .txt{font-family:Segoe UI,Arial,sans-serif;font-size:12px;fill:#33475b}
      .head{font-family:Segoe UI,Arial,sans-serif;font-size:18px;font-weight:800;fill:#0b2545}
    </style>
    <filter id="shadow"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-opacity="0.15"/></filter>
  </defs>
  <rect width="1080" height="360" rx="18" fill="#eef6ff"/>
  <text x="35" y="34" class="head">Suryagrid AI Phase 1 MVP Loop</text>

  <rect x="35" y="70" width="170" height="95" class="box"/>
  <text x="55" y="98" class="title">Toy Data Agent</text>
  <text x="55" y="122" class="txt">weather, cloud</text>
  <text x="55" y="140" class="txt">irradiance, schedule</text>

  <rect x="245" y="70" width="175" height="95" class="box"/>
  <text x="265" y="98" class="title">Forecast Agent</text>
  <text x="265" y="122" class="txt">formula model now</text>
  <text x="265" y="140" class="txt">pvlib/ML later</text>

  <rect x="460" y="70" width="175" height="95" class="box"/>
  <text x="480" y="98" class="title">DSM Classifier</text>
  <text x="480" y="122" class="txt">deviation MW/%</text>
  <text x="480" y="140" class="txt">penalty/no penalty</text>

  <rect x="675" y="70" width="170" height="95" class="box"/>
  <text x="695" y="98" class="title">Fuzzy Risk Agent</text>
  <text x="695" y="122" class="txt">LOW/MED/HIGH</text>
  <text x="695" y="140" class="txt">CRITICAL score</text>

  <rect x="885" y="70" width="160" height="95" class="box"/>
  <text x="905" y="98" class="title">Dashboard/API</text>
  <text x="905" y="122" class="txt">FastAPI + Next.js</text>
  <text x="905" y="140" class="txt">charts + report</text>

  <line x1="205" y1="118" x2="240" y2="118" stroke="#1f6feb" stroke-width="3" marker-end="url(#arrow)"/>
  <line x1="420" y1="118" x2="455" y2="118" stroke="#1f6feb" stroke-width="3" marker-end="url(#arrow)"/>
  <line x1="635" y1="118" x2="670" y2="118" stroke="#1f6feb" stroke-width="3" marker-end="url(#arrow)"/>
  <line x1="845" y1="118" x2="880" y2="118" stroke="#1f6feb" stroke-width="3" marker-end="url(#arrow)"/>

  <rect x="120" y="230" width="840" height="82" rx="12" fill="#0b2545" opacity="0.96"/>
  <text x="150" y="260" font-family="Segoe UI,Arial,sans-serif" font-size="17" font-weight="700" fill="#ffffff">Core output</text>
  <text x="150" y="287" font-family="Segoe UI,Arial,sans-serif" font-size="14" fill="#d4ecff">Predicted Generation MW + Scheduled MW + DSM Deviation + Penalty Cost + Fuzzy Risk + Explanation + Timeline</text>
</svg>

---

## 3. System Requirements

### 3.1 Functional requirements

| ID | Requirement | Phase 1 behavior |
|---|---|---|
| FR-01 | Create solar site | User can create site with capacity, location and config |
| FR-02 | Generate toy data | System creates synthetic weather/cloud/irradiance data |
| FR-03 | Predict generation | Forecast Agent calculates predicted generation MW |
| FR-04 | Compare with schedule | DSM Agent compares predicted MW with scheduled MW |
| FR-05 | Penalty classification | Output `NO_PENALTY` or `PENALTY_RISK` |
| FR-06 | Fuzzy risk | Output risk score and level |
| FR-07 | Explanation | Human-readable reason for result |
| FR-08 | Timeline | Chart-ready predicted/scheduled/actual data |
| FR-09 | API docs | FastAPI Swagger UI should work |
| FR-10 | Frontend | Dashboard with cards, charts and forms |
| FR-11 | Security | JWT auth, RBAC, audit logs, rate limiting |
| FR-12 | Future compatibility | Provider and RL stubs ready |

### 3.2 Non-functional requirements

| Category | Requirement |
|---|---|
| Correctness | Deterministic formulas must be unit tested |
| Safety | No unauthenticated control or integration endpoints |
| Cost control | No LLM call required for core Phase 1 calculations |
| Extensibility | Real providers can replace toy provider through interface |
| Observability | Logs for every prediction and DSM decision |
| Maintainability | Clear folder structure, typed schemas, modular services |
| Performance | Prediction endpoint should return quickly for one site |
| Reliability | Validation errors should be clear and never crash the app |

---

## 4. Tech Stack Lock

Use this stack for Phase 1 to match the larger project direction.

| Layer | Tooling | Phase 1 usage |
|---|---|---|
| Language | Python 3.12 | Backend, agents, data generation, formulas |
| API | FastAPI + Uvicorn | Main REST API |
| Validation | Pydantic v2 | Request/response schemas |
| DB ORM | SQLAlchemy 2 + Alembic | Database models and migrations |
| Data | Pandas + NumPy | Toy data generation and timelines |
| Solar math | pvlib | Installed and scaffolded; toy formula default |
| Agent graph | LangGraph + LangChain tools | Optional graph wrapper; Python classes first |
| ML future | scikit-learn | Optional baseline model later |
| Database | PostgreSQL | Store sites, weather, schedules, DSM results |
| Time-series future | TimescaleDB extension | Future optimization for readings |
| Cache/rate limit | Redis | Rate limiting and cache foundation |
| Frontend | Next.js + React + TypeScript | Dashboard |
| Styling | Tailwind CSS | UI |
| Charts | Recharts or ECharts | Timeline, DSM, weather charts |
| Auth | JWT now; Auth0/Clerk/Keycloak later | Role-based access |
| Secrets | `.env` now; Vault/AWS Secrets Manager later | Safe config |
| Deployment | Docker + Docker Compose | Local dev |
| CI/CD | GitHub Actions | Lint/test/build foundation |

---

## 5. Phase 1 Mermaid — Three-Level Architecture

Save as: `diagrams/01_three_level_architecture.mmd`

```mermaid
flowchart TB
  subgraph L3["LEVEL 3 — Experience & Integration"]
    FE["Next.js Dashboard"]
    API["FastAPI REST API"]
    DOCS["Swagger / OpenAPI"]
    ALERT["Reports & Alerts Stub"]
  end

  subgraph L2["LEVEL 2 — Intelligence & Agents"]
    ORC["Orchestrator Agent"]
    DATA["Toy Data Agent"]
    FORE["Forecast Agent"]
    DSM["DSM Classifier Agent"]
    FUZZ["Fuzzy Risk Agent"]
    EXPL["Explanation Agent"]
    APIM["API Management Agent"]
    SEC["Security Agent"]
    RLSTUB["Reward/RL Stub"]
  end

  subgraph L1["LEVEL 1 — Data Foundation"]
    PG["PostgreSQL"]
    TS["TimescaleDB-ready schema"]
    REDIS["Redis cache/rate limit"]
    CSV["Toy CSV export"]
    MOCK["Mock Weather/Cloud Provider"]
  end

  FE --> API
  DOCS --> API
  API --> SEC
  API --> APIM
  APIM --> ORC
  ORC --> DATA --> FORE --> DSM --> FUZZ --> EXPL
  DSM --> RLSTUB
  DATA --> PG
  FORE --> PG
  DSM --> PG
  FUZZ --> PG
  APIM --> REDIS
  MOCK --> DATA
  PG --> TS
  PG --> CSV
  EXPL --> API --> FE
```

---

## 6. Phase 1 Mermaid — Agent Workflow

Save as: `diagrams/02_agent_workflow.mmd`

```mermaid
flowchart LR
  START((Start)) --> AUTH{JWT valid?}
  AUTH -- No --> DENY["Reject request"]
  AUTH -- Yes --> RATE{Rate limit ok?}
  RATE -- No --> TOO["429 Too Many Requests"]
  RATE -- Yes --> ORC["Orchestrator Agent"]

  ORC --> DATA["Toy Data Agent"]
  DATA --> Q1{Data valid?}
  Q1 -- No --> FIXDATA["Regenerate / validate toy data"] --> DATA
  Q1 -- Yes --> FORE["Forecast Agent"]

  FORE --> Q2{Prediction in bounds?}
  Q2 -- No --> CLAMP["Clamp to 0..capacity"] --> DSM
  Q2 -- Yes --> DSM["DSM Classifier Agent"]

  DSM --> Q3{Schedule valid?}
  Q3 -- No --> BAD["INVALID_SCHEDULE"]
  Q3 -- Yes --> FUZZ["Fuzzy Risk Agent"]

  FUZZ --> EXPL["Explanation Agent"]
  EXPL --> SAVE["Save DSM result + audit log"]
  SAVE --> RETURN["Return JSON + dashboard data"]
  RETURN --> END((End))
```

---

## 7. Phase 1 Mermaid — Sequence Diagram

Save as: `diagrams/03_prediction_sequence.mmd`

```mermaid
sequenceDiagram
  autonumber
  actor User
  participant FE as Next.js Dashboard
  participant API as FastAPI
  participant SEC as Security Agent
  participant APIM as API Management Agent
  participant ORC as Orchestrator Agent
  participant DATA as Toy Data Agent
  participant FORE as Forecast Agent
  participant DSM as DSM Classifier Agent
  participant FUZZ as Fuzzy Risk Agent
  participant EXPL as Explanation Agent
  participant DB as PostgreSQL

  User->>FE: Submit prediction request
  FE->>API: POST /api/v1/predict
  API->>SEC: Verify JWT + role
  SEC-->>API: allowed
  API->>APIM: Validate request + rate limit
  APIM-->>API: ok
  API->>ORC: run_prediction_cycle(payload)
  ORC->>DATA: get toy weather/cloud/schedule
  DATA->>DB: read/write toy data
  DATA-->>ORC: normalized input
  ORC->>FORE: predict_generation(input)
  FORE-->>ORC: predicted_generation_mw + confidence
  ORC->>DSM: classify(predicted, scheduled, threshold)
  DSM-->>ORC: deviation + penalty status + cost
  ORC->>FUZZ: calculate fuzzy risk
  FUZZ-->>ORC: score + level
  ORC->>EXPL: explain result
  EXPL-->>ORC: explanation text
  ORC->>DB: save prediction, DSM result, audit log
  ORC-->>API: complete result
  API-->>FE: JSON response
  FE-->>User: Cards + charts + explanation
```

---

## 8. Phase 1 Mermaid — State Machine

Save as: `diagrams/04_state_machine.mmd`

```mermaid
stateDiagram-v2
  [*] --> RequestReceived
  RequestReceived --> AuthCheck
  AuthCheck --> Rejected: invalid token / role
  AuthCheck --> RateLimitCheck: valid
  RateLimitCheck --> Rejected: over limit
  RateLimitCheck --> DataPreparation: allowed
  DataPreparation --> DataQualityCheck
  DataQualityCheck --> DataPreparation: missing/outlier toy data
  DataQualityCheck --> Forecasting: pass
  Forecasting --> PredictionBoundsCheck
  PredictionBoundsCheck --> Forecasting: severe formula error
  PredictionBoundsCheck --> DSMClassification: pass or clamped
  DSMClassification --> InvalidSchedule: schedule <= 0
  DSMClassification --> FuzzyRiskScoring: valid schedule
  FuzzyRiskScoring --> ExplanationGeneration
  ExplanationGeneration --> PersistResults
  PersistResults --> PublishResponse
  PublishResponse --> [*]
  Rejected --> [*]
  InvalidSchedule --> PersistResults
```

---

## 9. Phase 1 Mermaid — Data Model ER Diagram

Save as: `diagrams/05_data_model_er.mmd`

```mermaid
erDiagram
  USER ||--o{ AUDIT_LOG : performs
  USER ||--o{ SITE_ACCESS : has
  SITE ||--o{ SITE_ACCESS : grants
  SITE ||--o{ TOY_WEATHER_READING : has
  SITE ||--o{ GENERATION_READING : has
  SITE ||--o{ SCHEDULE_WINDOW : has
  SITE ||--o{ DSM_RESULT : has
  SCHEDULE_WINDOW ||--o{ DSM_RESULT : evaluated_by

  USER {
    uuid id PK
    string email
    string password_hash
    string role
    timestamp created_at
  }

  SITE {
    uuid id PK
    string name
    float latitude
    float longitude
    string timezone
    float capacity_mw
    float panel_efficiency
    float tilt
    float azimuth
    timestamp created_at
  }

  SITE_ACCESS {
    uuid id PK
    uuid user_id FK
    uuid site_id FK
    string role
  }

  TOY_WEATHER_READING {
    uuid id PK
    uuid site_id FK
    timestamp ts
    float irradiance_w_m2
    float cloud_cover_percent
    float temperature_c
    float humidity_percent
    float wind_speed_mps
    float rain_probability_percent
    int quality_flag
  }

  GENERATION_READING {
    uuid id PK
    uuid site_id FK
    timestamp ts
    float actual_generation_mw
    float predicted_generation_mw
    string source
  }

  SCHEDULE_WINDOW {
    uuid id PK
    uuid site_id FK
    timestamp window_start
    timestamp window_end
    float scheduled_generation_mw
    float allowed_dsm_threshold_percent
    float penalty_rate_per_mw
  }

  DSM_RESULT {
    uuid id PK
    uuid site_id FK
    uuid schedule_window_id FK
    timestamp ts
    float predicted_generation_mw
    float scheduled_generation_mw
    float deviation_mw
    float deviation_percent
    string penalty_status
    float estimated_penalty_cost
    float fuzzy_risk_score
    string fuzzy_risk_level
    float confidence_score
    string explanation
  }

  AUDIT_LOG {
    uuid id PK
    uuid user_id FK
    string action
    string entity_type
    uuid entity_id
    json details
    string ip_address
    timestamp created_at
  }
```

---

## 10. Phase 1 Mermaid — Security Flow

Save as: `diagrams/06_security_flow.mmd`

```mermaid
flowchart TD
  REQ["Incoming API request"] --> CORS["CORS + HTTPS ready"]
  CORS --> JWT{JWT present?}
  JWT -- No --> R401["401 Unauthorized"]
  JWT -- Yes --> VERIFY{Signature valid?}
  VERIFY -- No --> R401
  VERIFY -- Yes --> ROLE{Role allowed?}
  ROLE -- No --> R403["403 Forbidden"]
  ROLE -- Yes --> SITE{Site access allowed?}
  SITE -- No --> R403
  SITE -- Yes --> RATE{Redis rate limit ok?}
  RATE -- No --> R429["429 Too Many Requests"]
  RATE -- Yes --> VALIDATE["Pydantic validation"]
  VALIDATE --> OK["Run service / agent workflow"]
  OK --> AUDIT["Write audit log"]
  AUDIT --> RESPONSE["Return response"]
```

---

## 11. Phase 1 Mermaid — API Management and Future Provider Failover

Save as: `diagrams/07_api_management_future.mmd`

```mermaid
flowchart LR
  REQ["Data request"] --> APIM["API Management Agent"]
  APIM --> PHASE1{Phase 1?}
  PHASE1 -- Yes --> MOCK["Mock Toy Provider"]
  PHASE1 -- No --> QUOTA{Primary quota ok?}
  QUOTA -- Yes --> SOL["Solcast Provider"]
  QUOTA -- No --> FB1["Open-Meteo Fallback"]
  SOL --> OK{Response ok?}
  OK -- Yes --> NORM["Normalize canonical schema"]
  OK -- No --> FB1
  FB1 --> OK2{Response ok?}
  OK2 -- Yes --> NORM
  OK2 -- No --> FB2["NASA POWER Fallback"]
  FB2 --> NORM
  NORM --> CACHE["Redis cache"]
  CACHE --> DB["PostgreSQL/Timescale-ready store"]
```

---

## 12. Phase 1 Mermaid — Fuzzy Logic Flow

Save as: `diagrams/08_fuzzy_logic_flow.mmd`

```mermaid
flowchart TD
  INPUT["DSM + weather inputs"] --> DEV["Deviation percentage"]
  INPUT --> CLOUD["Cloud cover percentage"]
  INPUT --> IRR["Irradiance W/m²"]
  INPUT --> CONF["Confidence score"]

  DEV --> SCORE["Weighted risk score"]
  CLOUD --> SCORE
  IRR --> SCORE
  CONF --> SCORE

  SCORE --> LOW{score < 25?}
  LOW -- Yes --> L["LOW"]
  LOW -- No --> MED{score < 50?}
  MED -- Yes --> M["MEDIUM"]
  MED -- No --> HIGH{score < 75?}
  HIGH -- Yes --> H["HIGH"]
  HIGH -- No --> C["CRITICAL"]

  L --> OUT["fuzzy_risk_level"]
  M --> OUT
  H --> OUT
  C --> OUT
```

---

## 13. Phase 1 Mermaid — Deployment View

Save as: `diagrams/09_local_deployment.mmd`

```mermaid
flowchart LR
  subgraph DEV["Local Development"]
    BROWSER["Browser"]
    FE["Next.js :3000"]
    BE["FastAPI :8000"]
    PG["PostgreSQL :5432"]
    REDIS["Redis :6379"]
  end

  subgraph CODE["Repo"]
    BACKEND["backend/app"]
    FRONTEND["frontend/app"]
    DOCS["docs + diagrams"]
    TESTS["pytest + frontend tests"]
  end

  BROWSER --> FE
  FE --> BE
  BE --> PG
  BE --> REDIS
  BACKEND --> BE
  FRONTEND --> FE
  DOCS --> BROWSER
  TESTS --> BE
```

---

## 14. Phase 1 Mermaid — Roadmap Gantt

Save as: `diagrams/10_phase1_gantt.mmd`

```mermaid
gantt
  title Suryagrid AI Phase 1 MVP Roadmap
  dateFormat  YYYY-MM-DD
  axisFormat  %d %b

  section Foundation
  Repo + Docker + env setup              :a1, 2026-06-20, 3d
  FastAPI base + health + docs           :a2, after a1, 3d
  PostgreSQL models + Alembic            :a3, after a2, 4d

  section Agents
  Toy Data Agent                         :b1, after a3, 4d
  Forecast Agent                         :b2, after b1, 3d
  DSM Classifier Agent                   :b3, after b2, 3d
  Fuzzy Risk Agent                       :b4, after b3, 3d
  Explanation Agent                      :b5, after b4, 2d

  section Security + API Management
  JWT Auth + RBAC                        :c1, after a3, 4d
  Redis rate limit + audit logs          :c2, after c1, 3d

  section Frontend
  Next.js dashboard layout               :d1, after b2, 4d
  Cards + forms + charts                 :d2, after d1, 5d
  API integration                        :d3, after d2, 3d

  section Quality
  Unit tests + API tests                 :e1, after b5, 4d
  README + docs                          :e2, after e1, 3d
```

---

## 15. Backend Folder Structure

Claude should create this exact structure first.

```text
suryagrid-ai-phase1/
  README.md
  docker-compose.yml
  .env.example
  .gitignore

  docs/
    PHASE_1_ADVANCED_IMPLEMENTATION.md
    API_DESIGN.md
    AGENT_ARCHITECTURE.md
    SECURITY_PLAN.md
    FUZZY_LOGIC.md
    FUTURE_PHASES.md
    diagrams/
      01_three_level_architecture.mmd
      02_agent_workflow.mmd
      03_prediction_sequence.mmd
      04_state_machine.mmd
      05_data_model_er.mmd
      06_security_flow.mmd
      07_api_management_future.mmd
      08_fuzzy_logic_flow.mmd
      09_local_deployment.mmd
      10_phase1_gantt.mmd

  backend/
    Dockerfile
    requirements.txt
    alembic.ini
    app/
      main.py
      config.py
      dependencies.py

      agents/
        __init__.py
        orchestrator_agent.py
        toy_data_agent.py
        forecast_agent.py
        dsm_classifier_agent.py
        fuzzy_risk_agent.py
        explanation_agent.py
        api_management_agent.py
        security_agent.py
        reward_stub_agent.py

      api/
        __init__.py
        routes_health.py
        routes_auth.py
        routes_sites.py
        routes_toy_data.py
        routes_prediction.py
        routes_dsm.py
        routes_timeline.py
        routes_config.py

      core/
        security.py
        rate_limit.py
        logging.py
        exceptions.py
        audit.py

      db/
        database.py
        session.py
        models.py
        migrations/

      schemas/
        auth_schema.py
        site_schema.py
        weather_schema.py
        prediction_schema.py
        dsm_schema.py
        timeline_schema.py

      services/
        site_service.py
        toy_data_service.py
        prediction_service.py
        dsm_service.py
        timeline_service.py
        auth_service.py
        provider_service.py

      providers/
        base_provider.py
        toy_weather_provider.py
        solcast_provider_stub.py
        open_meteo_provider_stub.py
        nasa_power_provider_stub.py

      utils/
        solar_formula.py
        fuzzy_logic.py
        time_utils.py
        validation.py
        response.py

    tests/
      test_solar_formula.py
      test_dsm_classifier.py
      test_fuzzy_logic.py
      test_toy_data_agent.py
      test_prediction_api.py
      test_security.py

  frontend/
    Dockerfile
    package.json
    next.config.js
    tsconfig.json
    tailwind.config.ts
    app/
      page.tsx
      dashboard/page.tsx
      sites/page.tsx
      predictions/page.tsx
      dsm/page.tsx
      settings/page.tsx
    components/
      cards/MetricCard.tsx
      cards/PenaltyStatusCard.tsx
      cards/FuzzyRiskCard.tsx
      charts/GenerationTimelineChart.tsx
      charts/DeviationChart.tsx
      charts/WeatherChart.tsx
      forms/SiteForm.tsx
      forms/PredictionForm.tsx
      forms/ScheduleForm.tsx
      layout/Navbar.tsx
      layout/Sidebar.tsx
      layout/PageHeader.tsx
    lib/
      api.ts
      types.ts
      auth.ts
      format.ts
```

---

## 16. Agent Implementation Contract

Each agent should expose a simple class with one main method. Keep it easy for Claude to implement and test.

### 16.1 Orchestrator Agent

```python
class OrchestratorAgent:
    def run_prediction_cycle(self, request: PredictionRequest) -> PredictionResponse:
        ...
```

Responsibilities:

- Coordinate all agents.
- Never do math itself.
- Validate order of operations.
- Save final result.
- Return API-ready response.

### 16.2 Toy Data Agent

```python
class ToyDataAgent:
    def generate_site_day(self, site_id: str, date: date, interval_minutes: int) -> list[ToyWeatherReading]:
        ...
```

Responsibilities:

- Generate toy irradiance curve.
- Generate cloud patterns.
- Generate temperature and humidity.
- Generate synthetic actual generation.
- Store and return normalized readings.

### 16.3 Forecast Agent

```python
class ForecastAgent:
    def predict(self, weather: WeatherInput, site: SiteConfig) -> ForecastResult:
        ...
```

Responsibilities:

- Use toy formula first.
- Clamp output between 0 and capacity.
- Return confidence score.
- Later allow pvlib/ML strategy.

### 16.4 DSM Classifier Agent

```python
class DSMClassifierAgent:
    def classify(self, predicted_mw: float, schedule: ScheduleConfig) -> DSMResult:
        ...
```

Responsibilities:

- Calculate deviation MW.
- Calculate deviation percent.
- Compare with threshold.
- Estimate penalty cost.

### 16.5 Fuzzy Risk Agent

```python
class FuzzyRiskAgent:
    def score(self, dsm: DSMResult, weather: WeatherInput, confidence_score: float) -> FuzzyRiskResult:
        ...
```

Responsibilities:

- Convert hard DSM output into soft risk score.
- Return risk level: LOW, MEDIUM, HIGH, CRITICAL.

### 16.6 Explanation Agent

```python
class ExplanationAgent:
    def explain(self, result: CompletePredictionResult) -> str:
        ...
```

Responsibilities:

- Explain why penalty/no penalty happened.
- Do not calculate values.
- Use already computed numbers.

### 16.7 API Management Agent

```python
class APIManagementAgent:
    def prepare_request(self, request_context: RequestContext) -> APIManagementDecision:
        ...
```

Responsibilities:

- Rate limiting.
- Provider selection.
- Mock provider routing.
- Future external provider failover.

### 16.8 Security Agent

```python
class SecurityAgent:
    def authorize(self, user: User, action: str, site_id: str | None) -> bool:
        ...
```

Responsibilities:

- JWT + RBAC.
- Site-level permission checks.
- Audit suspicious actions.

---

## 17. Toy Data Model

### Required columns

```csv
timestamp,site_id,irradiance_w_m2,cloud_cover_percent,temperature_c,humidity_percent,wind_speed_mps,rain_probability_percent,scheduled_generation_mw,actual_generation_mw
```

### Toy data rules

| Feature | Rule |
|---|---|
| Irradiance | 0 at night, rises after sunrise, peaks near noon, falls near sunset |
| Cloud cover | random with optional cloudy blocks |
| Temperature | lower morning, higher afternoon |
| Humidity | inverse-ish to temperature with noise |
| Rain probability | increases when cloud cover is high |
| Actual generation | formula generation + random noise |
| Scheduled generation | fixed or smooth daylight curve |

### Irradiance approximation

```python
import math

def toy_irradiance(hour: float, max_irradiance: float = 950.0) -> float:
    # Sunrise 6, sunset 18. Returns 0 outside daylight.
    if hour < 6 or hour > 18:
        return 0.0
    daylight_position = (hour - 6) / 12
    return max_irradiance * math.sin(math.pi * daylight_position)
```

---

## 18. Solar Prediction Formula

Phase 1 default prediction formula:

```python
def predict_generation(
    solar_capacity_mw: float,
    irradiance_w_m2: float,
    cloud_cover_percent: float,
    temperature_c: float,
) -> float:
    base_generation = solar_capacity_mw * (irradiance_w_m2 / 1000.0)
    cloud_loss_factor = 1.0 - ((cloud_cover_percent / 100.0) * 0.75)
    temperature_loss_factor = 1.0 - max(0.0, temperature_c - 25.0) * 0.005
    predicted = base_generation * cloud_loss_factor * temperature_loss_factor
    predicted = max(0.0, min(predicted, solar_capacity_mw))
    return round(predicted, 3)
```

This is a **toy approximation**, not final engineering-grade solar modelling. Later, the Forecast Agent can switch to pvlib or ML.

---

## 19. DSM Penalty Logic

### Formula

```python
deviation_mw = abs(predicted_generation_mw - scheduled_generation_mw)
deviation_percent = (deviation_mw / scheduled_generation_mw) * 100

if deviation_percent > allowed_dsm_threshold_percent:
    penalty_status = "PENALTY_RISK"
else:
    penalty_status = "NO_PENALTY"

estimated_penalty_cost = deviation_mw * penalty_rate_per_mw
```

### Production-safe behavior

If `scheduled_generation_mw <= 0`, return:

```json
{
  "penalty_status": "INVALID_SCHEDULE",
  "deviation_mw": 0,
  "deviation_percent": 0,
  "estimated_penalty_cost": 0
}
```

---

## 20. Fuzzy Logic Rules

### Inputs

- deviation_percent
- cloud_cover_percent
- irradiance_w_m2
- confidence_score
- scheduled_generation_mw

### Output

- fuzzy_risk_score: 0 to 100
- fuzzy_risk_level: LOW / MEDIUM / HIGH / CRITICAL

### Simple Phase 1 scoring

```python
def calculate_fuzzy_risk(
    deviation_percent: float,
    cloud_cover_percent: float,
    irradiance_w_m2: float,
    confidence_score: float,
) -> dict:
    risk_score = 0.0
    risk_score += deviation_percent * 0.5
    risk_score += cloud_cover_percent * 0.2

    if irradiance_w_m2 < 300:
        risk_score += 20

    if confidence_score < 0.6:
        risk_score += 15

    risk_score = max(0.0, min(100.0, risk_score))

    if risk_score < 25:
        level = "LOW"
    elif risk_score < 50:
        level = "MEDIUM"
    elif risk_score < 75:
        level = "HIGH"
    else:
        level = "CRITICAL"

    return {
        "fuzzy_risk_score": round(risk_score, 2),
        "fuzzy_risk_level": level,
    }
```

---

## 21. API Design

Base URL:

```text
/api/v1
```

### Endpoint table

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| GET | `/health` | System status | No |
| POST | `/auth/register` | Create user | No / dev only |
| POST | `/auth/login` | Login and receive token | No |
| GET | `/auth/me` | Current user | Yes |
| POST | `/sites` | Create solar site | Admin/operator |
| GET | `/sites` | List accessible sites | Yes |
| GET | `/sites/{site_id}` | Site details | Yes |
| POST | `/toy-data/generate` | Generate toy data | Operator/admin |
| GET | `/toy-data/{site_id}` | Get toy data | Yes |
| POST | `/predict` | Run full prediction cycle | Operator/admin |
| POST | `/dsm/check` | Direct DSM check | Operator/admin |
| GET | `/timeline/{site_id}` | Chart-ready timeline | Yes |
| GET | `/config/dsm` | Get default DSM config | Yes |
| PUT | `/config/dsm` | Update default DSM config | Admin |

---

## 22. Example Prediction Request

```json
{
  "site_id": "site_uuid",
  "solar_capacity_mw": 10,
  "irradiance_w_m2": 720,
  "cloud_cover_percent": 45,
  "temperature_c": 31,
  "humidity_percent": 62,
  "wind_speed_mps": 3.2,
  "rain_probability_percent": 12,
  "scheduled_generation_mw": 6.5,
  "allowed_dsm_threshold_percent": 10,
  "penalty_rate_per_mw": 15000
}
```

## 23. Example Prediction Response

```json
{
  "site_id": "site_uuid",
  "timestamp": "2026-06-18T12:00:00+05:30",
  "predicted_generation_mw": 4.65,
  "scheduled_generation_mw": 6.5,
  "deviation_mw": 1.85,
  "deviation_percent": 28.46,
  "allowed_dsm_threshold_percent": 10,
  "penalty_status": "PENALTY_RISK",
  "estimated_penalty_cost": 27750,
  "fuzzy_risk_score": 63.2,
  "fuzzy_risk_level": "HIGH",
  "confidence_score": 0.82,
  "explanation": "Penalty risk detected. Predicted generation is below the scheduled value. Cloud cover and reduced irradiance are the main risk drivers."
}
```

---

## 24. Database Tables

### Core tables

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'viewer',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sites (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  timezone VARCHAR(100) DEFAULT 'Asia/Kolkata',
  capacity_mw DOUBLE PRECISION NOT NULL,
  panel_efficiency DOUBLE PRECISION DEFAULT 0.18,
  tilt DOUBLE PRECISION DEFAULT 15,
  azimuth DOUBLE PRECISION DEFAULT 180,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE toy_weather_readings (
  id UUID PRIMARY KEY,
  site_id UUID REFERENCES sites(id),
  ts TIMESTAMP NOT NULL,
  irradiance_w_m2 DOUBLE PRECISION NOT NULL,
  cloud_cover_percent DOUBLE PRECISION NOT NULL,
  temperature_c DOUBLE PRECISION NOT NULL,
  humidity_percent DOUBLE PRECISION NOT NULL,
  wind_speed_mps DOUBLE PRECISION NOT NULL,
  rain_probability_percent DOUBLE PRECISION NOT NULL,
  quality_flag INT DEFAULT 1,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE schedule_windows (
  id UUID PRIMARY KEY,
  site_id UUID REFERENCES sites(id),
  window_start TIMESTAMP NOT NULL,
  window_end TIMESTAMP NOT NULL,
  scheduled_generation_mw DOUBLE PRECISION NOT NULL,
  allowed_dsm_threshold_percent DOUBLE PRECISION NOT NULL DEFAULT 10,
  penalty_rate_per_mw DOUBLE PRECISION NOT NULL DEFAULT 15000,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE dsm_results (
  id UUID PRIMARY KEY,
  site_id UUID REFERENCES sites(id),
  schedule_window_id UUID REFERENCES schedule_windows(id),
  ts TIMESTAMP NOT NULL,
  predicted_generation_mw DOUBLE PRECISION NOT NULL,
  scheduled_generation_mw DOUBLE PRECISION NOT NULL,
  deviation_mw DOUBLE PRECISION NOT NULL,
  deviation_percent DOUBLE PRECISION NOT NULL,
  penalty_status VARCHAR(50) NOT NULL,
  estimated_penalty_cost DOUBLE PRECISION NOT NULL,
  fuzzy_risk_score DOUBLE PRECISION NOT NULL,
  fuzzy_risk_level VARCHAR(50) NOT NULL,
  confidence_score DOUBLE PRECISION NOT NULL,
  explanation TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE audit_logs (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  action VARCHAR(255) NOT NULL,
  entity_type VARCHAR(100),
  entity_id UUID,
  ip_address VARCHAR(100),
  details JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 25. Frontend Dashboard Pages

### `/dashboard`

Cards:

- Solar capacity
- Predicted generation
- Scheduled generation
- Deviation MW
- Deviation percent
- Penalty status
- Fuzzy risk level
- Estimated penalty cost

Charts:

- Predicted vs scheduled generation timeline
- Actual vs predicted generation timeline
- Cloud cover vs generation
- Deviation percent timeline

### `/sites`

- Create site
- View site list
- Configure capacity, location, threshold and penalty rate

### `/predictions`

- Manual input form
- Run prediction
- Display JSON + cards

### `/dsm`

- DSM status table
- Filter by risk level
- Export results

### `/settings`

- DSM threshold
- Penalty rate
- API mode: toy/mock/live later
- User role display

---

## 26. Security Implementation

### Roles

```text
admin    -> full access
operator -> create data, run prediction, view results
viewer   -> view dashboards only
```

### JWT payload

```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "role": "operator",
  "exp": 1760000000
}
```

### Security checklist

- Hash passwords with bcrypt.
- JWT secret from `.env`.
- Never commit `.env`.
- Add `.env.example` only.
- Validate all numeric inputs with Pydantic.
- Use Redis rate limit per user/IP.
- Add audit logs for prediction, config change and login.
- Never expose future plant connector routes without auth.

---

## 27. API Management Implementation

Phase 1 API Management Agent should implement:

```text
- request_id generation
- standard response envelope
- standard error envelope
- rate limiting
- mock provider routing
- provider interface
- cache key format
- logging metadata
```

### Standard response envelope

```json
{
  "success": true,
  "request_id": "req_123",
  "data": {},
  "error": null
}
```

### Standard error envelope

```json
{
  "success": false,
  "request_id": "req_123",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "cloud_cover_percent must be between 0 and 100"
  }
}
```

---

## 28. Claude Build Plan

Claude should implement in this order.

### Step 1: Repository scaffold

Create folders, `.env.example`, `docker-compose.yml`, backend and frontend skeletons.

### Step 2: Backend base

Create FastAPI app with:

- `/api/v1/health`
- app config
- logging middleware
- exception handlers
- response envelope

### Step 3: Database

Create SQLAlchemy models and Alembic migration.

### Step 4: Core formulas

Create and test:

- `predict_generation`
- `classify_dsm_risk`
- `calculate_fuzzy_risk`
- `generate_explanation`

### Step 5: Agents

Wrap formulas in agent classes.

### Step 6: API endpoints

Build site, toy data, predict, DSM and timeline routes.

### Step 7: Security

Add auth, JWT, role dependency and audit logs.

### Step 8: Redis

Add simple rate limiting and cache helper.

### Step 9: Frontend

Build dashboard layout, metric cards, forms and charts.

### Step 10: Tests and docs

Run tests, update README and document API.

---

## 29. Test Cases

| Test | Input | Expected |
|---|---|---|
| Sunny day | high irradiance, low cloud | high generation, no penalty if near schedule |
| Cloudy day | low irradiance, high cloud | low generation, penalty risk |
| Invalid schedule | scheduled MW = 0 | no divide-by-zero, `INVALID_SCHEDULE` |
| Capacity clamp | irradiance > 1000 | prediction <= capacity |
| Bad cloud value | cloud > 100 | Pydantic 422 error |
| Low confidence | confidence < 0.6 | fuzzy score increases |
| Viewer writes data | viewer calls POST predict | 403 forbidden |
| Rate limit exceeded | many requests | 429 response |

---

## 30. Docker Compose

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: suryagrid
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000/api/v1
    volumes:
      - ./frontend:/app

volumes:
  postgres_data:
```

---

## 31. `.env.example`

```env
APP_NAME="Suryagrid AI"
APP_ENV=development
API_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/suryagrid
REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=change_this_secret_in_real_project
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

DEFAULT_DSM_THRESHOLD_PERCENT=10
DEFAULT_PENALTY_RATE_PER_MW=15000
DEFAULT_TIMEZONE=Asia/Kolkata

PHASE_MODE=toy
```

---

## 32. Future Phase Hooks

Do not build these fully now, but keep interfaces ready.

| Future feature | Phase 1 hook |
|---|---|
| Solcast | `providers/solcast_provider_stub.py` |
| Open-Meteo | `providers/open_meteo_provider_stub.py` |
| NASA POWER | `providers/nasa_power_provider_stub.py` |
| pvlib model | `services/pvlib_service.py` placeholder |
| RL reward engine | `agents/reward_stub_agent.py` |
| Consumer discount | settlement schema extension |
| SCADA/inverter | connector interface only |
| Multi-tenant SaaS | user/site access table |
| Cloud-camera nowcasting | cloud media field in provider schema |
| Deployment | Docker now, ECS/K8s later |

---

## 33. Definition of Done

Phase 1 is complete when:

1. Backend runs at `http://localhost:8000`.
2. Swagger docs open at `http://localhost:8000/docs`.
3. Frontend runs at `http://localhost:3000`.
4. User can create a solar site.
5. User can generate toy data.
6. User can run prediction.
7. DSM penalty status is calculated correctly.
8. Fuzzy risk level is shown.
9. Explanation is generated.
10. Timeline chart displays predicted, scheduled and actual generation.
11. JWT auth and role checks work.
12. Redis rate limiting works.
13. All formula tests pass.
14. Code structure is ready for Solcast/Open-Meteo/NASA/SCADA/RL later.

---

## 34. Final Claude Prompt

Copy this prompt into Claude Code after giving it this MD file:

```text
You are building Suryagrid AI Phase 1. Read PHASE_1_ADVANCED_IMPLEMENTATION.md completely and implement the project exactly in that order.

Important constraints:
- Build Phase 1 only.
- Use toy/synthetic weather, cloud and irradiance data.
- Use Python 3.12, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Redis, Next.js, TypeScript, Tailwind and Recharts/ECharts.
- Implement agents as Python classes first.
- Do not use real APIs yet.
- Do not implement full RL yet.
- Do not let an LLM calculate solar generation or DSM values.
- Add tests for formulas and APIs.
- Keep provider interfaces ready for Solcast, Open-Meteo and NASA POWER later.
- Keep security from day one: JWT, roles, audit logging and rate limiting.

Start by scaffolding the repo, then implement backend formulas, agents, routes, DB models, tests, Docker Compose and frontend dashboard.
```

---

# Final Summary

Suryagrid AI Phase 1 must prove the core foundation:

```text
Toy Weather + Cloud + Irradiance
        ↓
Forecast Agent
        ↓
Predicted Solar Generation
        ↓
DSM Classifier
        ↓
Fuzzy Risk Agent
        ↓
Penalty / No Penalty + Cost
        ↓
Explanation + API + Dashboard
```

This is the base on which the full solar multi-agent platform will be built.
