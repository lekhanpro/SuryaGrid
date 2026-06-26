# System Validation Report

**System**: Suryagrid AI — Solar Irradiance Nowcasting + DSM Penalty Prediction
**Date**: 2026-06-25
**Status**: VALIDATED (real data, real physics)

---

## What changed from the prototype

- Synthetic weather generator **removed** → replaced by real **Open-Meteo** provider.
- Toy generation formula **removed** → replaced by **pvlib** physics (POA transposition,
  cell temperature, PVWatts DC/AC).
- Arbitrary "fuzzy" risk **removed** → replaced by a deterministic `RiskAgent`.
- Day-ahead schedule now derived from a **clear-sky model** (realistic commitment).
- Backward-compat `toy-data` routes removed; new `weather` route exposes raw provider data.

## Test results

```
python -m pytest tests/ -q
16 passed
```

| Suite | Focus |
|-------|-------|
| test_forecast_agent.py | pvlib nowcast: daytime power, night zero, capacity clamp, confidence |
| test_dsm_classifier.py | Deviation band, penalty cost on excess, invalid schedule |
| test_risk_agent.py | Score bounds and level mapping |
| test_orchestrator.py | Full per-interval pipeline, clear-sky default schedule |
| test_api.py | All endpoints via ASGI (offline deterministic provider) |
| test_full_system.py | End-to-end checks |

Tests use an offline `FakeProvider` (in `conftest.py`) so they never hit the network.

## Verified behaviors

| Behavior | Status |
|----------|--------|
| Real irradiance fetched from Open-Meteo | PASS |
| Generation computed by pvlib, clamped to capacity | PASS |
| Night/zero-irradiance → 0 MW | PASS |
| Deviation beyond band → PENALTY_RISK with cost on excess energy | PASS |
| Zero/negative schedule → INVALID_SCHEDULE (no divide-by-zero) | PASS |
| Risk score bounded 0–100 | PASS |
| Timeline returns time + generation + energy + DSM values | PASS |
| API envelope includes timestamp; validation errors return 422 | PASS |

## Live check (real network)

`python run_all_demo.py` against Bhadla Solar Park (27.53, 71.91), 100 MW:
real noon GHI ≈ 860 W/m², pvlib nowcast ≈ 72 MW, clear-sky schedule ≈ 79 MW,
per-hour DSM classification and cumulative penalty estimate produced.

## Known limitations

1. Site registry is in-memory (PostgreSQL models exist, not wired to routes).
2. JWT auth and per-route rate limiting scaffolded but not enforced.
3. Adaptive RL penalty/discount policy (PROJECT_PLAN.md) is the next phase.
