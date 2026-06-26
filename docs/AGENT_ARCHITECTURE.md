# Agent Architecture - Suryagrid AI

## Data source
- **OpenMeteoProvider** (`app/providers/open_meteo.py`) — real hourly GHI/DNI/DHI,
  temperature, cloud cover, wind. Implements the `WeatherProvider` interface so other
  sources (Solcast, NASA POWER) can be added without changing the pipeline.

## Agents
1. **ForecastAgent** — pvlib physics. Solar position → plane-of-array transposition
   → cell temperature (Faiman) → PVWatts DC → inverter AC. Outputs predicted MW,
   clear-sky baseline MW, and a confidence score. When a source supplies GHI only,
   beam/diffuse components are derived via the Erbs decomposition.
2. **DSMClassifierAgent** — deviation of nowcast vs scheduled MW against the allowed
   band; penalty status and chargeable cost on the deviated energy.
3. **RiskAgent** — deterministic 0–100 score from band breach + confidence;
   LOW/MEDIUM/HIGH/CRITICAL.
4. **ExplanationAgent** — plain-language interval summary.
5. **OrchestratorAgent** — sequences the per-interval pipeline.

## Services
- **ForecastService** — fetches provider data, runs the agents across the whole
  series, and builds the timeline + day summary.
- **SiteStore** — in-memory site registry (PostgreSQL models available in `app/db`).

## Flow
```
OpenMeteoProvider → ForecastAgent (pvlib) → DSMClassifierAgent → RiskAgent → ExplanationAgent
```
The schedule defaults to the clear-sky baseline (a realistic day-ahead commitment)
and can be overridden per request.

## Reward & RL (PROJECT_PLAN sections 5-6)
- **RewardAgent** — penalty/bonus/discount settlement (owner target vs actual).
- **RL digital twin** — `SolarSettlementEnv` (synthetic) and `RealDataSettlementEnv`
  (real historical days from the Open-Meteo archive run through pvlib). A numpy
  REINFORCE trainer optimizes the rate policy; runs are persisted as `TrainingRun`.

## Energy (PROJECT_PLAN section 7)
- **EnergyService** — production vs consumption per interval: surplus, deficit,
  self-consumption %, grid import/export.
- **ConsumptionService** — residential/commercial/industrial synthetic load curves.

## Data layer
- **APIAgent** — provider rotation, failover and quota tracking (agent #6).
- **Database** — SQLAlchemy async, SQLite locally / PostgreSQL+TimescaleDB in prod
  via a portable GUID type. Repository layer persists sites, readings, forecasts,
  settlements and training runs (PROJECT_PLAN section 8 ER model).
- **site_resolver** — resolves a registered site from the DB, or builds an ad-hoc
  config from query params so any location works without registration.
