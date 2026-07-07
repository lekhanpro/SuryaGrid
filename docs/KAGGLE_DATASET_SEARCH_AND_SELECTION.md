# Kaggle Dataset Search and Selection (Phase 1.7)

Real Kaggle searches run on 2026-07-07 with the configured Kaggle CLI (user `lekhanpro`).
No dataset is claimed as downloaded unless it exists under
`backend/data/raw/kaggle/`. Sizes are the Kaggle-reported archive sizes.

## Searches executed (verbatim)
```
kaggle datasets list -s "india solar"
kaggle datasets list -s "solar power generation india"
kaggle datasets list -s "india solar power generation"
kaggle datasets list -s "solar irradiance india"
kaggle datasets list -s "karnataka electricity"
kaggle datasets list -s "india electricity load"
kaggle datasets list -s "india power demand"
kaggle datasets list -s "smart meter india"
kaggle datasets list -s "electricity consumption india"
kaggle datasets list -s "pv generation"
```

## Selected and DOWNLOADED datasets

| Slug | Title | Geography | Key variables | Size | Downloaded | Final use |
|------|-------|-----------|---------------|------|-----------|-----------|
| `anikannal/solar-power-generation-data` | Solar Power Generation Data | India (2 plants, unspecified site) | DATE_TIME, DC_POWER, AC_POWER, IRRADIATION, AMBIENT/MODULE_TEMPERATURE | 1.9 MB | yes | PV AC-power training (REAL_INDIA) |
| `meenakshihihihihi/time-series-solar-irradiance-for-indian-cities` | Time Series Solar Irradiance for Indian Cities | India incl. **Bengaluru** | YEAR/MO/DY/HR, ALLSKY_SFC_SW_DWN (GHI), ALLSKY_KT, T2M, PS, PRECTOTCORR, SZA | 762 KB | yes | Bengaluru irradiance + cloud training (REAL_BENGALURU) |
| `shubhamvashisht/hourly-load-india-electrical-load-forecasting` | Hourly Load India | India (National + 5 regions incl. Southern) | datetime, National/Southern/... Hourly Demand (MW) | 3.0 MB | yes | Load training (REAL_INDIA; Southern Region proxy) |
| `arunkanagolkar/solargeneration` | SolarGeneration | Unspecified | MODULE_TEMP, Amb_Temp, WIND_Speed, IRR (W/m2), AC Power (W) | 10.4 MB | yes | PRETRAINING_ONLY (no timestamp, unknown geography) |

Raw files saved under:
```
backend/data/raw/kaggle/pv_generation/anikannal_solar_power_generation/
backend/data/raw/kaggle/solar/india_cities_irradiance/
backend/data/raw/kaggle/solar/arunkanagolkar_solargeneration/
backend/data/raw/kaggle/load/hourly_load_india/
```

## Rejected / deferred (with reason)

| Slug | Reason |
|------|--------|
| `unseemlycoder/smart-energy-meters-in-bangalore-india` | Bengaluru-specific and high value, but **1.0 GB** archive; deferred to avoid a very large download. Candidate for a future dedicated ingest. |
| `pythonafroz/electricity-smart-meter-data-from-india` (184 MB), `jehanbhathena/smart-meter-data-mathura-and-bareilly` (184 MB) | Large; non-Karnataka (UP cities). Deferred. |
| `aryanpatel212/india-solar-site-selection-data` (1.1 GB), `narendersingh007/india-solar-benchmark-dataset` (829 MB) | Very large; site-selection/benchmark, not a clean time series. Deferred. |
| `mexwell/solar-pv-generation-time-series` (250 MB), `tecsci/brazilian-pv-dataset` (807 MB) | Non-local (global/Brazil) and large. Not production truth for Bengaluru. |
| `krishnadaskv/daily-power-generation-in-india-2013-2023` | India daily generation (coarse, not hourly PV/irradiance). Not needed. |
| `harshmishra00/state-wise-solar-irradiance-dataset-of-india` (2 KB) | Summary table, not a time series. |
| `smarthkaushal/energy-demand-profile` | Already ingested in a prior phase (India national hourly). Superseded here by the richer `hourly-load-india` (regional breakdown, more rows). |
| HI-SEAS (`dronio/SolarEnergy`) | Hawaii; **must not** be Bengaluru production truth. Not downloaded. |

## Geography labelling decisions
- `anikannal` PV: Indian plants, exact site not stated -> `REAL_INDIA` (usable for PV AC training, but not Bengaluru-local; domain shift for a Bengaluru rooftop).
- `meenakshihihihihi` Bengaluru city extract -> `REAL_BENGALURU` (NASA-POWER-derived, Bengaluru coordinate); other cities (Ahmedabad, Mumbai) -> `REAL_INDIA`.
- `hourly-load-india` -> `REAL_INDIA` (National); Southern Region column is the closest regional proxy to Karnataka but is **not** `REAL_KARNATAKA`.
- `arunkanagolkar` -> no timestamp, unknown geography -> `PRETRAINING_ONLY` / not used for production or time-series.
