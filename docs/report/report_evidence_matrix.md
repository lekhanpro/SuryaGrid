# SuryaGrid AI — Report Evidence Matrix

Every major claim in `suryagrid_final_technical_report.tex` maps to a row here. Verified
2026-07-07. Status legend: VERIFIED (observed this session), DOCUMENTED (stated in a repo
file, not independently run), NOT VERIFIED, PENDING, NOT PRESENT.

## A. Hosted application (http://suryagrid.mithungowda.in/)
| # | Claim | Evidence type | Source / command | Status | Notes |
|---|-------|---------------|------------------|--------|-------|
| A1 | Frontend is live | HTTP response | `curl -i http://suryagrid.mithungowda.in/` | VERIFIED | HTTP 200; `Server: nginx/1.24.0 (Ubuntu)`; `X-Powered-By: Next.js`; title "SuryaGrid AI — Solar DSM Intelligence" |
| A2 | Backend API is live | API response | `curl http://suryagrid.mithungowda.in/api/v1/health` | VERIFIED | HTTP 200 `{status:healthy, environment:production, database:connected (postgresql), redis:connected, record_counts all 0}` |
| A3 | Swagger `/docs` reachable on host | HTTP response | `curl -o/dev/null -w%{http_code} .../docs` | NOT PRESENT | HTTP 404 on hosted path |
| A4 | HTTPS with valid cert for the domain | web_fetch (auto-HTTPS) | web_fetch upgrade attempt | NOT VERIFIED | Cert altname is `apilumi.mithungowda.in`, not suryagrid; site served over HTTP:80 |
| A5 | Cloud provider is AWS EC2/Lightsail | repo file | `deploy.sh` header "Ubuntu EC2/Lightsail (32.197.42.115)" | DOCUMENTED | Not independently confirmable from HTTP; IP 32.197.42.115 |
| A6 | Live deployment = single-instance docker-compose+nginx | inference from A1/A2 + files | `setup-subdomain.sh` (nginx `/api/`→localhost:8080), `docker-compose.yml` | VERIFIED (path) / DOCUMENTED | Matches Path A; record_counts=0 → empty DB |

## B. Repository structure, tests, lint
| # | Claim | Evidence | Source / command | Status | Notes |
|---|-------|----------|------------------|--------|-------|
| B1 | Backend FastAPI, 56 `/api/v1` endpoints | route introspection | `app.main.app.routes` | VERIFIED | 15 routers + kaggle router |
| B2 | 16 agent modules | dir listing + docstrings | `backend/app/agents/*.py` | VERIFIED | subagent read docstrings |
| B3 | 103 backend tests pass | test run | `python -m pytest tests/ -q` | VERIFIED | "103 passed, 1 warning" |
| B4 | Frontend builds | build + hosted | earlier `npm run build` (14 routes) + A1 live | VERIFIED | Next.js 14 App Router |
| B5 | ruff check | lint run | `ruff check app tests` | PARTIAL | "Found 1 error (1 fixable)" — not fixed (no core-logic changes allowed for report) |
| B6 | Docker installed | command | `docker --version` | VERIFIED | 29.6.1 |
| B7 | `docker compose` usable locally | command | `docker compose version` | NOT VERIFIED | "unknown command: docker compose" locally (works on server per A1/A2) |

## C. Kaggle datasets and pipeline
| # | Claim | Evidence | Source | Status | Notes |
|---|-------|----------|--------|--------|-------|
| C1 | 10 Kaggle searches executed | command output | `kaggle datasets list -s ...` (x10) | VERIFIED | prior turn |
| C2 | 4 datasets downloaded (12 raw files) | dir listing | `backend/data/raw/kaggle/` | VERIFIED | pv_generation, solar, load; +arunkanagolkar |
| C3 | anikannal PV = real AC/DC+irradiation, India | file read | Plant_1/2 CSVs | VERIFIED | 68,778+67,698 gen; 3,182+3,259 weather; REAL_INDIA |
| C4 | Bengaluru irradiance file exists | file read | `Bengluru solar irradiance.csv` | VERIFIED | 17,568 rows; GHI=ALLSKY_SFC_SW_DWN; -999 fill (7,349) |
| C5 | India hourly load (xlsx) | file read | `hourlyLoadDataIndia.xlsx` | VERIFIED | 46,728 rows; National+Southern Region MW |
| C6 | arunkanagolkar rejected | file read | `Generation_data.csv` | VERIFIED | no timestamp/geography → PRETRAINING_ONLY |
| C7 | 3 processed parquet created | dir listing | `data/processed/kaggle/` | VERIFIED | pv 136,472; solar 52,704; load 46,728 |
| C8 | 4 ML training parquet created | dir listing | `data/ml/kaggle_*.parquet` | VERIFIED | pv 136,472; solar 10,219; cloud 5,356; load 46,560 |
| C9 | `download-kaggle.sh` targets HI-SEAS | file read | `download-kaggle.sh` DATASET=dronio/SolarEnergy | VERIFIED | Hawaii; separate legacy script, not used by data_pipeline |

## D. Kaggle models (metrics from model cards)
| # | Model | Evidence | Source card | Status | Metrics / prod |
|---|-------|----------|-------------|--------|----------------|
| D1 | kaggle_pv_ac_model | card + pkl | `kaggle_pv_ac_model_card.json` | VERIFIED | R2=0.869, RMSE=118.98 kW, MAE=37.78; REAL_INDIA; prod=false |
| D2 | kaggle_solar_irradiance_bengaluru_model | card + pkl | card json | VERIFIED | R2=0.920, RMSE=74.96 W/m2; REAL_BENGALURU; prod=true |
| D3 | kaggle_cloud_risk_bengaluru_model | card + pkl | card json | VERIFIED | F1=0.847, AUC=0.851; REAL_BENGALURU; prod=true |
| D4 | kaggle_load_forecast_model | card + pkl | card json | VERIFIED | R2=0.893, RMSE=6404.65 MW; REAL_INDIA; prod=false |

## E. Open-Meteo Phase 1.7 datasets/models (prior verified)
| # | Claim | Evidence | Source | Status | Notes |
|---|-------|----------|--------|--------|-------|
| E1 | Bengaluru weather history 26,304 rows | manifest | `dataset_build_manifest.json` | VERIFIED | 2022-2024; peak GHI 1044 W/m2 |
| E2 | NASA POWER cross-check r=0.87 | manifest | manifest nasa_power_cross_check | VERIFIED | 1096 days |
| E3 | solar model R2=0.956 | card | solar_forecast_model_card.json | VERIFIED | irradiance; prod=true |
| E4 | cloud F1=0.67 / dsm F1=0.79 | cards | cards | VERIFIED | prod=true |
| E5 | Open-Meteo load R2=0.88 | card | load_forecast_model_card.json | VERIFIED | REAL_INDIA; prod=false |
| E6 | RL not trained | card | rl_policy_card.json | VERIFIED | INSUFFICIENT_REAL_ENVIRONMENT_DATA; no rl_policy.zip |

## F. Substations / grid
| # | Claim | Evidence | Source | Status | Notes |
|---|-------|----------|--------|--------|-------|
| F1 | 344 OSM substations | manifest | dataset_build_manifest.json | VERIFIED | REAL_BENGALURU/REAL_KARNATAKA |
| F2 | voltage on 41%, capacity 0% | manifest | manifest substations.quality | VERIFIED | capacity null (never invented) |
| F3 | OSM Overpass source | code | `data_sources/substation_provider.py` | VERIFIED | ODbL |
| F4 | KPTCL/BESCOM/CEA capacity | — | — | NOT PRESENT / PENDING | requires official source |

## G. Data sources
| # | Source | Status | Evidence |
|---|--------|--------|----------|
| G1 | Open-Meteo forecast | VERIFIED wired | providers + `source_registry.py` |
| G2 | Open-Meteo archive | VERIFIED used | build manifest (26,304 rows) |
| G3 | NASA POWER | API reachable + build cross-check; live provider PENDING | manifest r=0.87; registry "not yet wired" |
| G4 | Kaggle (India) | Downloaded & used | C2-C8 |
| G5 | OSM/Overpass | VERIFIED used | F1-F3 |
| G6 | KERC/BESCOM/CERC tariff | Framework DOCUMENTED; rupee rates PENDING | DSM_RULE_SOURCES.md; dsm profiles STATUS_PENDING |
| G7 | CEA/Grid India/SLDC | Documented only / NOT wired | research doc |
| G8 | Synthetic weather | Present, labelled; blocked in real mode | synthetic_weather_provider.py; provenance guard |

## H. Formulas (verbatim from docs/code)
| # | Formula | Source file | Class |
|---|---------|-------------|-------|
| H1 | clearsky Ineichen (pvlib), alt 920m | formulas.md; agent_models.py | OFFICIAL (pvlib) |
| H2 | kt = GHI/clearsky (daylight, clip 0-1.2) | formulas.md | derived |
| H3 | cloud drop label kt<0.5 | formulas.md; build_kaggle_ml_datasets.py | engineering heuristic |
| H4 | DSM band ±15% (ML path) | formulas.md | FALLBACK_DEFAULT |
| H5 | Erbs/POA/Faiman/PVWatts DC | FORMULA_SOURCES.md | OFFICIAL (pvlib) |
| H6 | PV proxy = (POA/1000)*cap*eff*PR(0.80) | FORMULA_SOURCES.md; agent_models.py | FALLBACK_DEFAULT (PR) |
| H7 | confidence = clamp(1-0.35*cloud,0.4,0.99) | FORMULA_SOURCES.md | FALLBACK_DEFAULT |
| H8 | gamma_pdc=-0.0035; inverter eff=0.96 | FORMULA_SOURCES.md | FALLBACK_DEFAULT (PVWatts) |
| H9 | KERC ±5% band + slabs ₹2/4/6/kWh | DSM_RULE_SOURCES.md; india_dsm_rules.py | framework OFFICIAL; slab rates PENDING |
| H10 | deviation %, slab energy, dsm_charge | dsm_engine.py; FORMULA_SOURCES.md | formula OFFICIAL; rates PENDING |

## I. Deployment files (declared, not all verified live)
| # | Artifact | Status | Notes |
|---|----------|--------|-------|
| I1 | docker-compose.yml (4 svc, 8080:8000) | VERIFIED present; live per A1/A2 | postgres16-alpine/redis7/backend/frontend |
| I2 | deploy.sh (EC2/Lightsail) | DOCUMENTED | IP 32.197.42.115 |
| I3 | nginx.conf + setup-subdomain.sh | DOCUMENTED; consistent with live | listen 80; /api/→8080 |
| I4 | infra/terraform ECS/RDS/Redis/S3/CloudFront | DOCUMENTED (code only) | ap-south-1; HTTPS/ACM commented; no tfvars; NOT verified deployed |
| I5 | deploy-aws.yml (ECS+S3/CloudFront) | DOCUMENTED | OIDC; not verified run |
| I6 | deploy.yml (GitHub Pages) | DOCUMENTED | separate from AWS |

## J. Intentional downgrades (missing evidence)
| # | Downgraded claim | Reason |
|---|------------------|--------|
| J1 | "official tariff integrated" | rupee rates PENDING (DSM profiles STATUS_PENDING) |
| J2 | "local PV generation available" | anikannal is REAL_INDIA plant, not Bengaluru; prod=false |
| J3 | "AWS ECS stack deployed" | only single-instance docker-compose verified live; ECS is code-only |
| J4 | "fully production-ready" | load/RL non-prod; tariff pending; capacity missing |
| J5 | "Kaggle UI-surfaced" | frontend lib/api.ts has no /kaggle/* calls |
| J6 | "HTTPS secured" | host served on HTTP:80; cert mismatch |
