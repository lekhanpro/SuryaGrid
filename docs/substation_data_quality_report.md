# Bengaluru / Karnataka Substation Data Quality Report

Generated: 2026-07-06
Source: OpenStreetMap via Overpass API (ODbL 1.0, © OpenStreetMap contributors)
Search: 45.0 km radius around Bengaluru (Bangalore) (12.9716, 77.5946)

## Coverage

- Total substations (power=substation): **344**
- With voltage tag (kV): 141 (41.0%)
- With operator: 147
- With district: 0
- With capacity (MVA): 0 (0.0%)

## Honesty notes

- **Capacity (MVA) is almost never present in OSM** and is therefore kept `null`. The pipeline does NOT invent capacity or voltage. Any substation-level DSM/capacity optimisation is disabled until an official KPTCL/BESCOM capacity source is connected.
- Coordinates are used exactly as published by OSM contributors; none are fabricated.
- `reliability_score` starts at the OSM base confidence (0.6) and is reduced by 0.1 for each missing key field (voltage, capacity, operator, district).
- Grid features in `bengaluru_grid_features.parquet` are **geometry-only** (distances, neighbour density) derived from real coordinates -> `ESTIMATED_FROM_REAL`.

## Files

- `backend/data/ml/bengaluru_substations_cleaned.parquet` (344 rows)
- `backend/data/ml/bengaluru_grid_features.parquet` (344 rows)

## Missing / needed official sources

- KPTCL/BESCOM substation capacity (MVA) and transformer ratings -> `NEEDS_OFFICIAL_SOURCE`.
- Feeder-level load per substation -> `NEEDS_OFFICIAL_SOURCE` (KPTCL-SLDC).
