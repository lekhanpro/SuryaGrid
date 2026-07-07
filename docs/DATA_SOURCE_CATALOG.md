# SuryaGrid AI — Data Source Catalog

Catalog of every real data source the platform can ingest, with access method,
fields, units, limits, license, and status. Machine-readable mirror:
`backend/app/data_sources/source_registry.py`. Status API: `GET /api/v1/sources`.

Providers implement `app/data_sources/base_provider.py::DataProvider` and report a
`status()` — **no silent fallback**: if a real source is unavailable, its status says so.

---

## 1. Live weather forecast — Open-Meteo `SRC-OPENMETEO-001`  (PRIMARY, live)

| Property | Value |
|----------|-------|
| Provider class | `live_weather_provider.LiveWeatherProvider` (wraps `providers/open_meteo.py`) |
| Endpoint | `https://api.open-meteo.com/v1/forecast` (+ `archive-api.open-meteo.com/v1/archive`) |
| Auth | none (key-less) |
| License | CC BY 4.0, free non-commercial; attribution required |
| Units | irradiance W/m², temp °C, humidity %, cloud %, wind m/s, pressure hPa, precip-prob % |
| Horizon | up to 16 days; hourly; `current` block ~15-min; archive = ERA5 history |
| Limits | fair-use ≈10k calls/day; we cache in Redis + persist to DB to avoid re-calls |
| Fields | shortwave_radiation, direct_normal_irradiance, diffuse_radiation, temperature_2m, relative_humidity_2m, cloud_cover, wind_speed_10m, surface_pressure, precipitation_probability, weather_code |
| Status | ✅ implemented & live |

## 2. Historical ML dataset — Kaggle Solar Radiation Prediction `SRC-KAGGLE-SOLAR-001`

| Property | Value |
|----------|-------|
| Provider class | `kaggle_solar_provider.KaggleSolarProvider` |
| Dataset | `dronio/SolarEnergy` — NASA HI-SEAS meteorological data (2016) |
| URL | https://www.kaggle.com/datasets/dronio/SolarEnergy |
| Auth | Kaggle API `KAGGLE_USERNAME` + `KAGGLE_KEY` (never commit `kaggle.json`) |
| Manual fallback | drop CSV in `backend/data/raw/kaggle/` (no credentials needed) |
| License | public-domain style per dataset page (verify before redistribution) |
| Target | `Radiation` (W/m²) — solar irradiance (no plant generation column) |
| Columns | UNIXTime, Data, Time, Radiation, Temperature(°F), Pressure(inHg), Humidity(%), WindDirection(Degrees), Speed(mph), TimeSunRise, TimeSunSet |
| Conversions | °F→°C, inHg→hPa, mph→m/s (see `FORMULA_SOURCES.md#unit-conversions`) |
| Detection | provider reports `loaded: true/false`; **"Kaggle dataset not loaded"** if absent |
| Status | ✅ implemented (ingest + normalize); requires creds OR manual file to load data |

> Because the dataset provides **irradiance, not plant generation**, the ML model predicts
> irradiance and generation is derived via the pvlib pipeline (`FORMULA_SOURCES.md#irradiance-to-gen`).

## 3. Substation / grid locations — OpenStreetMap Overpass `SRC-OSM-SUBSTATION-001`

| Property | Value |
|----------|-------|
| Provider class | `substation_provider.SubstationProvider` |
| Endpoint | `https://overpass-api.de/api/interpreter` |
| Query | `node/way/relation["power"="substation"](bbox);` |
| Auth | none |
| License | ODbL 1.0 — "© OpenStreetMap contributors"; share-alike |
| Fields | name, voltage, operator, lat, lon (+ district/state when tagged) |
| Confidence | `source_confidence`: OSM=0.6 default, operator CSV=1.0 |
| Manual fallback | CSV import via `POST /api/v1/substations/import` |
| Coordinates | used as published; **never invented** |
| Status | ✅ implemented (Overpass fetch + CSV import) |

## 4. Synthetic fallback — Phase 1 synthetic provider (TEST/OFFLINE ONLY)

| Property | Value |
|----------|-------|
| Provider class | `synthetic_weather_provider.SyntheticWeatherProvider` |
| Purpose | deterministic offline data for tests & when live sources are down |
| Behaviour | clear-sky diurnal irradiance shape + configurable cloud noise (seeded) |
| Status | ✅ implemented — **labelled `synthetic` in every response**; never presented as real |

## 5. Reserved future providers (modular slots, not yet wired)

| Provider | Source ID | Notes |
|----------|-----------|-------|
| NASA POWER | `SRC-NASA-POWER-001` | free reanalysis; endpoint known; slot reserved |
| Solcast | `SRC-SOLCAST-001` | commercial, API key; slot reserved |

Adding one = implement `DataProvider` + register in `source_registry.py` + `APIAgent`.
The pvlib/ML pipeline is provider-agnostic and runs unchanged.

---

## 6. Augmented dataset (built from the above)

`app/ml/dataset_builder.py` joins Kaggle history + live-weather features + site + schedule
+ nearest-substation distance into the canonical augmented schema (see `ML_PIPELINE.md`).
Every row carries `source_provider` and `quality_flag`. Data-quality checks:
missing values, invalid units, invalid/duplicate timestamps, impossible irradiance
(<0 or >1500 W/m²), negative generation, generation-above-capacity, bad coordinates.

## 7. Status endpoint contract

`GET /api/v1/sources` → list of `{id, name, type, classification, license, url,
access_date, status, available, detail}`. `GET /api/v1/sources/{id}` → one record with
fields/units. `GET /api/v1/system/status` aggregates provider availability.
