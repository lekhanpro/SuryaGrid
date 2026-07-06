# SuryaGrid AI — API Reference (Phase 1.5)

Base URL: `http://localhost:8000/api/v1` · Swagger UI: `http://localhost:8000/docs`

Every response is `{"success": bool, "message": str, "data": ..., "timestamp": iso}`.
Errors return `success:false` with `error_code` and HTTP 4xx/5xx.

## Health & system
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | DB engine, Redis, record counts. |
| GET | `/system/status` | DB / Redis / weather providers / Kaggle / model / counts. |

## Sources (source registry)
| GET | `/sources?type=` | All source records (weather/dataset/substation/formula/dsm_rule). |
| GET | `/sources/{source_id}` | One source record (404 if unknown). |
| GET | `/data-sources/status` | Live provider status (kaggle/live-weather/substation/synthetic). |

## Sites
| POST | `/sites` · GET `/sites` · GET `/sites/{id}` | Register / list / get sites. |

## Locations & substations
| GET | `/locations` · `/locations/available` | Discoverable locations. |
| GET | `/substations` | List imported substations. |
| POST | `/substations/import` | OSM (`latitude`,`longitude`,`radius_km`) or CSV (`csv_text`). |
| GET | `/substations/nearest/{site_id}` | Nearest substation + distance (haversine). |
| GET | `/sites/{site_id}/data-coverage` | Coverage flags. |

## Weather
| GET | `/weather/{site_id}` | Raw hourly weather (persisted for registered sites). |
| POST | `/weather/fetch` | Live fetch for a coordinate (Redis-cached; horizon param). |
| GET | `/weather/latest/{site_id}` | Latest current conditions. |
| GET | `/weather/forecast/{site_id}` | Forecast over a horizon (persisted). |
| GET | `/weather/providers/status` | Live + fallback provider status. |

## ML
| POST | `/ml/datasets/ingest-kaggle` | Download Kaggle dataset (if creds). |
| POST | `/ml/datasets/build-augmented?source=kaggle\|weather\|synthetic` | Build augmented dataset. |
| POST | `/ml/train?model_name=auto` | Train + register a model. |
| GET | `/ml/model/status` | Model + dataset + Kaggle status. |
| POST | `/ml/predict` | Single-interval formula/ml/hybrid prediction. |

## Forecast & prediction
| POST | `/predict` | Single-interval DSM eval from explicit inputs. |
| GET | `/predict/{site_id}` | **Full end-to-end prediction** (see schema below). |
| GET | `/forecast/{site_id}?mode=auto&horizon=24h` | Mode-aware generation timeline. |
| GET | `/timeline/{site_id}` · `/summary/{site_id}` | 24h DSM timeline / day summary. |

## DSM
| GET | `/dsm/rule-profiles` · POST `/dsm/rule-profiles` · GET `/dsm/rule-profiles/{id}` | Configurable profiles. |
| POST | `/dsm/check` | Simple threshold classification. |
| POST | `/dsm/advanced-check` | Advanced rule-profile deviation + charge + source. |
| POST | `/dsm/karnataka/{site_id}` | KERC/BESCOM day settlement. |

## Existing extras (Phase 1)
`/energy/{id}`, `/settle`, `/settle/day/{id}`, `/settlements/{id}`, `/rl/rates`,
`/rl/runs`, `/rl/train`, `/consumption/profiles`, `/karnataka/seed`, `/karnataka/regions`,
`/bescom/status`, `/weather/current/{id}`, `/ingest/current/{id}`.

**Total: 49 endpoints.**

---

## Full prediction response — `GET /predict/{site_id}`

```json
{
  "site_id": "primary-site",
  "timestamp": "2026-07-05T12:00:00+00:00",
  "forecast_mode": "hybrid",
  "model_version": "20260705120000",
  "source_used": "hybrid:formula+ml(random_forest)",
  "data_sources": ["live_weather", "kaggle"],
  "weather_mode": "real",
  "ghi_w_m2": 812.0,
  "cloud_cover_percent": 18.0,
  "temperature_c": 33.1,
  "capacity_mw": 2050.0,
  "predicted_generation_mw": 1523.4,
  "scheduled_generation_mw": 1600.0,
  "deviation_mw": -76.6,
  "deviation_percent": 3.7,
  "deviation_direction": "UNDER_INJECTION",
  "dsm_band": "within_band",
  "penalty_status": "NO_PENALTY",
  "charge_rate": 0.0,
  "estimated_dsm_charge": 0.0,
  "dsm_profile": "kerc-solar",
  "rule_source": {"name": "KERC ...", "url": "https://karnatakaerc.gov.in", "status": "USER_CONFIGURABLE_PENDING_OFFICIAL_SOURCE"},
  "fuzzy_risk_score": 18.4,
  "fuzzy_risk_level": "LOW",
  "confidence_score": 0.9,
  "nearest_substation": {"name": "...", "distance_km": 5.2, "source": "OpenStreetMap (Overpass)"},
  "sources": [
    {"id": "SRC-OPENMETEO-001", "name": "Open-Meteo Forecast API", "type": "weather", "classification": "OFFICIAL_SOURCE", "reference": "https://open-meteo.com/en/docs"},
    {"id": "SRC-KAGGLE-SOLAR-001", "name": "Kaggle Solar Radiation Prediction (NASA HI-SEAS)", "type": "dataset", "classification": "OFFICIAL_SOURCE", "reference": "..."},
    {"id": "SRC-PVLIB-001", "name": "pvlib-python ...", "type": "formula", "classification": "OFFICIAL_SOURCE", "reference": "..."},
    {"id": "SRC-KERC-DSM", "name": "KERC ...", "type": "dsm_rule", "classification": "USER_CONFIGURABLE_PENDING_OFFICIAL_SOURCE", "reference": "..."}
  ],
  "explanation": "Within band: ...",
  "persisted": false
}
```

Query params: `latitude, longitude, timezone, capacity_mw, tilt, azimuth,
panel_efficiency, scheduled_mw, mode (auto|formula|ml|hybrid), region, regulator,
rule_profile_id`.
