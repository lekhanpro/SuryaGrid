# SuryaGrid AI — Location & Substation Data

The platform collects and exposes **all discoverable locations**, not just main weather
stations: solar sites, weather grid points, and grid substations. Managed by
`LocationDataAgent` (`backend/app/agents/location_data_agent.py`).

See also: `SOURCE_REGISTRY.md#src-osm-substation-001`, `DATA_SOURCE_CATALOG.md`.

## Data classes

1. **Solar sites** — registered sites (DB) + a preset registry (Karnataka parks).
2. **Weather grid points** — Open-Meteo covers any coordinate globally; explicit points
   can be stored in `weather_provider_locations`.
3. **Substations** — from OpenStreetMap (Overpass) or operator CSV.
4. **Nearest-substation mapping** — haversine distance, persisted per site.

## Substation sources

| Source | Method | License | Confidence |
|--------|--------|---------|-----------|
| OpenStreetMap | Overpass `power=substation` | ODbL 1.0 (attribution required) | 0.6 (completeness varies) |
| Operator CSV | manual import | operator-owned | 1.0 |

**Coordinates are used exactly as published — never invented.** Rows without valid
coordinates are skipped. Every record stores `source_name`, `source_url`, and
`source_confidence`.

Overpass requests send a descriptive `User-Agent` and `Accept: application/json`
(required — the endpoint returns HTTP 406 otherwise).

## Tables

- `substations` — id, name, voltage_level, operator, latitude, longitude, district,
  state, country, source_name, source_url, source_confidence, osm_id, created_at, updated_at.
- `locations` — generic discoverable location (site / substation / weather_grid).
- `weather_provider_locations` — provider, label, latitude, longitude.
- `site_substation_map` — site_id, substation_id, distance_km.

## CSV import format

```
name,voltage_level,operator,latitude,longitude,district,state,country
Peenya 220kV,220000,KPTCL,13.03,77.52,Bengaluru,Karnataka,IN
```

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/locations` | Unified discoverable location list. |
| GET | `/api/v1/locations/available` | Aggregate: sites, registry, substations, weather points. |
| GET | `/api/v1/substations` | List imported substations. |
| POST | `/api/v1/substations/import` | Import from OSM (`latitude`,`longitude`,`radius_km`) **or** CSV (`csv_text`). |
| GET | `/api/v1/substations/nearest/{site_id}` | Nearest substation (haversine) + distance. |
| GET | `/api/v1/sites/{site_id}/data-coverage` | Coverage flags for a site. |

### Import examples

```bash
# From OpenStreetMap around a point (25 km):
curl -X POST http://localhost:8000/api/v1/substations/import \
  -H "Content-Type: application/json" \
  -d '{"latitude":12.97,"longitude":77.59,"radius_km":25}'

# From a CSV string:
curl -X POST http://localhost:8000/api/v1/substations/import \
  -H "Content-Type: application/json" \
  -d '{"csv_text":"name,voltage_level,operator,latitude,longitude\nX SS,220000,KPTCL,12.9,77.6\n"}'
```

## Data-coverage response

```json
{
  "weather_forecast_available": true,
  "weather_provider": "open-meteo",
  "historical_kaggle_coverage": false,
  "nearest_substation_available": true,
  "nearest_substation": {"name": "...", "distance_km": 7.0, "source": "..."},
  "dsm_rule_profile_available": true,
  "model_available": false
}
```
