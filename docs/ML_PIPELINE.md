# SuryaGrid AI — ML Pipeline

Real-data solar forecasting: Kaggle history → augmented dataset → scikit-learn model
→ formula/ml/hybrid forecasting. All numeric math is deterministic code; no LLM.

See also: `DATA_SOURCE_CATALOG.md`, `FORMULA_SOURCES.md`, `SOURCE_REGISTRY.md`.

---

## 1. Stages

```
Kaggle / live-weather / synthetic source frame
        │  (unit-normalized: F→C, inHg→hPa, mph→m/s)
        ▼
FeatureEngineeringAgent → dataset_builder.build_augmented()
        │  canonical 20-column augmented schema + data-quality flags
        ▼
train_model.train()  → scikit-learn regressor  → model_registry (joblib + metadata.json)
        ▼
predict_model.ModelPredictor  → ForecastAgent (ml / hybrid)  → pvlib → generation
```

Code: `backend/app/ml/` (`feature_engineering.py`, `data_quality.py`, `dataset_builder.py`,
`train_model.py`, `model_registry.py`, `predict_model.py`) and `agents/forecast_agent.py`.

## 2. Augmented dataset schema (canonical)

`timestamp, hour_of_day, day_of_year, month, latitude, longitude, irradiance_w_m2,
cloud_cover_percent, temperature_c, humidity_percent, wind_speed_mps,
precipitation_probability_percent, pressure_hpa, site_capacity_mw, panel_efficiency,
nearest_substation_distance_km, scheduled_generation_mw, actual_generation_mw,
source_provider, quality_flag`

Every row carries `source_provider` and `quality_flag` (1 good / 0 flagged).

## 3. Data-quality checks (`data_quality.py`)

Missing values · invalid units · invalid timestamps · duplicate timestamps · impossible
irradiance (`<0` or `>1500` W/m²) · negative generation · generation above capacity ·
bad coordinates. Bad rows are **flagged, not silently dropped**; training excludes flagged rows.

## 4. Target selection

- If the dataset has real plant generation → target = `actual_generation_mw`.
- Otherwise (the Kaggle HI-SEAS case) → target = `irradiance_w_m2`. The model predicts
  irradiance and generation is derived via the pvlib pipeline
  (`FORMULA_SOURCES.md#irradiance-to-gen`). This is reported in `target_type`.

## 5. Models & metrics

Candidates (scikit-learn only — no heavy frameworks): `random_forest`,
`gradient_boosting`, `hist_gradient_boosting`, `linear` (baseline).
`model_name="auto"` trains all and keeps the best by test **RMSE**.
Metrics recorded: **MAE, RMSE, MAPE, R²** (`sklearn.metrics`, RMSE via `sqrt(MSE)`).

## 6. Model registry (`backend/models/`)

- `solar_forecast_model.joblib` — `{estimator, feature_columns}`.
- `model_metadata.json` — training dataset, columns used, target + target_type, model type,
  metrics, training date, `model_version`, **source_references**, and **limitations**.

`SURYAGRID_MODELS_DIR` overrides the directory (used by tests).

## 7. Forecast modes (`ForecastAgent`)

| Mode | Behaviour |
|------|-----------|
| `formula` | pvlib physics only (baseline & fallback). |
| `ml` | model predicts irradiance → pvlib → generation. |
| `hybrid` | mean of formula and ml generation. |
| `auto` | hybrid when a valid model exists, else formula fallback (reported). |

Every forecast point reports `forecast_mode`, `model_version`, `confidence_score`,
and `source_used`. If `ml`/`hybrid` is requested with no trained model, it falls back to
`formula` and says so — never silently.

## 8. API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/ml/datasets/ingest-kaggle` | Download via Kaggle API (if creds set). |
| POST | `/api/v1/ml/datasets/build-augmented?source=kaggle\|weather\|synthetic` | Build + persist the augmented dataset. |
| POST | `/api/v1/ml/train?model_name=auto` | Train and register a model. |
| GET | `/api/v1/ml/model/status` | Model + dataset + Kaggle status. |
| POST | `/api/v1/ml/predict` | Single-interval formula/ml/hybrid prediction. |

## 9. How to train (quick start)

```bash
# 1. (optional) load Kaggle data — or drop the CSV in backend/data/raw/kaggle/
curl -X POST http://localhost:8000/api/v1/ml/datasets/ingest-kaggle
# 2. build the augmented dataset (kaggle if loaded, else weather/synthetic)
curl -X POST "http://localhost:8000/api/v1/ml/datasets/build-augmented?source=kaggle"
# 3. train (auto-selects the best candidate)
curl -X POST "http://localhost:8000/api/v1/ml/train?model_name=auto"
# 4. check status
curl http://localhost:8000/api/v1/ml/model/status
```

If the Kaggle dataset is absent, step 1 reports it clearly and you can build from
`weather`/`synthetic` instead (labelled accordingly in `source_provider`).

## 10. Limitations (honesty)

Decision-support estimates, not a settlement of record. Model accuracy depends on how
representative the training data is of the target site/season. The HI-SEAS Kaggle set is
irradiance-only and Hawaii-based; for a specific Indian plant, ingest local generation
history and retrain. All limitations are recorded in `model_metadata.json`.
