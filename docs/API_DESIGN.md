# API Design - Suryagrid AI

## Base URL
`/api/v1`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check (DB/Redis status) |
| POST | /sites | Register a solar site |
| GET | /sites | List sites |
| GET | /sites/{id} | Get site |
| GET | /weather/{site_id} | Real hourly irradiance/weather (Open-Meteo) |
| POST | /predict | Single-interval DSM evaluation from explicit irradiance |
| POST | /dsm/check | Standalone DSM classification |
| GET | /timeline/{site_id} | Hourly nowcast + DSM timeline + summary |
| GET | /summary/{site_id} | Day summary |

`weather`, `timeline` and `summary` accept query params so any location works
without first registering a site: `latitude`, `longitude`, `timezone`, `capacity_mw`,
`tilt`, `azimuth`, `scheduled_mw` (blank → clear-sky baseline), `threshold_percent`,
`penalty_rate`, `forecast_days`, `past_days`.

## Response envelope

```json
{
  "success": true,
  "message": "OK",
  "data": { },
  "timestamp": "..."
}
```

Errors return `success: false` with `error_code`, `message`, `details`.

## Timeline entry shape

```json
{
  "timestamp": "2026-06-25T12:00:00+05:30",
  "ghi_w_m2": 862.0,
  "poa_w_m2": 910.3,
  "cloud_cover_percent": 2.0,
  "temperature_c": 38.4,
  "predicted_generation_mw": 72.5,
  "energy_mwh": 72.5,
  "scheduled_generation_mw": 79.0,
  "deviation_mw": 6.5,
  "deviation_percent": 8.2,
  "penalty_status": "NO_PENALTY",
  "estimated_penalty_cost": 0.0,
  "risk_score": 0.0,
  "risk_level": "LOW",
  "confidence_score": 0.99,
  "explanation": "..."
}
```
