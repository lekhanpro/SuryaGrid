# SuryaGrid AI — Real-Data Phase 1.5

Phase 1.5 upgrades the Phase 1 nowcaster into a **real-data** solar forecasting + DSM
risk platform: Kaggle-trained ML, live weather, substation/location data, an advanced
configurable DSM engine, and a fully **sourced** multi-agent pipeline — all runnable via
Docker. Synthetic data remains only as a fallback/testing mode, always labelled.

Scope guardrails (explicitly **not** added): blockchain, energy trading, RL optimization,
real SCADA control, hardware control, payment settlement, consumer discount engine.
(Pre-existing RL/settlement modules from Phase 1 are retained untouched, not extended.)

## What changed vs Phase 1

| Area | Phase 1 | Phase 1.5 |
|------|---------|-----------|
| Data sources | Open-Meteo only | + Kaggle history, OSM substations, synthetic fallback, source registry |
| Forecasting | pvlib formula only | formula **/ ml / hybrid** (scikit-learn), model registry + metrics |
| DSM | simple band + KERC slabs (hardcoded) | **configurable rule profiles** (region/regulator/bands) with source status |
| Risk | linear score | genuine **fuzzy** inference (triangular membership, Mamdani, centroid) |
| Locations | site centroids | sites + substations + weather grid + nearest-mapping + data-coverage |
| Sourcing | implicit | every value classified & cited (`docs/SOURCE_REGISTRY.md`) |
| Agents | 5 | 12 deterministic coordinators (`docs/AGENT_WORKFLOWS.md`) |
| Frontend | dashboard/timeline/… | + data-sources, locations, ml, dsm, system; offline banner (no silent fake) |
| Deploy | compose (basic) | compose w/ healthchecks, volumes, data mount, .env |

## Documentation map

- Sources: `SOURCE_REGISTRY.md`, `FORMULA_SOURCES.md`, `DSM_RULE_SOURCES.md`, `DATA_SOURCE_CATALOG.md`
- ML: `ML_PIPELINE.md`
- Locations: `LOCATION_AND_SUBSTATION_DATA.md`
- Agents: `AGENT_WORKFLOWS.md`
- API: `API_REFERENCE.md`
- Ops: `DOCKER_ARCHITECTURE.md`

## Source-first rule

No formula, DSM threshold, penalty rate, solar constant, weather field, or dataset
assumption is arbitrary. Each is classified `OFFICIAL_SOURCE` / `DATASET_DERIVED` /
`MODEL_LEARNED` / `USER_CONFIGURABLE` / `FALLBACK_DEFAULT` (or
`…_PENDING_OFFICIAL_SOURCE`) and cited in prediction responses. Regulatory DSM figures
that need live verification are marked pending — the system never claims regulatory
accuracy for a specific penalty number.

## End-to-end flow

Site → data coverage + nearest substation → live weather → forecast (formula/ml/hybrid)
→ advanced DSM (configurable profile) → fuzzy risk → explanation with source citations →
persist → API response → dashboard. See `AGENT_WORKFLOWS.md`.

## Honest limitations

- Kaggle HI-SEAS is irradiance-only and Hawaii-based; the ML model predicts irradiance and
  converts to generation via pvlib. For a specific plant, ingest local generation history.
- "Actual injection" for DSM is the nowcast until a metered SLDC/BESCOM feed is connected.
- Sub-hourly weather horizons resolve to the nearest hourly forecast (Open-Meteo free tier).
- DSM charges are decision-support estimates, not a settlement of record.
