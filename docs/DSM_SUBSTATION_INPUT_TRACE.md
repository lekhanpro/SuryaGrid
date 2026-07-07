# DSM Substation Input Trace

How a selected substation's context feeds the DSM step of the
[substation-driven workflow](SUBSTATION_DRIVEN_AGENT_WORKFLOW.md), and — just as important —
which DSM calculations are **blocked** because the real input does not exist. Nothing is
fabricated and no rupee value is ever emitted.

Implementation: `SubstationOrchestrator._build_dsm_forecast()`
(`backend/app/agents/substation_orchestrator.py`) + `agent_models.predict_dsm()`
(`backend/app/ml/agent_models.py`). See also [DSM_RULE_SOURCES.md](DSM_RULE_SOURCES.md).

---

## Inputs the DSM step receives

| Input | From | Used for | If missing |
|-------|------|----------|------------|
| `substation_id`, `latitude`, `longitude` | `SubstationContext` | Echoed in `context_inputs_used`; coordinates drove the weather/irradiance | always present |
| `voltage_kv` | `SubstationContext` | `voltage_status`; gates voltage-band optimisation | `voltage_band_optimisation` **blocked** |
| `capacity_mva` | `SubstationContext` (**null in OSM**) | would give substation loading | `substation_loading_percent = null`, **blocked** |
| `source_label` | `SubstationContext` | provenance on the DSM result | — |
| `estimated_energy_mwh` | Generation timeline | deviation vs. schedule | generation not estimated without `site_capacity_mw` |
| `scheduled_generation_mw` | request | deviation + scheduled-irradiance back-estimate | breach risk = `NOT_AVAILABLE` |
| `site_capacity_mw` | request | back-estimate scheduled irradiance | breach risk = `NOT_AVAILABLE` |
| forecast weather @ peak hour | Weather agent | ML DSM features | — |

The DSM result includes `context_inputs_used` so you can see exactly which substation fields
were passed in.

---

## What is computed (honestly)

### 1. Deviation-breach risk (ML)
`agent_models.predict_dsm()` runs **only** when both `scheduled_generation_mw` and
`site_capacity_mw` are provided, because it needs a *scheduled irradiance*, which is
back-estimated:

```
scheduled_ghi_estimate_wm2 = scheduled_generation_mw / (site_capacity_mw × performance_ratio(0.80)) × 1000
```

The model returns a breach probability. It emits **no rupee value** (`emits_rupee_values = false`).
Without a schedule, `breach_risk = {status: NOT_AVAILABLE, reason: "…"}`.

### 2. Framework deviation (energy basis)
```
deviation_percent = (estimated_energy_mwh − scheduled_energy_mwh) / scheduled_energy_mwh × 100
scheduled_energy_mwh = scheduled_generation_mw × horizon_hours    # constant-MW assumption
deviation_band = WITHIN_MODELLING_BAND(±15%) | EXCEEDS_MODELLING_BAND(±15%)
```

> The ±15% band is a **modelling parameter**, *not* an official KERC/CERC value.

---

## What is blocked (and why)

`dsm_forecast.blocked_calculations[]` lists each blocked calculation with a `reason` and what
it `needs`:

| Blocked calculation | Reason | Needs |
|---------------------|--------|-------|
| `substation_loading_percent` | `capacity_mva` unavailable in OSM (and no real load telemetry) | official KPTCL/BESCOM substation capacity (MVA) + BESCOM feeder/substation load (MW) |
| `voltage_band_optimisation` *(only if `voltage_kv` is null)* | voltage level unavailable for this substation | official substation voltage level (kV) |
| `load_following_optimisation` | no substation-level real-time load/demand feed | BESCOM feeder/substation load time-series |
| `dsm_rupee_charge` | no official KERC/CERC rupee DSM tariff is parsed | official KERC/CERC DSM tariff order (rupee slabs) |

Corresponding status flags on the DSM result: `capacity_status = NOT_AVAILABLE`,
`load_data_status = NOT_AVAILABLE`, `tariff_status = NEEDS_OFFICIAL_SOURCE`,
`substation_loading_percent = null`, `emits_rupee_values = false`.

---

## Why no rupees

The platform has **no parsed official KERC/CERC rupee DSM tariff order**. Emitting a rupee
figure would be fabrication. Instead the DSM step returns deviation %, a modelling band, a
breach-risk probability, and a `framework_recommendation` — all labelled `NEEDS_OFFICIAL_SOURCE`.
Connect an official tariff order to unlock rupee charges.

---

## Worked example

Substation `OSM-1299917513` (220 kV, `capacity_mva = null`), `site_capacity_mw = 50`,
`scheduled_generation_mw = 20`, 12 h horizon:

- `scheduled_ghi_estimate_wm2 = 20 / (50 × 0.80) × 1000 = 500`
- `estimated_energy_mwh ≈ 259.7`, `scheduled_energy_mwh = 20 × 12 = 240`
- `deviation_percent ≈ 8.19` → `WITHIN_MODELLING_BAND(±15%)`
- `capacity_status = NOT_AVAILABLE`, `substation_loading_percent = null`
- `blocked_calculations = [substation_loading_percent, load_following_optimisation, dsm_rupee_charge]`
- `emits_rupee_values = false`

Verified by `backend/tests/test_substation_workflow.py`
(`test_dsm_receives_substation_context`, `test_dsm_blocks_capacity_load_and_tariff_and_no_rupees`).
