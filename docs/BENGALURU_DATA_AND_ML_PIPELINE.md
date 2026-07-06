# Bengaluru Data & ML Pipeline (Phase 1.7)

How SuryaGrid turns the closest **real** Bengaluru/Karnataka/India data into ML-ready
files and trained agents — honestly, with every value labelled by source geography.

> Correction adopted in Phase 1.7: SuryaGrid is a **Bengaluru/Karnataka/India** project.
> Foreign datasets (e.g. Hawaii HI-SEAS) are NOT production truth. They may exist only as
> `REAL_NON_LOCAL` / `PRETRAINING_ONLY` with `domain_shift_risk=HIGH`.

## Source-geography priority

1. Bengaluru-specific (`REAL_LOCAL`)
2. Karnataka-specific (`REAL_KARNATAKA`)
3. South India → India-wide (`REAL_INDIA`)
4. Coordinate-based global APIs at Bengaluru lat/lon (`REAL_COORDINATE_BASED`)
5. Non-local real data → `REAL_NON_LOCAL` / `PRETRAINING_ONLY` only (never production truth)

Bengaluru reference coordinate: **lat 12.9716, lon 77.5946**, tz `Asia/Kolkata`, altitude ~920 m.

## Data sources actually used

| Dataset | Source | Label | Notes |
|---------|--------|-------|-------|
| Weather/solar history | Open-Meteo Historical Archive + NASA POWER (cross-check) | `REAL_COORDINATE_BASED` | 26,304 hourly rows 2022–2024; NASA↔Open-Meteo daily GHI r≈0.87 |
| Substations / grid | OpenStreetMap (Overpass, ODbL) | `REAL_LOCAL` / `REAL_KARNATAKA` | 344 substations ≤45 km; capacity kept `null` (never invented) |
| Grid features | derived from OSM coordinates | `ESTIMATED_FROM_REAL` | geometry only (distances, neighbour density) |
| Load history | Kaggle `smarthkaushal/energy-demand-profile` | `REAL_INDIA` | India NATIONAL hourly demand (MW), 2023–2024; NOT Bengaluru-local |
| Tariff / DSM | KERC + CERC (framework only) | `NEEDS_OFFICIAL_TARIFF_SOURCE` | no rupee values (market-linked & under litigation) |
| Clear-sky GHI | pvlib Ineichen (derived) | `ESTIMATED_FROM_REAL` | used for clearness index / cloud labels |

## Pipeline stages

```
build_ml_datasets.py                        train_all_agents.py
──────────────────────                      ─────────────────────
Open-Meteo archive ─┐                        solar_agent_training  → solar_forecast_model.pkl
NASA POWER (x-check)├─► weather_solar_history ┤cloud_agent_training  → cloud_risk_classifier.pkl
pvlib clear-sky ────┘         │               dsm_agent_training    → dsm_classifier.pkl + dsm_rules_engine.json
OSM Overpass ─► substations_cleaned + grid_features
Kaggle ───────► karnataka_or_india_load_history → load_agent_training → load_forecast_model.pkl
(no official tariff rupees, no local load) ─────────────────────────► rl: SKIPPED (honest)
```

## ML files (`backend/data/ml/`)

| File | Rows | Label |
|------|------|-------|
| `bengaluru_weather_solar_history.parquet` | 26,304 | `REAL_COORDINATE_BASED` |
| `bengaluru_substations_cleaned.parquet` | 344 | `REAL_LOCAL`/`REAL_KARNATAKA` |
| `bengaluru_grid_features.parquet` | 344 | `ESTIMATED_FROM_REAL` |
| `karnataka_or_india_load_history.parquet` | 11,664 | `REAL_INDIA` |
| `solar_agent_training.parquet` | 26,304 | `REAL_COORDINATE_BASED` |
| `cloud_agent_training.parquet` | 12,041 | `REAL_COORDINATE_BASED` |
| `dsm_agent_training.parquet` | 12,031 | `REAL_COORDINATE_BASED` |
| `load_agent_training.parquet` | 11,496 | `REAL_INDIA` |
| `rl_environment_dataset.parquet` | — | `NOT_AVAILABLE` (not written) |
| `tariff_dsm_rules_official_or_pending.json` | — | `NEEDS_OFFICIAL_TARIFF_SOURCE` |
| `dataset_build_manifest.json` | — | build provenance manifest |

Feature/label definitions (clear-sky, clearness index, drop threshold, DSM band, load
lags) are documented in [`formulas.md`](formulas.md).

## Trained models (`backend/models/trained/`) + cards (`backend/models/metadata/`)

| Model | Type | Metric | production_ready |
|-------|------|--------|------------------|
| `solar_forecast_model.pkl` | HistGradientBoosting (irradiance) | R²=0.956, RMSE=57.5 W/m² | ✅ (irradiance only) |
| `cloud_risk_classifier.pkl` | RandomForest | F1=0.67, AUC=0.90 | ✅ |
| `dsm_classifier.pkl` + `dsm_rules_engine.json` | RF + framework rules | F1=0.79, AUC=0.75 | ✅ (no rupees) |
| `load_forecast_model.pkl` | HistGradientBoosting | R²=0.88, RMSE=6260 MW | ❌ REAL_INDIA national, not local |
| `rl_policy.zip` | — | not trained | ❌ INSUFFICIENT_REAL_ENVIRONMENT_DATA |

Each model has a card in `backend/models/metadata/*_card.json` with the full required
schema (training/target geography, domain shift, synthetic %, non-local %, metrics,
limitations, production status).

## API (provenance-carrying)

Mounted under `/api/v1` (see `app/api/routes_agents.py`):
- `GET /agents/status`, `GET /agents/data-status`
- `POST /agents/solar/forecast` → irradiance (W/m²), never PV
- `POST /agents/cloud/risk` → irradiance-drop probability
- `POST /agents/dsm/assess` → deviation-breach risk + framework recommendation (no rupees;
  returns `NOT_AVAILABLE` if no day-ahead schedule is supplied)

Every response includes: `prediction_type, prediction_value, unit, model_file,
model_version, training_geography, target_geography, local_data_used, source_status,
confidence_components, limitations, production_ready, warnings`.

## Reproduce

```bash
cd backend
python -m app.ml.build_ml_datasets --region bengaluru --data-mode real
python -m app.ml.train_all_agents  --region bengaluru --data-mode real
python -m pytest tests/ -q
```

`--data-mode real` forbids any synthetic fallback: if a real source is unavailable, the
corresponding file/model is skipped and marked `NOT_AVAILABLE` rather than faked.
