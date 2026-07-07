# Application Flow — End-to-End Prediction Pipeline

This document traces the complete data flow from a user clicking "Run Full Prediction"
to seeing results on the dashboard. It explains the DSM logic, fuzzy risk system,
why PENALTY_RISK appears, and how to interpret every field.

---

## Table of Contents

1. [High-Level Pipeline](#1-high-level-pipeline)
2. [Step-by-Step Flow](#2-step-by-step-flow)
3. [Forecast Agent (Solar Generation Prediction)](#3-forecast-agent)
4. [DSM Engine (Deviation Settlement Mechanism)](#4-dsm-engine)
5. [Fuzzy Risk Agent](#5-fuzzy-risk-agent)
6. [Why PENALTY_RISK Appears (and How to Get NO_PENALTY)](#6-why-penalty_risk-appears)
7. [Dashboard Data Mapping](#7-dashboard-data-mapping)
8. [API Response Schema](#8-api-response-schema)

---

## 1. High-Level Pipeline

```
┌──────────────┐   ┌───────────────┐   ┌────────────────┐   ┌────────────────┐   ┌─────────────┐
│   Frontend   │──▶│  Live Weather │──▶│  Forecast Agent │──▶│   DSM Engine   │──▶│ Fuzzy Risk  │
│  Dashboard   │   │  (Open-Meteo) │   │ (pvlib / ML)   │   │  (KERC/CERC)   │   │   Agent     │
└──────────────┘   └───────────────┘   └────────────────┘   └────────────────┘   └─────────────┘
       │                                                                                  │
       │                         ┌──────────────┐                                         │
       │◀────────────────────────│ Orchestrator │◀────────────────────────────────────────┘
       │                         │    Agent     │
       │                         └──────────────┘
       │                               │
       │                    ┌──────────▼──────────┐
       │                    │  Persistence Agent  │
       │                    │   (PostgreSQL)      │
       │                    └─────────────────────┘
       │
       ▼
  [Dashboard renders: Predicted MW, Deviation %, Risk Gauge, DSM Charge, Explanation]
```

---

## 2. Step-by-Step Flow

When the user clicks **"Run Full Prediction"** on the dashboard:

### Step 1: Frontend Request
```
GET /api/v1/predict/primary-site?latitude=14.10&longitude=77.28&capacity_mw=2050&mode=auto&regulator=KERC/BESCOM
```
- Parallel request also fetches the 24-hour timeline for the chart.

### Step 2: Site Resolution
The `OrchestratorAgent.run_full()` method resolves the site:
- Looks up or creates a site record in the database
- Finds the nearest substation (for ML features + display)

### Step 3: Live Weather Fetch
`LiveWeatherAgent.latest()` calls Open-Meteo:
- Fetches: GHI, DNI, DHI, temperature, cloud cover, wind speed, humidity, pressure
- **Caches in Redis** (1-hour TTL for forecast, 15-min for current conditions)
- If Open-Meteo fails → falls back to synthetic provider but **marks it** (`weather_mode: "synthetic"`)
- Never silently fakes data

### Step 4: Solar Generation Forecast
`ForecastAgent.forecast_timeline()` predicts generation:
- **Formula mode**: pvlib physics (solar position → POA irradiance → cell temp → PVWatts DC → inverter AC)
- **ML mode**: scikit-learn model predicts irradiance → convert via pvlib
- **Hybrid mode**: average of formula + ML
- **Auto mode**: hybrid if model available, formula fallback
- Also computes `clearsky_generation_mw` (theoretical max, no clouds)

### Step 5: Scheduled Generation Default
```python
scheduled = scheduled_generation_mw if provided else clearsky_generation_mw
```
- If user provides a value → use it
- If blank → **use clear-sky** (theoretical max) as the "declared schedule"

### Step 6: Advanced DSM Evaluation
`DSMEngineAgent.evaluate()` compares predicted vs. scheduled:
- Resolves the regulatory profile (KERC/BESCOM, CERC, or generic)
- Computes deviation % against the profile's denominator
- Applies slab-based charges if deviation exceeds tolerance band

### Step 7: Fuzzy Risk Scoring
`FuzzyRiskAgent.score()` produces the 0-100 risk score:
- Combines breach + uncertainty + volatility via fuzzy inference
- Returns: score (0-100) + level (LOW/MEDIUM/HIGH/CRITICAL)

### Step 8: Explanation + Sources
- `ExplanationAgent.explain()` generates a human-readable summary
- `SourceRegistry.cite()` attaches provenance citations

### Step 9: Persist + Return
- Saves forecast + DSM result to PostgreSQL
- Returns full response to frontend

---

## 3. Forecast Agent

### Physics Model (pvlib)

The formula mode replicates how a real solar plant performs:

```
Solar Position (lat, lon, time)
        │
        ▼
  Direct Normal Irradiance (DNI)      GHI from weather
  Diffuse Horizontal (DHI)            ────────┐
        │                                      │
        ▼                                      ▼
  Plane-of-Array (POA) Irradiance ◀── Transposition (tilt, azimuth)
        │
        ▼
  Cell Temperature (Faiman model, wind + ambient temp)
        │
        ▼
  DC Power (PVWatts: POA × capacity × efficiency × temp coeff)
        │
        ▼
  AC Power (× inverter efficiency 0.96)
        │
        ▼
  predicted_generation_mw
```

### Clear-Sky Baseline

pvlib computes what the plant **would** generate with zero clouds. This becomes
the `clearsky_generation_mw` value — used as the default "schedule" when the user
doesn't specify one.

### ML Mode

When trained (Kaggle solar dataset or weather-based):
- Features: GHI, DNI, DHI, temperature, cloud cover, wind speed, humidity, pressure, panel_efficiency, substation_distance
- Target: irradiance → converted to generation via pvlib
- Model: scikit-learn (GradientBoosting/RandomForest, selected by auto-training)

### Confidence Score

```python
confidence = 1.0 - (cloud_cover / 200) - abs(ghi_predicted - ghi_clearsky) / max(ghi_clearsky, 1)
```
Clamped to [0.3, 0.99]. Higher confidence when conditions match clear-sky.

---

## 4. DSM Engine

### What is DSM?

The **Deviation Settlement Mechanism** is the Indian power grid's penalty system.
Solar generators must declare their expected generation (schedule) for each 15-min
time block. If actual generation deviates beyond the allowed band, a financial
charge applies.

### How it works in SuryaGrid

```
                    ┌─────────────────────┐
                    │  Rule Profile       │
                    │  (KERC/BESCOM/CERC) │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │                                             │
        │  deviation_% = |predicted - scheduled|      │
        │                 ─────────────────────       │
        │                    denominator              │
        │                                             │
        │  denominator = installed_capacity (KERC)    │
        │            OR = scheduled (simple mode)     │
        │                                             │
        └──────────────────────┬──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ deviation_% ≤ band? │
                    └──────────┬──────────┘
                       │              │
                      YES            NO
                       │              │
                       ▼              ▼
              ┌────────────┐  ┌──────────────────────────────┐
              │ NO_PENALTY │  │ PENALTY_RISK                 │
              │ charge = 0 │  │ Apply slab charges to energy │
              │            │  │ beyond the tolerance band    │
              └────────────┘  └──────────────────────────────┘
```

### Rule Profiles

| Profile | Regulator | Tolerance Band | Denominator | Slab Rates |
|---------|-----------|----------------|-------------|------------|
| KERC/BESCOM Solar | KERC/BESCOM | 15% | Available Capacity | Escalating slabs (15-25%, 25-35%, >35%) |
| CERC (central) | CERC | 10% | Available Capacity | Different rates for under/over injection |
| Generic (default) | (operator) | 10% | Scheduled | Flat ₹12/kWh beyond band |

### Slab-Based Charging (KERC Example)

```
Tolerance band: 15%
Slab 1 (15-25%):  ₹1.50/kWh on energy in this range
Slab 2 (25-35%):  ₹2.50/kWh on energy in this range
Slab 3 (>35%):    ₹3.50/kWh on energy in this range

Charge = Σ (pct_in_slab / 100) × denominator_MW × interval_hours × rate
```

### Deviation Direction

- `UNDER_INJECTION`: predicted < scheduled (plant generating less than declared)
- `OVER_INJECTION`: predicted > scheduled (plant generating more than declared)
- `WITHIN_LIMIT`: deviation within tolerance band

---

## 5. Fuzzy Risk Agent

### Why Fuzzy Logic?

A hard threshold (penalty/no-penalty) doesn't capture operational risk. You might
be technically within the band but very close to breaching it, or your forecast
might be uncertain due to clouds. The fuzzy system captures this nuance.

### Three Input Dimensions

| Input | Source | Normalized Range |
|-------|--------|-----------------|
| **Breach** | How far deviation exceeds tolerance band | 0 = within band, 1 = 2× band exceeded |
| **Uncertainty** | 1 - confidence_score | 0 = very confident, 1 = very uncertain |
| **Volatility** | cloud_cover / 100 | 0 = clear sky, 1 = fully overcast |

### Fuzzy Membership Functions

Each input is fuzzified into LOW / MEDIUM / HIGH using triangular membership:

```
        LOW          MEDIUM         HIGH
  1.0 ──┐╲         ╱╲            ╱┌──
        │  ╲      ╱  ╲          ╱ │
        │   ╲    ╱    ╲        ╱  │
  0.0 ──┼────╲──╱──────╲──────╱──┤───
        0   0.4  0.2  0.5  0.8  0.6  1.0
```

### Rule Base (Mamdani-Style)

| # | Condition | → Output |
|---|-----------|----------|
| 1 | Breach HIGH | CRITICAL |
| 2 | Breach MEDIUM AND (Uncertainty HIGH OR MEDIUM) | CRITICAL |
| 3 | Breach MEDIUM | HIGH |
| 4 | Uncertainty HIGH AND Volatility HIGH | HIGH |
| 5 | Breach LOW AND Uncertainty HIGH | MEDIUM |
| 6 | Breach LOW AND Volatility HIGH | MEDIUM |
| 7 | Breach LOW AND Uncertainty LOW AND NOT Volatility HIGH | LOW |

### Defuzzification

Centroid method over 0-100 output universe:
```
score = Σ(x × μ_aggregated(x)) / Σ(μ_aggregated(x))   for x = 0..100
```

### Risk Levels

| Score Range | Level |
|-------------|-------|
| 0 – 24 | LOW |
| 25 – 49 | MEDIUM |
| 50 – 74 | HIGH |
| 75 – 100 | CRITICAL |

---

## 6. Why PENALTY_RISK Appears

### The Root Cause

When the user leaves **"Scheduled MW"** blank on the dashboard, the system defaults
to **clear-sky generation** as the schedule:

```python
scheduled = clearsky_generation_mw  # theoretical max (no clouds)
```

Real weather **always** has some clouds, temperature losses, and atmospheric effects,
so:

```
predicted_generation (real weather) < clearsky_generation (ideal)

deviation = |predicted - scheduled| / denominator × 100
         = |1200 - 1800| / 2050 × 100
         = 29.3%    ← exceeds 15% band → PENALTY_RISK
```

### This is Correct Behavior

The system is answering: *"If you declared clear-sky as your schedule and the real
weather produces less, would you face a DSM penalty?"* — and the answer is usually YES.

### How to See NO_PENALTY

| Method | How | When it works |
|--------|-----|---------------|
| Enter realistic schedule | Type a value in "Scheduled MW" close to what you expect | Always — if predicted ≈ scheduled |
| Wait for peak solar noon | Clear day + maximum GHI | predicted ≈ clearsky → low deviation |
| Use a conservative schedule | Set scheduled below expected output | Creates headroom in the band |

### Example

```
Capacity: 2050 MW (Pavagada)
Clear-sky at noon: 1800 MW
Real predicted (cloud 30%): 1250 MW
Deviation: |1250 - 1800| / 2050 = 26.8% → PENALTY_RISK

Fix: Set scheduled_mw = 1300
Deviation: |1250 - 1300| / 2050 = 2.4% → NO_PENALTY ✓
```

---

## 7. Dashboard Data Mapping

| Dashboard Element | API Field | Description |
|-------------------|-----------|-------------|
| Predicted (now) | `predicted_generation_mw` | Current nowcast from forecast agent |
| Scheduled | `scheduled_generation_mw` | Declared or clear-sky baseline |
| Deviation % | `deviation_percent` | Absolute % deviation from schedule |
| Deviation direction | `deviation_direction` | UNDER / OVER / WITHIN |
| Est. DSM Charge | `estimated_dsm_charge` | ₹ penalty estimate (0 if no penalty) |
| DSM Band | `dsm_band` | Which slab the deviation falls in |
| Penalty Status | `penalty_status` | PENALTY_RISK / NO_PENALTY / INVALID_SCHEDULE |
| Fuzzy Risk Score | `fuzzy_risk_score` | 0-100 composite risk |
| Fuzzy Risk Level | `fuzzy_risk_level` | LOW / MEDIUM / HIGH / CRITICAL |
| Confidence | `confidence_score` | 0-1 forecast confidence |
| GHI | `ghi_w_m2` | Ground-level solar irradiance (W/m²) |
| Cloud Cover | `cloud_cover_percent` | Current cloud coverage (%) |
| Weather Mode | `weather_mode` | "real" or "synthetic" (never hidden) |
| Forecast Mode | `forecast_mode` | formula / ml / hybrid |
| DSM Profile | `dsm_profile` | Rule set used (KERC/BESCOM, CERC, etc.) |
| Nearest Substation | `nearest_substation` | Name + distance from OSM data |
| Sources | `sources[]` | Provenance citations for all data used |
| Explanation | `explanation` | Human-readable summary of the result |

---

## 8. API Response Schema

Full response from `GET /api/v1/predict/{site_id}`:

```json
{
  "site_id": "primary-site",
  "timestamp": "2026-07-07T07:12:00+00:00",
  "forecast_mode": "formula",
  "model_version": null,
  "source_used": "formula:pvlib",
  "data_sources": ["live_weather"],
  "weather_mode": "real",
  "ghi_w_m2": 612.3,
  "cloud_cover_percent": 42.0,
  "temperature_c": 31.2,
  "capacity_mw": 2050.0,
  "predicted_generation_mw": 1247.83,
  "scheduled_generation_mw": 1802.45,
  "deviation_mw": -554.62,
  "deviation_percent": 27.05,
  "deviation_direction": "UNDER_INJECTION",
  "dsm_band": "25-35%",
  "penalty_status": "PENALTY_RISK",
  "charge_rate": 2.5,
  "estimated_dsm_charge": 18450.00,
  "dsm_profile": "kerc-bescom-solar",
  "rule_source": {
    "name": "KERC DSM Order 2021",
    "url": "https://kerc.karnataka.gov.in/...",
    "status": "PENDING_OFFICIAL_GAZETTE",
    "profile": "kerc-bescom-solar",
    "regulator": "KERC/BESCOM",
    "denominator": "available_capacity"
  },
  "fuzzy_risk_score": 62.4,
  "fuzzy_risk_level": "HIGH",
  "confidence_score": 0.71,
  "nearest_substation": {
    "name": "Pavagada 220kV",
    "distance_km": 3.2,
    "source": "OpenStreetMap"
  },
  "sources": [
    { "id": "SRC-PVLIB-001", "name": "pvlib", "classification": "FORMULA" },
    { "id": "SRC-OPENMETEO-001", "name": "Open-Meteo", "classification": "LIVE_DATA" }
  ],
  "explanation": "Penalty risk: 27.1% deviation (under-injection) exceeds the 15% band under KERC/BESCOM rules. Estimated DSM charge: ₹18,450. (Rates are configurable/pending official source; not authoritative.)",
  "persisted": true
}
```

---

## Summary of Key Design Decisions

1. **Clear-sky as default schedule** — worst-case conservative; shows the maximum
   possible DSM exposure. Real operators would set their own declared schedule.

2. **Never fake data** — synthetic weather is labeled. "Backend Offline" banner
   shows instead of stale numbers.

3. **Slab-based DSM (not flat)** — mirrors real Indian regulatory structure where
   higher deviations attract progressively higher charges.

4. **Fuzzy risk adds operational nuance** — even within the DSM band, high
   uncertainty or cloud volatility can push risk up.

5. **All math is deterministic** — no LLM touches the numbers. Every formula,
   threshold, and rate is traceable to a source citation.
