# SuryaGrid AI - Permanent Main-Plan Context Prompt

Version: 1.0  
Context frozen: 2026-07-09  
Purpose: source-of-truth prompt for future agents, developers, reviewers, and document writers.

## Copy/paste prompt

You are working on **SuryaGrid AI**, a solar-generation forecasting, grid decision-support,
reward/penalty research, and future plant-integration platform. Preserve the complete project
context below. Do not reduce the project to only the current substation/DSM workflow.

### 1. Governing source material

Use the following evidence in this order:

1. **Main handwritten plan:**  
   `C:\Users\lekhan hr\Downloads\IMG_20260611_162613.jpg`
2. **Handwritten Phase 1 note:**  
   `C:\Users\lekhan hr\Downloads\IMG-20260618-WA0001.jpg`  
   A copy also exists at `D:\Suryagrid AI\IMG-20260618-WA0001.jpg`.
3. **Current repository and verified implementation evidence:**  
   `D:\Suryagrid AI\README.md` and
   `D:\Suryagrid AI\docs\report\report_evidence_matrix.md`.
4. **Older interpretation documents:** `PROJECT_PLAN.md` and
   `SURYAGRID_PHASE1_ADVANCED_IMPLEMENTATION.md`. These are supporting material, not authority
   where they conflict with the handwritten main plan or verified code.

### 2. Main-plan intent

The main plan is a four-level execution concept:

- **L1 - Data/API foundation:** solar and weather inputs, with Solcast written as the intended
  source and additional providers/fallbacks allowed.
- **L2 - Forecasting and intelligence:** cloud/weather interpretation, statistical or
  mathematical processing, ML forecasting, and an answer to: "How much power can each DG/solar
  station generate?"
- **L3 - Cost, incentive, reward, penalty, and discount logic:** compare generation or commitment
  with demand/request; calculate the gap; apply an approved policy. Handwritten values such as
  "25" and "15% discount" are exploratory notes only, not approved rules.
- **L4 - Operational workflow:** orchestrate the end-to-end process through agents, APIs/tools,
  review gates, dashboards, and later hardware/plant integration.

The intended end-to-end flow is:

`station/configuration + demand/request -> solar/weather data -> quality checks -> forecast/ML ->
per-station generation estimate -> compare with schedule/demand -> gap -> reward/penalty/discount
decision -> QA/audit -> API/dashboard/alerts`

Reinforcement learning belongs in a controlled feedback loop after deterministic calculations,
approved tariff/reward rules, and measured local telemetry exist. It must begin offline, then run
in shadow mode. It must not autonomously set money, dispatch, or plant controls in the initial
pilot.

### 3. Agent model

Keep six logical responsibilities, even if the code uses more specialized modules:

1. **Orchestrator Agent** - triggers, state, retries, QA gates, trace, and final assembly.
2. **Source/API Agent** - provider selection, quotas, failover, normalization, and provenance.
3. **Forecast Agent** - irradiance, solar generation, and load forecasts with confidence.
4. **Cloud/Weather Risk Agent** - cloud regime and forecast-risk classification.
5. **Logic/Calculation Agent** - deterministic energy, gap, DSM, and constraint calculations.
6. **Reward/Policy Agent** - approved reward/penalty/discount policy and later safe RL proposals.

Do not call the fourth role "Cloudinary" unless the owner explicitly confirms that a media CDN
was intended. The handwriting does not support that name with confidence.

### 4. How Phase 1 fits

The handwritten Phase 1 note asks for solar irradiance nowcasting, generation prediction, an
agreement/scheduled MW comparison, DSM threshold classification, penalty/no-penalty risk, cost or
PV math, and a time-based generation/DSM timeline.

The original Phase 1 specification implemented this first as a toy-data/formula MVP. In the main
plan's numbering, that work is closer to a **simulation/foundation subset**, not the complete live
pilot. Later repository work substantially extended it with real weather, pvlib, trained models,
substation context, REST APIs, dashboard pages, and deployment assets.

Use this phase reconciliation:

- **Foundation / simulation MVP:** historical "Phase 1" work.
- **Current baseline:** real-data decision-support prototype, approximately Phase 1.7 in repo
  language.
- **Next target:** controlled live/shadow pilot for 1-3 sites.
- **Later target:** validated reward/discount policy, RL-assisted recommendations, then hardware
  and SCADA integration.

### 5. Verified current baseline as of 2026-07-09

Verified in the repository:

- Backend: FastAPI, 61 `/api/v1` routes, PostgreSQL/SQLite support, Redis integration, ingestion
  and ML pipelines, deterministic pvlib calculations, DSM/fuzzy logic, and multi-agent
  orchestration.
- Data: live Open-Meteo paths, historical Bengaluru weather, Kaggle datasets, source/provenance
  tracking, and 344 real OSM substations.
- Models: production-marked irradiance and cloud-risk models exist with model cards; DSM
  classification exists as decision support.
- Frontend: Next.js dashboard and 14 application routes.
- Operations: Docker Compose and single-instance deployment scripts exist; managed AWS
  Terraform is code-only unless separately verified.
- Verification on 2026-07-09: 118 backend tests passed; Ruff passed; frontend production build
  passed.

Current limitations that must remain explicit:

- Solcast is not integrated; only one live weather provider is operational.
- There is no measured Bengaluru site-level PV generation truth or local substation/feeder load
  telemetry.
- Substation capacity is missing for all 344 OSM records; voltage is incomplete.
- Official effective-dated KERC/CERC/BESCOM DSM rupee rates are not connected.
- Any hard-coded rupee reward/penalty defaults are illustrative and must not be presented as
  settlement truth.
- PV output is estimated from irradiance, not measured.
- The RL production model is intentionally blocked because real local load, economics, and
  training rows are insufficient.
- Authentication/RBAC/multi-tenancy, enforced rate limits, alert delivery, SCADA connectors,
  HTTPS verification, observability, backup/restore, and managed-cloud deployment are incomplete
  or unverified.

### 6. Non-negotiable engineering rules

1. Never fabricate missing capacity, voltage, load, generation, tariff, or monetary values.
2. Label every value as measured, sourced, estimated, model-predicted, illustrative, or missing.
3. Keep physics, energy, DSM, and money calculations deterministic and versioned.
4. Use ML for forecasts/classification; use LLMs only for orchestration or explanation, never as
   the numerical authority.
5. Do not emit real rupee settlement values until an approved, effective-dated regulatory source
   is parsed, reviewed, and tested.
6. Do not train or deploy RL until measured local telemetry and approved economics exist.
7. Require offline evaluation, shadow mode, human approval, rollback, and audit logs before any
   reward/dispatch recommendation affects operations.
8. Separate decision support from settlement of record and plant control.
9. Preserve source lineage, formula/model version, input timestamps, timezone, units, and
   calculation trace in every decision.
10. Treat Solcast, GraphQL, TimescaleDB, S3, AWS ECS, SCADA, and hardware as planned until their
    real integration is verified.

### 7. Required execution order

Use this dependency chain:

`scope and policy lock -> official rules/data agreements -> reliable data foundation -> validated
site-level forecast and deterministic DSM -> secure operator workflow -> shadow pilot -> RL
research gate -> controlled production decision`

Parallel work is allowed for security, frontend, infrastructure, and observability, but those
workstreams must pass before a live pilot.

The reference execution horizon for a 3-5 engineer team is:

- Weeks 0-1: baseline, scope, and unsupported-money quarantine.
- Weeks 2-5: official data/rule access and contracts.
- Weeks 3-7: Level 1 productionization.
- Weeks 6-11: Level 2 site-level validation and versioned DSM.
- Weeks 10-14: Level 3 operator workflows and read-only integration.
- Weeks 12-17: RL research gate, conditional on real data and approved economics.
- Weeks 14-18: security/operations hardening.
- Weeks 19-22: controlled shadow pilot and acceptance.

Minimum credible decision-support pilot: roughly 14-18 weeks.  
RL-assisted gated pilot: roughly 20-24 weeks.  
External approvals or telemetry agreements can add 4-8 or more weeks.

### 8. Required response behavior for future work

Before proposing or implementing work:

1. State which main-plan level and agent responsibility the work belongs to.
2. State whether it is already implemented, partially implemented, blocked, or new.
3. Cite repository evidence.
4. Identify required inputs, dependencies, outputs, tests, and acceptance criteria.
5. Distinguish facts from assumptions and unresolved handwriting.
6. Do not produce a plan focused only on substation DSM unless the user specifically asks for
   that narrow scope.
7. Keep deliverables tied to the main business flow: per-station generation, demand/gap,
   policy/reward decision, orchestration, and safe operational integration.

### 9. Unresolved owner decisions

Ask the owner before locking these decisions:

- Is "Solcast" mandatory, or is a provider-neutral source layer acceptable?
- Does the unclear handwritten cloud role mean cloud/weather risk, camera/cloud imagery, or a
  separate media service?
- What exactly are S/M and the unclear station-system acronym in the main image?
- Which Karnataka market participant and DSM regulation apply?
- What is the settlement interval, schedule source, and under/over-generation treatment?
- Who are the owner and consumer personas, and what reward/discount behavior is legally allowed?
- Which 1-3 pilot sites can provide nameplate data, measured PV, schedules, and load?
- Is the first live release decision support only, or is any control action expected?

End of permanent context prompt.
