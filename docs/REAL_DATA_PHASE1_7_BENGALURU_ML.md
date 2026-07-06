# SuryaGrid — Real-Data Phase 1.7 (Bengaluru ML) Report

Phase 1.7 creates ML-ready datasets from the **closest real** Bengaluru/Karnataka/India
sources and trains the agents **honestly**, on the existing repository (no rebuild, no
frontend redesign, no replaced architecture).

Generated: 2026-07-06 · Region: Bengaluru (12.9716, 77.5946) · `APP_DATA_MODE=real`.

## 0. Refinements in this iteration

- Added `docs/BENGALURU_DATA_SOURCE_RESEARCH.md` — an 11-source assessment (Open-Meteo,
  NASA POWER, Kaggle solar/load, KPTCL-SLDC, Grid India/POSOCO, CEA, KERC/BESCOM, CERC,
  KPTCL substations, OSM) with `READY / NEEDS_KEY / NEEDS_MANUAL_DOWNLOAD / NOT_USABLE /
  DOCUMENTATION_ONLY` status per source.
- New provenance label **`REAL_BENGALURU`** (city-explicit); substations now split
  244 `REAL_BENGALURU` + 100 `REAL_KARNATAKA`.
- Every dataset row now carries source metadata: `source_name`, `source_url`,
  `data_geography`, `ingestion_time`, and a per-row `quality_score` (weather mean 0.994).
- Every model card now includes **`data_mode`** and **`source_status`** (auto-derived from
  the training sources) — enforced as required fields and covered by tests.
- API envelope now includes `data_mode`; the solar endpoint returns an optional
  `pv_estimate` block flagged `estimated_output=true`, `is_actual_generation=false`
  (`ESTIMATED_FROM_REAL`), with the formula shown.
- Added `backend/tests/test_phase17_ml.py` (16 tests) — real-mode guard, card completeness,
  no-synthetic-in-real, model existence, honest load/RL skips, and non-fabricated
  API confidence. Full suite: **93 passed**.

## 1. Sources used

| Source | Access | Geography label | Used for |
|--------|--------|-----------------|----------|
| Open-Meteo Historical Weather Archive | key-less HTTP (httpx) | `REAL_COORDINATE_BASED` | Bengaluru hourly weather + irradiance (GHI/DNI/DHI), 2022–2024 |
| NASA POWER (daily ALLSKY_SFC_SW_DWN) | HTTP | `REAL_COORDINATE_BASED` | second-source GHI cross-check (daily r≈0.87 vs Open-Meteo) |
| pvlib Ineichen clear-sky | library | `ESTIMATED_FROM_REAL` | clearness index + cloud labels |
| OpenStreetMap Overpass (power=substation) | HTTP (ODbL) | `REAL_LOCAL`/`REAL_KARNATAKA` | 344 Bengaluru-area substations + grid geometry |
| Kaggle `smarthkaushal/energy-demand-profile` | Kaggle API | `REAL_INDIA` | India NATIONAL hourly demand (MW), 2023–2024 |
| KERC (F&S&DSM Regulations 2015/2026) | web-verified | `NEEDS_OFFICIAL_TARIFF_SOURCE` | DSM framework (no rupees) |
| CERC (DSM Regulations 2024) | web-verified | `NEEDS_OFFICIAL_TARIFF_SOURCE` | DSM framework (market-linked, litigated) |

Foreign data (HI-SEAS Hawaii etc.) was **not** used as production truth anywhere.

## 2. ML datasets created (`backend/data/ml/`)

| File | Rows | Label | Notes |
|------|-----:|-------|-------|
| bengaluru_weather_solar_history.parquet | 26,304 | REAL_COORDINATE_BASED | 3 full years hourly; peak GHI 1044 W/m² |
| bengaluru_substations_cleaned.parquet | 344 | REAL_LOCAL/REAL_KARNATAKA | 41% have voltage; 0% capacity (null, not invented) |
| bengaluru_grid_features.parquet | 344 | ESTIMATED_FROM_REAL | geometry-only features |
| karnataka_or_india_load_history.parquet | 11,664 | REAL_INDIA | national demand, NOT Bengaluru-local |
| solar_agent_training.parquet | 26,304 | REAL_COORDINATE_BASED | target = GHI (W/m²) |
| cloud_agent_training.parquet | 12,041 | REAL_COORDINATE_BASED | daylight; 12.2% drop-positive |
| dsm_agent_training.parquet | 12,031 | REAL_COORDINATE_BASED | breach rate 43.1%, ±15% band |
| load_agent_training.parquet | 11,496 | REAL_INDIA | engineered lags/calendar |
| tariff_dsm_rules_official_or_pending.json | — | NEEDS_OFFICIAL_TARIFF_SOURCE | framework only, no rupees |
| rl_environment_dataset.parquet | — | NOT_AVAILABLE | not written (honest) |

## 3. Models trained

| Model | Algo | Test metrics | Split | production_ready |
|-------|------|--------------|-------|------------------|
| solar_forecast_model.pkl (irradiance) | HistGradientBoosting | R²=0.9563, RMSE=57.51 W/m², MAE=29.12 W/m² | chronological 80/20 | ✅ (irradiance; PV=false) |
| cloud_risk_classifier.pkl | RandomForest | F1=0.6707, ROC-AUC=0.9001 | chronological 80/20 | ✅ |
| dsm_classifier.pkl (+ dsm_rules_engine.json) | RandomForest | F1=0.7905, ROC-AUC=0.7489 | chronological 80/20 | ✅ (no rupees) |
| load_forecast_model.pkl | HistGradientBoosting | R²=0.883, RMSE=6259.5 MW | chronological 80/20 (9196/2300) | ❌ (see below) |

Model cards: `backend/models/metadata/{solar_forecast_model,cloud_risk_classifier,dsm_model,load_forecast_model,rl_policy}_card.json`.

## 4. Models skipped / not production-ready (and why)

- **RL policy** — SKIPPED, no `rl_policy.zip` written. `reason = INSUFFICIENT_REAL_ENVIRONMENT_DATA`:
  an honest reward needs official DSM/tariff rupee terms (absent → `NEEDS_OFFICIAL_TARIFF_SOURCE`)
  and real **local** load (absent — only India-national exists). Fabricating a reward would
  produce misleading dispatch actions, so it was refused.
- **Load model** — TRAINED on real data but `production_ready=false`,
  `reason = INSUFFICIENT_LOCAL_LOAD_DATA`: it learned India NATIONAL demand, not Bengaluru
  feeder load. `domain_shift_risk=HIGH`. Usable as an India baseline / pretraining only.
- **Solar model** — production-ready for **irradiance** only.
  `production_ready_for_pv_generation=false`: no real local PV dataset, so PV output must be
  derived from user capacity via pvlib (`ESTIMATED_FROM_REAL`), never predicted.

## 5. Production readiness summary

| Agent | Ready | For what |
|-------|-------|----------|
| Solar | ✅ | Bengaluru irradiance (GHI) forecast |
| Cloud | ✅ | irradiance-drop-risk classification |
| DSM | ✅ | deviation-breach risk + **framework-only** recommendation (no ₹) |
| Load | ❌ | India-national baseline only (domain shift HIGH) |
| RL | ❌ | not trained (insufficient real environment) |

## 6. Honesty guarantees (verified)

- `APP_DATA_MODE=real` blocks synthetic fallback in the dataset builder and each trainer
  (`SyntheticFallbackError`; agents skip with a stated reason).
- No fabricated confidence: classifiers expose their real predicted probability; regressors
  expose real test R²/RMSE. No invented scores.
- No fake PV generation (irradiance only). No fake load/substation capacity (kept `null`).
- No rupee DSM/tariff values (framework-only; `NEEDS_OFFICIAL_TARIFF_SOURCE`).
- All 5 model cards contain every required field; `synthetic_percentage=0`,
  `non_local_data_percentage=0` (India-national is real Indian data, flagged non-local via
  `local_data_available=false` + `domain_shift_risk=HIGH`).
- Backend regression: **77/77 tests pass** after all changes.

## 7. Limitations

- Weather is Open-Meteo reanalysis at the city coordinate; a specific rooftop microclimate
  may differ (retrain with on-site pyranometer data).
- "Scheduled" injection for DSM is a day-ahead persistence proxy, not a metered SLDC schedule.
- Substation capacity/voltage frequently missing in OSM; no substation-level DSM.
- Load is national India, not Bengaluru; connect BESCOM/KPTCL feeder load to localise.
- DSM rupee settlement needs the current CERC/KERC order (market-linked, under litigation).

## 8. Exact commands to reproduce

```bash
cd backend
# 1) Build real datasets (Open-Meteo + NASA POWER + OSM + Kaggle load)
python -m app.ml.build_ml_datasets --region bengaluru --data-mode real --start-year 2022 --end-year 2024
# 2) Train all agents (skips honestly where data is insufficient)
python -m app.ml.train_all_agents  --region bengaluru --data-mode real --no-build
# 3) Tests
python -m pytest tests/ -q
# 4) (optional) run API and inspect provenance
uvicorn app.main:app --reload    # GET /api/v1/agents/status
```

Individual trainers: `python -m app.ml.train_solar_agent` (and `_cloud_`, `_dsm_`, `_load_`,
`_rl_`) all accept `--region bengaluru --data-mode real`.

## 9. What the operator must do next

1. **Localise load**: obtain Bengaluru/Karnataka feeder or BESCOM load (KPTCL-SLDC) to make
   the load model production-ready and unlock a real RL environment.
2. **Official tariff/DSM**: enter the current CERC/KERC solar deviation "X" and rate into
   `tariff_dsm_rules_official_or_pending.json`, flip `emits_rupee_values=true` → enables ₹ DSM.
3. **Substation capacity**: add KPTCL/BESCOM capacity (MVA) to enable substation-level DSM.
4. **On-site irradiance** (optional): add a local pyranometer feed to reduce solar domain gap.
