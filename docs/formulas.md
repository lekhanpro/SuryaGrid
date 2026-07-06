# SuryaGrid Phase 1.7 - Formulas & Threshold Logic

Every derived label/feature in the Phase 1.7 ML datasets is defined here so nothing is
a black box. All are computed from REAL Bengaluru coordinate data (Open-Meteo archive +
pvlib), unless stated otherwise.

## 1. Clear-sky GHI (pvlib Ineichen)

For each hourly timestamp we compute the clear-sky global horizontal irradiance for
Bengaluru using pvlib:

```
Location(lat=12.9716, lon=77.5946, tz="Asia/Kolkata", altitude=920 m)
clearsky_ghi_wm2 = Location.get_clearsky(times, model="ineichen")["ghi"]
```

`altitude = 920 m` is Bengaluru's approximate mean elevation.

## 2. Clearness index (kt)

```
clearness_index (kt) = shortwave_radiation_wm2 / clearsky_ghi_wm2
```

- Defined only for **daylight** hours where `clearsky_ghi_wm2 > 50 W/m2`
  (`is_daylight = 1`). Night hours are excluded (kt is undefined at night).
- Clipped to [0.0, 1.2] to absorb minor reanalysis/clear-sky mismatch.

## 3. Cloud agent label - irradiance_drop_risk

```
irradiance_drop_risk = 1  if  kt < 0.5   (during daylight)
                     = 0  otherwise
```

- Threshold **0.5** is a modelling choice: a clearness index below 0.5 means the
  measured GHI is less than half the clear-sky expectation, i.e. a **significant
  irradiance drop** (cloud/haze). It is NOT a regulatory definition.
- This labels an **IRRADIANCE** drop, not a PV-output drop (no real local PV dataset).
- Bengaluru observed positive rate ~ 12.2% of daylight hours (2022-2024).

## 4. DSM agent - scheduled proxy, deviation, and band

Day-ahead persistence baseline (no metered SLDC schedule available):

```
scheduled_ghi_wm2(t) = shortwave_radiation_wm2(t - 24h)      # same hour, previous day
deviation_percent(t) = 100 * (actual - scheduled) / scheduled   # daylight only
```

Deviation band classification (MODELLING parameter, `band = 15%`):

```
WITHIN_BAND     : |deviation_percent| <= 15
OVER_INJECTION  : deviation_percent  >  15
UNDER_INJECTION : deviation_percent  < -15
breach_risk = 0 if WITHIN_BAND else 1
```

- The `+/-15%` band is a `FALLBACK_DEFAULT`, **not** an official KERC/CERC value. The
  official solar deviation "X" and rupee charges are market-linked and pending
  (`NEEDS_OFFICIAL_TARIFF_SOURCE`; see `docs/tariff_and_dsm_source_verification.md`).
- No rupee DSM charge is computed anywhere in Phase 1.7.

## 5. Cyclical time encodings (all agents)

```
hour_sin = sin(2*pi*hour/24),   hour_cos = cos(2*pi*hour/24)
doy_sin  = sin(2*pi*doy/365.25), doy_cos = cos(2*pi*doy/365.25)
dow_sin  = sin(2*pi*dow/7),      dow_cos = cos(2*pi*dow/7)   # load agent only
```

## 6. Load agent (India national baseline) features

```
lag_24h      = load_value(t - 24h)
lag_168h     = load_value(t - 168h)          # same hour, previous week
roll_24h_mean = mean(load_value[t-24 .. t-1]) # trailing 24h mean, shifted to avoid leakage
```

## 7. PV generation (NOT predicted)

There is no real local PV generation dataset, so PV output is **never** predicted by a
model. When a user supplies plant capacity, PV output is derived from forecast irradiance
via the existing pvlib pipeline. Any PV number is therefore `ESTIMATED_FROM_REAL`
irradiance + user capacity, and is flagged as an estimate, not a measurement.

## 8. NASA POWER cross-check

Open-Meteo daily GHI energy (`sum(shortwave_radiation_wm2)/1000` kWh/m2/day) is compared
to NASA POWER `ALLSKY_SFC_SW_DWN` daily GHI for the same dates. Pearson r and means are
recorded in `backend/data/ml/dataset_build_manifest.json` (Bengaluru 2022-2024: r ~ 0.87).
