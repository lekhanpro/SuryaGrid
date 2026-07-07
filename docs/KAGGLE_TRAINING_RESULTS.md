# Kaggle Training Results (Phase 1.7)

Real Kaggle datasets only. All numbers below are from actual downloads, processed
parquet, and training runs on 2026-07-07 (`--data-mode real`). Model cards in
`backend/models/metadata/kaggle_*_card.json`; run manifest in
`kaggle_training_run_manifest.json`.

## Datasets downloaded (raw)
| Slug | Raw path | Rows (raw) | Label |
|------|----------|-----------|-------|
| anikannal/solar-power-generation-data | `raw/kaggle/pv_generation/anikannal_solar_power_generation/` | 68,778+67,698 gen; 3,182+3,259 weather | REAL_INDIA |
| meenakshihihihihi/time-series-solar-irradiance-for-indian-cities | `raw/kaggle/solar/india_cities_irradiance/` | 17,568 x 3 cities | REAL_BENGALURU / REAL_INDIA |
| shubhamvashisht/hourly-load-india-electrical-load-forecasting | `raw/kaggle/load/hourly_load_india/` | 46,728 (xlsx) | REAL_INDIA |
| arunkanagolkar/solargeneration | `raw/kaggle/solar/arunkanagolkar_solargeneration/` | 118,865 | PRETRAINING_ONLY (rejected: no timestamp/geo) |

## Processed files created (`backend/data/processed/kaggle/`)
| File | Rows |
|------|-----:|
| kaggle_pv_generation_processed.parquet | 136,472 |
| kaggle_solar_processed.parquet | 52,704 (17,568 Bengaluru) |
| kaggle_load_processed.parquet | 46,728 |

## ML training files created (`backend/data/ml/`)
| File | Rows | Target |
|------|-----:|--------|
| kaggle_pv_ac_training.parquet | 136,472 | ac_power |
| kaggle_solar_irradiance_training.parquet | 10,219 | ghi_wm2 |
| kaggle_cloud_training.parquet | 5,356 | irradiance_drop_risk |
| kaggle_load_training.parquet | 46,560 | national_demand_mw |

## Results table

| Agent | Dataset (slug) | Geography | Rows (tr/te) | Target | Model file | Metrics | Prod? | Limitation |
|-------|----------------|-----------|-------------|--------|-----------|---------|-------|-----------|
| PV AC power | anikannal/solar-power-generation-data | REAL_INDIA | 109,177 / 27,295 | ac_power (kW) | kaggle_pv_ac_model.pkl | R2=0.869, RMSE=118.98, MAE=37.78, MAPE=15.6% | no | India plant, 34-day window, not Bengaluru (domain shift) |
| Solar irradiance | meenakshihihihihi/...indian-cities | REAL_BENGALURU | 8,175 / 2,044 | ghi_wm2 | kaggle_solar_irradiance_bengaluru_model.pkl | R2=0.920, RMSE=74.96, MAE=40.05 | yes | GHI only, not PV; secondary to Open-Meteo model |
| Cloud drop-risk | meenakshihihihihi/...indian-cities | REAL_BENGALURU | 4,284 / 1,072 | irradiance_drop_risk | kaggle_cloud_risk_bengaluru_model.pkl | F1=0.847, AUC=0.851, acc=0.790 | yes | label from real ALLSKY_KT<0.5; irradiance drop, not PV |
| Load forecast | shubhamvashisht/hourly-load-india | REAL_INDIA | 37,248 / 9,312 | national_demand_mw | kaggle_load_forecast_model.pkl | R2=0.893, RMSE=6404.65 MW, MAPE=2.5% | no | India national, not Karnataka (domain shift HIGH) |

Chronological 80/20 split for every model. All cards: `uses_synthetic_data=false`,
`synthetic_percentage=0`, `data_mode=real`.

## Models skipped / not trained
- **RL policy** - not trained (unchanged from Phase 1.7): no official tariff rupee reward
  and no real Karnataka load. `rl_policy_card.json` remains
  `production_ready=false`, `reason=INSUFFICIENT_REAL_ENVIRONMENT_DATA`.
- **DSM rupee charges** - not computed: no official KERC/BESCOM/CERC rates parsed
  (`NEEDS_OFFICIAL_TARIFF_SOURCE`). The existing framework rules engine is unchanged.

## Non-local data usage (honest)
- PV AC model and load model are trained on **real Indian** data that is **not
  Bengaluru-local** (`REAL_INDIA`); both are marked `production_ready=false` for a
  Bengaluru target with an explicit reason. `non_local_data_percentage=0` because
  REAL_INDIA is real Indian (not foreign) data; the non-locality is captured by
  `local_data_available=false` + `domain_shift_risk`.
- The Bengaluru irradiance and cloud models use the Bengaluru city extract
  (`REAL_BENGALURU`).

## Non-destructive note
These Kaggle artifacts are `kaggle_`-prefixed and do **not** overwrite the existing
Open-Meteo Phase 1.7 models/datasets. The Open-Meteo Bengaluru solar model
($R^2=0.956$) remains the primary irradiance model.

## Exact commands to reproduce
```bash
cd backend
kaggle datasets download -d anikannal/solar-power-generation-data -p data/raw/kaggle/pv_generation/anikannal_solar_power_generation --unzip
kaggle datasets download -d meenakshihihihihi/time-series-solar-irradiance-for-indian-cities -p data/raw/kaggle/solar/india_cities_irradiance --unzip
kaggle datasets download -d shubhamvashisht/hourly-load-india-electrical-load-forecasting -p data/raw/kaggle/load/hourly_load_india --unzip
python -m app.data_pipeline.ingest_kaggle_pv_generation --data-mode real
python -m app.data_pipeline.ingest_kaggle_solar --data-mode real
python -m app.data_pipeline.ingest_kaggle_load --data-mode real
python -m app.ml.build_kaggle_ml_datasets --data-mode real
python -m app.ml.train_from_kaggle --data-mode real
python -m pytest tests/ -q
```

## Frontend
Not redesigned. The existing dashboard `ModelProvenancePanel` reads `/agents/status`
(Open-Meteo agents). Surfacing the Kaggle models in the UI is **pending frontend
integration** (backend exposes them at `/api/v1/kaggle/*`).
