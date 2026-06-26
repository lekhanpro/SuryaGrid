# Agent Architecture - Suryagrid AI

## Data source
- **OpenMeteoProvider** (`app/providers/open_meteo.py`) — real hourly GHI/DNI/DHI,
  temperature, cloud cover, wind. Implements the `WeatherProvider` interface so other
  sources (Solcast, NASA POWER) can be added without changing the pipeline.

## Agents
1. **ForecastAgent** — pvlib physics. Solar position → plane-of-array transposition
   → cell temperature (Faiman) → PVWatts DC → inverter AC. Outputs predicted MW,
   clear-sky baseline MW, and a confidence score.
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
