# Substation-Driven Agent Workflow

When a substation is selected from the dropdown, it becomes the **central context object**
that flows through every agent — weather → solar irradiance → cloud risk → generation
timeline → DSM — and the response carries a full **agent trace** and **calculation trace**
so every number can be traced to its source. Nothing is fabricated: fields that are missing
in the real data stay `null` and their dependent calculations are explicitly blocked.

- **Data source:** 344 real Bengaluru substations from OpenStreetMap (Overpass, ODbL),
  `backend/data/ml/bengaluru_substations_cleaned.parquet`.
- **Backend:** `SubstationContext` (schema) → `SubstationContextService` → `SubstationOrchestrator`
  → `routes_substation_orchestrate` (API).
- **Frontend:** `components/SubstationWorkflowPanel.tsx` (dropdown → run → results), wired into
  the Locations and DSM pages.

---

## 1. The context object — `SubstationContext`

`backend/app/schemas/substation_context.py`. Built by `SubstationContextService.get_context()`
from one parquet row, coercing every form of missing value (`None`, `NaN`, `"nan"/"none"/"null"/""`)
to `None`.

| Field | Source | Notes |
|-------|--------|-------|
| `substation_id`, `name`, `latitude`, `longitude` | OSM (always present) | Coordinates used as-is, never invented. |
| `operator` | OSM (147/344 present) | `null` when unknown. |
| `voltage_kv` | OSM (141/344 present) | 66 / 110 / 220 / 230 / 400 kV. `null` otherwise. |
| `capacity_mva` | **unavailable in OSM (0/344)** | Always `null` → `capacity_status = NOT_AVAILABLE`. Never fabricated. |
| `district` | **unavailable in OSM (0/344)** | Always `null`. |
| `source_label` | OSM ingestion | `REAL_BENGALURU` or `REAL_KARNATAKA`. |
| `reliability_score`, `missing_fields`, `data_geography`, `ingestion_time` | OSM ingestion | Provenance. |
| `display_label` | derived | e.g. `"220/33kV GIS Sub Station, Central Silk Board - 220 kV"` or `"… - voltage unknown"`. |
| `distance_from_site_km` | derived (haversine) | Only when a site lat/lon is supplied. |
| `capacity_status` / `voltage_status` / `load_data_status` / `tariff_status` / `source_status` | derived | Honest per-field status flags. |
| `limitation_notes` | derived | Human-readable honesty notes. |

**Honesty rule:** a missing real field is `null` + `*_status = NOT_AVAILABLE`; it is never
replaced by a plausible guess.

---

## 2. The workflow — `SubstationOrchestrator`

`backend/app/agents/substation_orchestrator.py`, method `run(context, *, site_capacity_mw,
forecast_horizon_hours, scheduled_generation_mw, use_live_weather, start_time)` (async).

```
SubstationContext
   │
   ▼  (1) SubstationContextAgent   → loads the selected substation as the context object
   ▼  (2) WeatherAgent             → Open-Meteo @ the substation's OWN coordinates,
   │                                  degrading to pvlib clear-sky physics if unreachable
   ▼  (3) SolarIrradianceAgent     → solar_forecast_model.pkl → GHI (W/m²) per hour
   ▼  (4) CloudRiskAgent           → cloud_risk_classifier.pkl → P(kt<0.5) per hour
   ▼  (5) GenerationTimelineAgent  → GHI + USER plant capacity → ESTIMATED PV (MW) per hour
   ▼  (6) DSMAgent                 → deviation-breach risk + honest, framework-only DSM
   ▼  (7) OrchestratorAgent        → assembles the context-linked result + provenance
```

Each step appends to `workflow.agent_trace[]` (`step`, `agent`, `action`, `status`,
`source_label`, `detail`) and every computed quantity records its formula and provenance in
`workflow.calculation_trace{}`.

### Weather (real, per-coordinate, offline-capable)

- **Live:** `OpenMeteoProvider.fetch_forecast()` at the substation's lat/lon →
  `REAL_COORDINATE_BASED`. Each substation therefore gets its own weather.
- **Degraded (never synthetic):** if the network is unreachable, pvlib Ineichen clear-sky GHI
  is computed at the substation coordinates (still `REAL_COORDINATE_BASED` physics). A limitation
  note is added; no invented data is used. `use_live_weather=false` forces this path (used by tests).

### Generation (ESTIMATED, never measured)

```
estimated_generation_mw = site_capacity_mw × (forecast_GHI_wm2 / 1000) × performance_ratio(0.80)
```

- `site_capacity_mw` is the **USER's plant capacity**, *not* the substation `capacity_mva`
  (which is unavailable). Every timeline row is labelled `generation_type = ESTIMATED_FROM_IRRADIANCE`,
  `actual_generation_available = false`, and carries the `substation_id`.
- Without `site_capacity_mw`, generation is reported as irradiance only (`estimated_generation_mw = null`).

### DSM (framework-only, context-gated)

See **[DSM_SUBSTATION_INPUT_TRACE.md](DSM_SUBSTATION_INPUT_TRACE.md)** for the full input trace.
Summary: capacity/voltage/load/tariff that have no real source **block** their calculation
(listed in `blocked_calculations`); no rupee charge is ever emitted.

---

## 3. API endpoints

Base URL `http://<host>/api/v1`. Every response is the standard
`{success, message, data, timestamp}` envelope.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/substations/catalog?limit=` | Dropdown-ready list: `substation_id`, `display_label`, coords, `voltage_kv`, `reliability_score`. Sorted by reliability. |
| GET | `/substations/{substation_id}` | Full `SubstationContext` (404 if unknown). |
| POST | `/orchestrate/substation` | Run the whole workflow for the selected substation. |
| POST | `/dsm/forecast` | Substation-context DSM forecast (framework-only, no rupees). |
| GET | `/generation/timeline?substation_id=&site_capacity_mw=&forecast_horizon_hours=&allow_estimated=&use_live_weather=` | Generation timeline. `allow_estimated=false` suppresses the estimate honestly (only real irradiance is shown). |

`POST /orchestrate/substation` and `POST /dsm/forecast` body:

```json
{
  "substation_id": "OSM-1299917513",
  "site_capacity_mw": 50,
  "scheduled_generation_mw": 20,
  "forecast_horizon_hours": 12,
  "use_live_weather": true,
  "site_latitude": null,
  "site_longitude": null
}
```

### Example (`POST /orchestrate/substation`) — abridged

```json
{
  "success": true,
  "data": {
    "substation": { "substation_id": "OSM-1299917513", "display_label": "… - 220 kV",
      "capacity_mva": null, "capacity_status": "NOT_AVAILABLE",
      "voltage_kv": 220.0, "voltage_status": "REAL_BENGALURU",
      "source_status": "REAL_BENGALURU", "missing_fields": ["capacity_mva", "district", "operator"] },
    "workflow": {
      "agent_trace": [ {"step":1,"agent":"SubstationContextAgent","status":"ok"}, … 7 steps … ],
      "calculation_trace": {
        "clearsky_ghi_wm2": {"formula":"pvlib Ineichen clear-sky GHI at substation (lat, lon)","source_label":"REAL_COORDINATE_BASED"},
        "forecast_ghi_wm2": {"model_file":"backend/models/trained/solar_forecast_model.pkl","source_label":"REAL_BENGALURU"},
        "estimated_generation_mw": {"formula":"site_capacity_mw * (forecast_GHI_wm2 / 1000) * performance_ratio","source_label":"ESTIMATED_FROM_REAL"}
      }
    },
    "generation_timeline": [ {"timestamp":"…T12:00:00","substation_id":"OSM-1299917513",
      "forecast_ghi_wm2":881.22,"estimated_generation_mw":35.249,
      "generation_type":"ESTIMATED_FROM_IRRADIANCE","actual_generation_available":false}, … ],
    "generation_summary": {"peak_estimated_generation_mw":35.249,"total_estimated_energy_mwh":259.665},
    "dsm_forecast": {"emits_rupee_values":false,"deviation_percent":8.19,
      "deviation_band":"WITHIN_MODELLING_BAND(+/-15%)","capacity_status":"NOT_AVAILABLE",
      "blocked_calculations":[{"calculation":"substation_loading_percent","reason":"…"}, …]},
    "data_sources": [ … ], "limitations": [ … ],
    "data_mode": "real", "is_estimated": true, "is_synthetic": false, "production_ready": false
  }
}
```

---

## 4. Frontend

`frontend/components/SubstationWorkflowPanel.tsx` (self-contained client component):

1. Loads the catalog on mount → populates the **dropdown** (`display_label`).
2. Inputs: plant capacity (MW), scheduled generation (MW), horizon (hours), live-weather toggle.
3. **Run Agent Workflow** → `POST /orchestrate/substation` → renders the substation context
   card (status chips + `missing_fields`), the agent trace, the generation summary + timeline
   (each row shows the `substation_id`), the DSM forecast (blocked calculations + "NO RUPEE
   CHARGE" chip), and the honest limitations.

Wired into `app/locations/page.tsx` and `app/dsm/page.tsx`. No redesign — it reuses the
existing `glass-card` / `input-field` / `btn-primary` styles.

---

## 5. Honesty guarantees (enforced + tested)

- `capacity_mva` and `district` are **always `null`** (unavailable in OSM) — never fabricated.
- PV generation is **ESTIMATED** from irradiance + user capacity, never measured.
- DSM is **framework-only**: no rupee charge (`emits_rupee_values = false`); the ±15% band is a
  modelling parameter, not an official KERC/CERC value.
- In `APP_DATA_MODE=real` there is **no synthetic fallback** (`is_synthetic = false`); weather
  degrades to real clear-sky physics, not invented data.
- Every response carries `data_sources`, `limitations`, provenance labels, and the agent/calculation trace.

Verified by `backend/tests/test_substation_workflow.py` (15 tests).
