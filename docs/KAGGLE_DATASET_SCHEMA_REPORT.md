# Kaggle Dataset Schema Report (Phase 1.7)

Schemas verified by reading the actual downloaded files (pandas). Row counts are exact
(full-file). Detected-variable columns use: A=AC power, D=DC power, I=irradiation/GHI,
T=temperature, MT=module temp, L=load, TS=timestamp, G=geography.

## 1. anikannal/solar-power-generation-data  (REAL_INDIA PV)
Four files (two plants), 15-minute cadence, ~34 days (May-June 2020).

| File | Rows | Columns | Detected |
|------|-----:|---------|----------|
| Plant_1_Generation_Data.csv | 68,778 | DATE_TIME, PLANT_ID, SOURCE_KEY, DC_POWER, AC_POWER, DAILY_YIELD, TOTAL_YIELD | A,D,TS |
| Plant_1_Weather_Sensor_Data.csv | 3,182 | DATE_TIME, PLANT_ID, SOURCE_KEY, AMBIENT_TEMPERATURE, MODULE_TEMPERATURE, IRRADIATION | I,T,MT,TS |
| Plant_2_Generation_Data.csv | 67,698 | (same as P1 generation) | A,D,TS |
| Plant_2_Weather_Sensor_Data.csv | 3,259 | (same as P1 weather) | I,T,MT,TS |

Notes (honest):
- **Timestamp formats differ between files**: Plant_1 generation uses `DD-MM-YYYY HH:MM`
  (dayfirst); weather files and Plant_2 generation use ISO `YYYY-MM-DD HH:MM:SS`. Parsing
  must be format-robust.
- 22 inverters (SOURCE_KEY) per plant; weather is plant-level (one sensor).
  Modelling joins per-inverter generation to plant weather on the timestamp.
- `IRRADIATION` is normalised (max ~1.22, not W/m2). `AC_POWER` max ~1411 (kW, per inverter).
  Plant_1 `DC_POWER` max ~14471 is ~10x AC (a known unit/scaling anomaly in this dataset);
  we therefore model **AC_POWER** from irradiation+temperature, which is physically sound.
- No latitude/longitude in the data -> geography = `REAL_INDIA` (site unspecified).

## 2. meenakshihihihihi/time-series-solar-irradiance-for-indian-cities  (REAL_BENGALURU)
Per-city CSVs; hourly; YEAR range 2023-2025; NASA-POWER-derived parameter names.

| File | Rows | Key columns | Detected |
|------|-----:|-------------|----------|
| Bengluru solar irradiance.csv | 17,568 | YEAR,MO,DY,HR, ALLSKY_SFC_SW_DWN (GHI), SZA, ALLSKY_KT, PRECTOTCORR, T2M, PS | I,T,TS,G |
| Ahmedabad solar irradiance.csv | 17,568 | (as above, + UVA/UVB/PAR/WSC) | I,T,TS,G |
| Mumbai Solar irradiance.csv | 17,568 | (as above) | I,T,TS,G |

Notes:
- **GHI = `ALLSKY_SFC_SW_DWN`** (W/m2), max 1059.2 for Bengaluru; **`ALLSKY_KT`** is the
  clearness index (real, usable for cloud-drop labels).
- `-999` is a fill value (7,349 of 17,568 Bengaluru rows for GHI); treated as missing and
  dropped for training (10,219 valid rows remain).
- Timestamp built from YEAR/MO/DY/HR. Bengaluru city -> `REAL_BENGALURU`; other cities ->
  `REAL_INDIA`.

## 3. shubhamvashisht/hourly-load-india-electrical-load-forecasting  (REAL_INDIA)
Excel workbook (requires openpyxl).

| File | Rows | Columns | Detected |
|------|-----:|---------|----------|
| hourlyLoadDataIndia.xlsx | 46,728 | datetime, National Hourly Demand, Northern/Western/Eastern/**Southern**/North-Eastern Region Hourly Demand (MW) | L,TS |
| monthly_temp.xlsx | 36 | Year, Month, Monthly_load, max_temp | L |

Notes:
- Real hourly demand in MW from 2019-01-01; National demand ~116-119 GW at the sample rows.
- **Southern Region Hourly Demand** is the closest regional proxy to Karnataka but is a
  5-state regional aggregate, not Karnataka -> label `REAL_INDIA`, not `REAL_KARNATAKA`.

## 4. arunkanagolkar/solargeneration  (PRETRAINING_ONLY)
| File | Rows | Columns | Detected |
|------|-----:|---------|----------|
| Generation_data.csv | 118,865 | MODULE_TEMP, Amb_Temp, WIND_Speed, IRR (W/m2), DC Current (A), AC Ir/Iy/Ib (A), AC Power in Watts | A,D,I,T,MT |

Notes:
- **No timestamp and no geography** -> cannot be used for time-series forecasting and
  cannot be confirmed as India/Bengaluru. Units look inconsistent (e.g. WIND_Speed ~47).
- Classified `PRETRAINING_ONLY`; **not** used for any production or time-series model here.

## Training eligibility summary
| Dataset | Time series? | Real target | Eligible model | Geography label |
|---------|:---:|:---:|----------------|-----------------|
| anikannal | yes | AC_POWER (real) | PV AC-power regression | REAL_INDIA |
| Bengaluru irradiance | yes | GHI (real) | irradiance forecast + cloud-drop | REAL_BENGALURU |
| hourly-load-india | yes | demand MW (real) | load forecast (non-local) | REAL_INDIA |
| arunkanagolkar | no | AC power (no TS) | none (pretraining only) | UNKNOWN |
