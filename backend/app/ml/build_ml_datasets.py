"""Phase 1.7 - Build ML-ready datasets from the closest REAL Bengaluru/Karnataka/
India data sources. Honest by construction:

  * Weather/solar history  -> Open-Meteo archive + NASA POWER at Bengaluru lat/lon
                              (REAL_COORDINATE_BASED).
  * Substations/grid       -> OpenStreetMap / Overpass (REAL_LOCAL/REAL_KARNATAKA);
                              capacity/voltage never invented.
  * Load history           -> best-effort real India/Karnataka data (Kaggle/public);
                              NOT_AVAILABLE if nothing valid is found.
  * Derived training sets  -> solar (irradiance forecast), cloud (irradiance-drop
                              risk), dsm (deviation-band framework) - all from the
                              real Bengaluru history above.

HARD RULE: in --data-mode real, nothing falls back to synthetic. If a real source
yields no usable data, the corresponding file is NOT written and the status is
recorded as NOT_AVAILABLE.

Usage:
    python -m app.ml.build_ml_datasets --region bengaluru --data-mode real
    python -m app.ml.build_ml_datasets --region bengaluru --data-mode real \
        --start-year 2022 --end-year 2024
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, date, datetime

import httpx
import numpy as np
import pandas as pd

from app.ml import provenance as prov
from app.ml.provenance import (
    NOT_AVAILABLE,
    REAL_BENGALURU,
    REAL_COORDINATE_BASED,
    REAL_INDIA,
    REAL_KARNATAKA,
    Region,
    get_region,
)
from app.utils.geo import haversine_km

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_HOURLY = "https://power.larc.nasa.gov/api/temporal/hourly/point"
NASA_POWER_DAILY = "https://power.larc.nasa.gov/api/temporal/daily/point"

ARCHIVE_HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "shortwave_radiation",  # GHI
    "direct_radiation",
    "direct_normal_irradiance",  # DNI
    "diffuse_radiation",  # DHI
    "wind_speed_10m",
    "surface_pressure",
    "precipitation",
    "weather_code",
]

BENGALURU_ALTITUDE_M = 920.0  # Bengaluru mean elevation (~900-920 m); used for pvlib clear-sky.

# Substation search radius around the city centre (metro coverage).
SUBSTATION_RADIUS_KM = 45.0

# Minimum real rows required before we treat a source as trainable.
MIN_WEATHER_ROWS = 2000
MIN_LOAD_ROWS = 1000

# Cloud/irradiance-drop labelling (documented in docs/formulas.md).
CLEARSKY_DAYLIGHT_MIN_WM2 = 50.0  # only label hours with meaningful clear-sky GHI
CLEARNESS_DROP_THRESHOLD = 0.5  # kt < 0.5 => significant irradiance drop (cloudy)

# DSM deviation band (KERC/CERC framework structure; NOT an official rupee penalty).
DSM_DEVIATION_BAND_PERCENT = 15.0

# File names (Phase 1.7 canonical outputs)
F_WEATHER = "bengaluru_weather_solar_history.parquet"
F_SUBSTATIONS = "bengaluru_substations_cleaned.parquet"
F_GRID = "bengaluru_grid_features.parquet"
F_SOLAR = "solar_agent_training.parquet"
F_CLOUD = "cloud_agent_training.parquet"
F_DSM = "dsm_agent_training.parquet"
F_LOAD_HISTORY = "karnataka_or_india_load_history.parquet"
F_LOAD_TRAIN = "load_agent_training.parquet"
F_RL_ENV = "rl_environment_dataset.parquet"


def _log(msg: str) -> None:
    print(f"[build_ml_datasets] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# 1. Bengaluru weather/solar history (Open-Meteo archive + NASA POWER)
# --------------------------------------------------------------------------- #
def _fetch_openmeteo_year(region: Region, start: str, end: str) -> pd.DataFrame:
    params = {
        "latitude": region.latitude,
        "longitude": region.longitude,
        "timezone": region.timezone,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(ARCHIVE_HOURLY_FIELDS),
    }
    with httpx.Client(timeout=90.0) as client:
        resp = client.get(OPEN_METEO_ARCHIVE, params=params)
        resp.raise_for_status()
        payload = resp.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        return pd.DataFrame()

    def col(key: str) -> list:
        return hourly.get(key) or [None] * len(times)

    df = pd.DataFrame(
        {
            "timestamp_local": times,
            "temperature_c": col("temperature_2m"),
            "relative_humidity_percent": col("relative_humidity_2m"),
            "cloud_cover_percent": col("cloud_cover"),
            "shortwave_radiation_wm2": col("shortwave_radiation"),
            "direct_radiation_wm2": col("direct_radiation"),
            "direct_normal_irradiance_wm2": col("direct_normal_irradiance"),
            "diffuse_radiation_wm2": col("diffuse_radiation"),
            "wind_speed_mps": col("wind_speed_10m"),
            "surface_pressure_hpa": col("surface_pressure"),
            "precipitation_mm": col("precipitation"),
            "weather_code": col("weather_code"),
        }
    )
    return df


def _fetch_nasa_power_daily_ghi(region: Region, start_year: int, end_year: int) -> pd.DataFrame:
    """NASA POWER daily all-sky GHI (kWh/m2/day) for cross-validation. REAL_COORDINATE_BASED."""
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "latitude": region.latitude,
        "longitude": region.longitude,
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "format": "JSON",
    }
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(NASA_POWER_DAILY, params=params)
            resp.raise_for_status()
            payload = resp.json()
        series = payload["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        rows = [
            {"date": datetime.strptime(k, "%Y%m%d").date().isoformat(), "nasa_ghi_kwh_m2_day": v}
            for k, v in series.items()
            if v is not None and v >= 0  # NASA uses -999 for fill
        ]
        return pd.DataFrame(rows)
    except Exception as exc:  # noqa: BLE001 - cross-check is best-effort, never fatal
        _log(f"NASA POWER daily fetch failed (non-fatal cross-check): {exc}")
        return pd.DataFrame()


def build_weather_solar_history(
    region: Region, start_year: int, end_year: int, data_mode: str
) -> dict:
    _log(f"Fetching Open-Meteo archive {start_year}-01-01..{end_year}-12-31 for {region.display_name}")
    frames: list[pd.DataFrame] = []
    today = date.today()
    for yr in range(start_year, end_year + 1):
        start = f"{yr}-01-01"
        end = f"{yr}-12-31"
        # Do not request beyond the archive's available window.
        if date.fromisoformat(end) >= today:
            end = (today.replace(day=1)).isoformat()  # safe past date (start of current month)
        try:
            part = _fetch_openmeteo_year(region, start, end)
            _log(f"  {yr}: {len(part)} hourly rows")
            if not part.empty:
                frames.append(part)
        except Exception as exc:  # noqa: BLE001
            _log(f"  {yr}: fetch failed: {exc}")

    if not frames:
        if data_mode == prov.DATA_MODE_REAL:
            raise prov.SyntheticFallbackError(
                "Open-Meteo archive returned no data and real mode forbids synthetic fallback."
            )
        return {"status": NOT_AVAILABLE, "rows": 0, "file": None}

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["timestamp_local"]).reset_index(drop=True)

    # Types + time features (local IST hour drives the solar cycle).
    ts = pd.to_datetime(df["timestamp_local"], errors="coerce")
    df = df[ts.notna()].copy()
    ts = pd.to_datetime(df["timestamp_local"])
    df["timestamp_local"] = ts.dt.strftime("%Y-%m-%dT%H:%M:%S")
    df["date"] = ts.dt.date.astype(str)
    df["year"] = ts.dt.year
    df["month"] = ts.dt.month
    df["day_of_year"] = ts.dt.dayofyear
    df["hour_of_day"] = ts.dt.hour
    for c in [
        "temperature_c",
        "relative_humidity_percent",
        "cloud_cover_percent",
        "shortwave_radiation_wm2",
        "direct_radiation_wm2",
        "direct_normal_irradiance_wm2",
        "diffuse_radiation_wm2",
        "wind_speed_mps",
        "surface_pressure_hpa",
        "precipitation_mm",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["weather_code"] = pd.to_numeric(df["weather_code"], errors="coerce").astype("Int64")

    df["latitude"] = region.latitude
    df["longitude"] = region.longitude
    df["source"] = REAL_COORDINATE_BASED
    df["source_provider"] = "open-meteo-archive"
    df["source_url"] = OPEN_METEO_ARCHIVE

    # pvlib clear-sky GHI (Ineichen) -> clearness index kt (physically grounded).
    df = _add_clearsky(df, region)

    # NASA POWER daily GHI cross-check merged by date (second real source).
    nasa = _fetch_nasa_power_daily_ghi(region, start_year, end_year)
    nasa_agreement = None
    if not nasa.empty:
        df = df.merge(nasa, on="date", how="left")
        # daily Open-Meteo GHI energy (kWh/m2) vs NASA daily for agreement metric
        om_daily = (
            df.groupby("date")["shortwave_radiation_wm2"].sum() / 1000.0
        ).rename("om_ghi_kwh_m2_day")
        cmp = pd.concat([om_daily, nasa.set_index("date")["nasa_ghi_kwh_m2_day"]], axis=1).dropna()
        if len(cmp) > 10:
            nasa_agreement = {
                "days_compared": int(len(cmp)),
                "pearson_r": round(float(cmp.corr().iloc[0, 1]), 4),
                "mean_open_meteo_kwh_m2_day": round(float(cmp["om_ghi_kwh_m2_day"].mean()), 3),
                "mean_nasa_kwh_m2_day": round(float(cmp["nasa_ghi_kwh_m2_day"].mean()), 3),
            }
    else:
        df["nasa_ghi_kwh_m2_day"] = np.nan

    # Per-dataset + per-row source metadata (Phase 1.7 honesty requirement).
    ingestion_time = datetime.now(UTC).isoformat()
    df["source_name"] = "Open-Meteo Historical Weather Archive (+ NASA POWER cross-check)"
    df["data_geography"] = f"{region.display_name}, {region.state}, {region.country}"
    df["ingestion_time"] = ingestion_time
    df["quality_score"] = _weather_quality_score(df)

    if len(df) < MIN_WEATHER_ROWS and data_mode == prov.DATA_MODE_REAL:
        _log(f"WARNING: only {len(df)} rows (< {MIN_WEATHER_ROWS}); downstream training may skip.")

    path = prov.write_parquet(df, F_WEATHER)
    _log(f"Wrote {F_WEATHER}: {len(df)} rows -> {path}")
    return {
        "status": "OK",
        "rows": int(len(df)),
        "file": str(path),
        "source_label": REAL_COORDINATE_BASED,
        "columns": list(df.columns),
        "date_range": [df["date"].min(), df["date"].max()],
        "nasa_power_cross_check": nasa_agreement,
        "peak_ghi_wm2": round(float(df["shortwave_radiation_wm2"].max()), 1),
    }


def _weather_quality_score(df: pd.DataFrame) -> pd.Series:
    """Honest per-row data-quality score in [0,1].

    Fraction of non-null key fields, zeroed for physically-impossible irradiance and
    halved when measured GHI exceeds clear-sky by an implausible margin.
    """
    key = [
        "temperature_c",
        "relative_humidity_percent",
        "cloud_cover_percent",
        "shortwave_radiation_wm2",
        "wind_speed_mps",
        "surface_pressure_hpa",
    ]
    present = [c for c in key if c in df.columns]
    score = df[present].notna().mean(axis=1)
    ghi = pd.to_numeric(df.get("shortwave_radiation_wm2"), errors="coerce")
    impossible = (ghi < 0) | (ghi > 1500)
    score = score.mask(impossible.fillna(False), 0.0)
    if "clearsky_ghi_wm2" in df.columns:
        over = ghi > (pd.to_numeric(df["clearsky_ghi_wm2"], errors="coerce") * 1.3 + 20)
        score = score.where(~over.fillna(False), score * 0.5)
    return score.round(3)


def _add_clearsky(df: pd.DataFrame, region: Region) -> pd.DataFrame:
    """Add clearsky_ghi_wm2 and clearness_index (kt) using pvlib Ineichen."""
    try:
        import pvlib

        loc = pvlib.location.Location(
            region.latitude, region.longitude, tz=region.timezone, altitude=BENGALURU_ALTITUDE_M
        )
        idx = pd.DatetimeIndex(pd.to_datetime(df["timestamp_local"])).tz_localize(
            region.timezone, nonexistent="shift_forward", ambiguous="NaT"
        )
        cs = loc.get_clearsky(idx, model="ineichen")
        df["clearsky_ghi_wm2"] = cs["ghi"].to_numpy()
    except Exception as exc:  # noqa: BLE001
        _log(f"pvlib clear-sky computation failed (non-fatal): {exc}")
        df["clearsky_ghi_wm2"] = np.nan

    with np.errstate(divide="ignore", invalid="ignore"):
        kt = df["shortwave_radiation_wm2"] / df["clearsky_ghi_wm2"]
    kt = kt.where(df["clearsky_ghi_wm2"] > CLEARSKY_DAYLIGHT_MIN_WM2, other=np.nan)
    df["clearness_index"] = kt.clip(lower=0.0, upper=1.2)
    df["is_daylight"] = (df["clearsky_ghi_wm2"] > CLEARSKY_DAYLIGHT_MIN_WM2).astype(int)
    return df


# --------------------------------------------------------------------------- #
# 2. Substations / grid features (OpenStreetMap via Overpass)
# --------------------------------------------------------------------------- #
def _parse_voltage_kv(raw) -> float | None:
    """Parse an OSM 'voltage' tag (volts, possibly ';'-separated) to max kV. Null if unknown."""
    if not raw:
        return None
    best = None
    for token in str(raw).replace(",", ";").split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            volts = float(token)
        except ValueError:
            continue
        kv = volts / 1000.0 if volts > 1000 else volts  # some tags already in kV
        best = kv if best is None else max(best, kv)
    return round(best, 2) if best is not None else None


def build_substations(region: Region, data_mode: str) -> dict:
    from app.data_sources.substation_provider import (
        OSM_SOURCE_NAME,
        OSM_SOURCE_URL,
        SubstationProvider,
    )

    _log(f"Fetching OSM substations within {SUBSTATION_RADIUS_KM} km of {region.display_name}")
    provider = SubstationProvider()
    try:
        raw = asyncio.run(
            provider.fetch_around(region.latitude, region.longitude, SUBSTATION_RADIUS_KM)
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"Overpass fetch failed: {exc}")
        if data_mode == prov.DATA_MODE_REAL:
            return {"status": NOT_AVAILABLE, "rows": 0, "file": None, "error": str(exc)}
        raw = []

    if not raw:
        return {"status": NOT_AVAILABLE, "rows": 0, "file": None}

    ingestion_time = datetime.now(UTC).isoformat()
    rows = []
    for i, r in enumerate(raw):
        voltage_kv = _parse_voltage_kv(r.get("voltage_level"))
        district = r.get("district")
        # capacity is essentially never present in OSM -> keep null, never invent.
        capacity_mva = None
        in_blr = _within_bengaluru(region, r)
        missing = [
            f
            for f, v in {
                "voltage_kv": voltage_kv,
                "capacity_mva": capacity_mva,
                "operator": r.get("operator"),
                "district": district,
            }.items()
            if v in (None, "")
        ]
        # reliability: OSM base confidence, minus penalty per missing key field.
        reliability = round(max(0.1, 0.6 - 0.1 * len(missing)), 2)
        rows.append(
            {
                "substation_id": f"OSM-{r.get('osm_id', i)}",
                "name": r.get("name"),
                "latitude": r.get("latitude"),
                "longitude": r.get("longitude"),
                "operator": r.get("operator"),
                "voltage_kv": voltage_kv,
                "capacity_mva": capacity_mva,
                "district": district,
                "state": r.get("state") or region.state,
                "source": OSM_SOURCE_NAME,
                "source_url": OSM_SOURCE_URL,
                "source_label": REAL_BENGALURU if in_blr else REAL_KARNATAKA,
                "data_geography": (
                    f"Bengaluru, {region.state}, {region.country}"
                    if in_blr
                    else f"{region.state}, {region.country}"
                ),
                "ingestion_time": ingestion_time,
                "reliability_score": reliability,
                "missing_fields": ",".join(missing) if missing else "",
            }
        )
    sub = pd.DataFrame(rows)
    sub_path = prov.write_parquet(sub, F_SUBSTATIONS)
    _log(f"Wrote {F_SUBSTATIONS}: {len(sub)} substations -> {sub_path}")

    grid = _build_grid_features(sub, region)
    grid_path = prov.write_parquet(grid, F_GRID)
    _log(f"Wrote {F_GRID}: {len(grid)} rows -> {grid_path}")

    quality = _substation_quality(sub)
    _write_substation_quality_report(sub, grid, region, quality)

    return {
        "status": "OK",
        "rows": int(len(sub)),
        "file": str(sub_path),
        "grid_file": str(grid_path),
        "source_label": f"{REAL_BENGALURU}/{REAL_KARNATAKA}",
        "quality": quality,
    }


def _within_bengaluru(region: Region, rec: dict) -> bool:
    try:
        return haversine_km(region.latitude, region.longitude, rec["latitude"], rec["longitude"]) <= 25.0
    except Exception:  # noqa: BLE001
        return False


def _build_grid_features(sub: pd.DataFrame, region: Region) -> pd.DataFrame:
    """Geometric grid features derived from REAL coordinates (ESTIMATED_FROM_REAL).

    No capacity/voltage is invented; features are purely spatial.
    """
    lats = sub["latitude"].to_numpy(dtype=float)
    lons = sub["longitude"].to_numpy(dtype=float)
    feats = []
    for i in range(len(sub)):
        dists = np.array(
            [
                haversine_km(lats[i], lons[i], lats[j], lons[j])
                for j in range(len(sub))
                if j != i
            ]
        )
        nearest = float(dists.min()) if dists.size else None
        density_5km = int((dists <= 5.0).sum()) if dists.size else 0
        density_10km = int((dists <= 10.0).sum()) if dists.size else 0
        feats.append(
            {
                "substation_id": sub.iloc[i]["substation_id"],
                "latitude": lats[i],
                "longitude": lons[i],
                "distance_to_city_center_km": round(
                    haversine_km(region.latitude, region.longitude, lats[i], lons[i]), 3
                ),
                "nearest_substation_km": round(nearest, 3) if nearest is not None else None,
                "substation_density_5km": density_5km,
                "substation_density_10km": density_10km,
                "voltage_kv": sub.iloc[i]["voltage_kv"],  # real where known, else null
                "source_label": prov.ESTIMATED_FROM_REAL,
                "feature_basis": "geometry_from_real_osm_coordinates",
            }
        )
    return pd.DataFrame(feats)


def _substation_quality(sub: pd.DataFrame) -> dict:
    n = len(sub)
    return {
        "total_substations": int(n),
        "with_voltage_kv": int(sub["voltage_kv"].notna().sum()),
        "with_operator": int(sub["operator"].notna().sum()),
        "with_district": int(sub["district"].notna().sum()),
        "with_capacity_mva": int(sub["capacity_mva"].notna().sum()),
        "pct_voltage_known": round(100.0 * sub["voltage_kv"].notna().mean(), 1) if n else 0.0,
        "pct_capacity_known": round(100.0 * sub["capacity_mva"].notna().mean(), 1) if n else 0.0,
    }


def _write_substation_quality_report(
    sub: pd.DataFrame, grid: pd.DataFrame, region: Region, q: dict
) -> None:
    path = prov.docs_dir() / "substation_data_quality_report.md"
    lines = [
        "# Bengaluru / Karnataka Substation Data Quality Report",
        "",
        f"Generated: {datetime.now(UTC).date().isoformat()}",
        "Source: OpenStreetMap via Overpass API (ODbL 1.0, \u00a9 OpenStreetMap contributors)",
        f"Search: {SUBSTATION_RADIUS_KM} km radius around {region.display_name} "
        f"({region.latitude}, {region.longitude})",
        "",
        "## Coverage",
        "",
        f"- Total substations (power=substation): **{q['total_substations']}**",
        f"- With voltage tag (kV): {q['with_voltage_kv']} ({q['pct_voltage_known']}%)",
        f"- With operator: {q['with_operator']}",
        f"- With district: {q['with_district']}",
        f"- With capacity (MVA): {q['with_capacity_mva']} ({q['pct_capacity_known']}%)",
        "",
        "## Honesty notes",
        "",
        "- **Capacity (MVA) is almost never present in OSM** and is therefore kept `null`. "
        "The pipeline does NOT invent capacity or voltage. Any substation-level DSM/capacity "
        "optimisation is disabled until an official KPTCL/BESCOM capacity source is connected.",
        "- Coordinates are used exactly as published by OSM contributors; none are fabricated.",
        "- `reliability_score` starts at the OSM base confidence (0.6) and is reduced by 0.1 for "
        "each missing key field (voltage, capacity, operator, district).",
        "- Grid features in `bengaluru_grid_features.parquet` are **geometry-only** "
        "(distances, neighbour density) derived from real coordinates -> `ESTIMATED_FROM_REAL`.",
        "",
        "## Files",
        "",
        f"- `backend/data/ml/{F_SUBSTATIONS}` ({len(sub)} rows)",
        f"- `backend/data/ml/{F_GRID}` ({len(grid)} rows)",
        "",
        "## Missing / needed official sources",
        "",
        "- KPTCL/BESCOM substation capacity (MVA) and transformer ratings -> `NEEDS_OFFICIAL_SOURCE`.",
        "- Feeder-level load per substation -> `NEEDS_OFFICIAL_SOURCE` (KPTCL-SLDC).",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _log("Wrote docs/substation_data_quality_report.md")


# --------------------------------------------------------------------------- #
# 3. Load history (best-effort real India/Karnataka; honest NOT_AVAILABLE)
# --------------------------------------------------------------------------- #
_KAGGLE_LOAD_CANDIDATES = [
    "smarthkaushal/energy-demand-profile",  # National-Level Electricity Load Curve (India)
]


def _kaggle_download(dataset: str, dest) -> bool:
    dest.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", dataset, "-p", str(dest), "--unzip"],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        _log(f"Kaggle download failed for {dataset}: {exc}")
        return False


def _detect_load_frame(csv_path) -> pd.DataFrame | None:
    """Read a CSV and detect a (timestamp, load) pair. Returns normalized frame or None.

    Honesty guard: timestamps whose parsed year is implausible (< 2000) are rejected
    rather than persisted. A separate `Year` column is combined with a year-less date
    column (e.g. the India national load curve uses Year + "01-Jan 12am").
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception:  # noqa: BLE001
        return None
    if df.empty:
        return None
    cols = {c.lower(): c for c in df.columns}

    dt_col = next((cols[k] for k in ("datetime", "timestamp", "date", "time", "date_time") if k in cols), None)
    year_col = cols.get("year")
    load_col = None
    for key in ("demand", "load", "mw", "power", "usage", "consumption", "value"):
        load_col = next((orig for lc, orig in cols.items() if key in lc), None)
        if load_col:
            break
    if dt_col is None or load_col is None:
        return None

    val = pd.to_numeric(df[load_col], errors="coerce")

    # Build timestamps. Prefer combining an explicit Year column with a year-less date.
    ts = None
    if year_col is not None:
        combo = df[dt_col].astype(str).str.strip() + " " + df[year_col].astype(str)
        for fmt in ("%d-%b %I%p %Y", "%d-%b %Y %I%p", "%d-%b-%Y %I%p"):
            cand = pd.to_datetime(combo, format=fmt, errors="coerce")
            if cand.notna().mean() > 0.9:
                ts = cand
                break
    if ts is None:
        ts = pd.to_datetime(df[dt_col], errors="coerce")

    out = pd.DataFrame({"timestamp": ts, "load_value": val}).dropna()
    # Reject implausible years (guards against year-0001 / 1900 default parses).
    out = out[out["timestamp"].dt.year >= 2000]
    out = out.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    if len(out) < MIN_LOAD_ROWS:
        return None
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    out["source_column"] = load_col
    return out.reset_index(drop=True)


def build_load_history(region: Region, data_mode: str, attempt_kaggle: bool) -> dict:
    if not attempt_kaggle:
        return {"status": NOT_AVAILABLE, "rows": 0, "file": None, "reason": "kaggle attempt disabled"}

    raw_root = prov.raw_data_dir() / "load"
    for dataset in _KAGGLE_LOAD_CANDIDATES:
        dest = raw_root / dataset.split("/")[-1]
        _log(f"Attempting real load dataset from Kaggle: {dataset}")
        if not _kaggle_download(dataset, dest):
            continue
        for csv_path in sorted(dest.rglob("*.csv")):
            frame = _detect_load_frame(csv_path)
            if frame is not None:
                frame["load_mw"] = frame["load_value"]
                frame["geography"] = "India (national)"
                frame["region_scope"] = "India (national)"
                frame["source_label"] = REAL_INDIA
                frame["source_name"] = "National-Level Electricity Load Curve Data (India) - Kaggle"
                frame["source_dataset"] = dataset
                frame["source_url"] = f"https://www.kaggle.com/datasets/{dataset}"
                frame["data_granularity"] = "hourly"
                frame["ingestion_time"] = datetime.now(UTC).isoformat()
                frame["quality_score"] = (frame["load_value"] > 0).astype(float).round(3)
                path = prov.write_parquet(frame, F_LOAD_HISTORY)
                _log(f"Wrote {F_LOAD_HISTORY}: {len(frame)} rows from {csv_path.name}")
                return {
                    "status": "OK",
                    "rows": int(len(frame)),
                    "file": str(path),
                    "source_label": REAL_INDIA,
                    "dataset": dataset,
                    "geography": "India (national) - NOT Bengaluru-specific",
                }
    return {
        "status": NOT_AVAILABLE,
        "rows": 0,
        "file": None,
        "reason": "No Kaggle/public dataset yielded >= "
        f"{MIN_LOAD_ROWS} valid timestamped load rows with a detectable schema.",
    }


# --------------------------------------------------------------------------- #
# 4. Derived training datasets (all from the REAL Bengaluru history)
# --------------------------------------------------------------------------- #
def _cyclical(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hour_sin"] = np.sin(2 * np.pi * df["hour_of_day"] / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour_of_day"] / 24.0)
    df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365.25)
    return df


def build_solar_training(weather: pd.DataFrame) -> dict:
    """Irradiance forecast training set. Target = shortwave_radiation_wm2 (GHI). NOT PV output."""
    df = _cyclical(weather)
    feature_cols = [
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
        "month",
        "cloud_cover_percent",
        "temperature_c",
        "relative_humidity_percent",
        "wind_speed_mps",
        "surface_pressure_hpa",
        "precipitation_mm",
        "clearsky_ghi_wm2",
    ]
    keep = [*feature_cols, "shortwave_radiation_wm2", "timestamp_local", "date"]
    out = df[keep].dropna(subset=["shortwave_radiation_wm2"]).reset_index(drop=True)
    out["target_ghi_wm2"] = out["shortwave_radiation_wm2"]
    out["prediction_type"] = "irradiance_forecast"
    out["source_label"] = REAL_COORDINATE_BASED
    path = prov.write_parquet(out, F_SOLAR)
    _log(f"Wrote {F_SOLAR}: {len(out)} rows, {len(feature_cols)} features")
    return {
        "status": "OK",
        "rows": int(len(out)),
        "file": str(path),
        "features": feature_cols,
        "target": "target_ghi_wm2",
        "prediction_type": "irradiance_forecast",
    }


def build_cloud_training(weather: pd.DataFrame) -> dict:
    """Irradiance-drop-risk classification. Label from clearness index kt in daylight hours."""
    df = _cyclical(weather)
    day = df[df["is_daylight"] == 1].copy()
    day = day.dropna(subset=["clearness_index"])
    day["irradiance_drop_risk"] = (day["clearness_index"] < CLEARNESS_DROP_THRESHOLD).astype(int)
    feature_cols = [
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
        "cloud_cover_percent",
        "relative_humidity_percent",
        "temperature_c",
        "wind_speed_mps",
        "surface_pressure_hpa",
        "precipitation_mm",
    ]
    keep = [*feature_cols, "irradiance_drop_risk", "clearness_index", "timestamp_local", "date"]
    out = day[keep].reset_index(drop=True)
    out["prediction_type"] = "irradiance_drop_risk"
    out["source_label"] = REAL_COORDINATE_BASED
    path = prov.write_parquet(out, F_CLOUD)
    pos = int(out["irradiance_drop_risk"].sum())
    _log(f"Wrote {F_CLOUD}: {len(out)} daylight rows, {pos} positive (drop) labels")
    return {
        "status": "OK",
        "rows": int(len(out)),
        "file": str(path),
        "features": feature_cols,
        "target": "irradiance_drop_risk",
        "positive_rate": round(float(out["irradiance_drop_risk"].mean()), 4) if len(out) else 0.0,
        "prediction_type": "irradiance_drop_risk",
    }


def build_dsm_training(weather: pd.DataFrame) -> dict:
    """DSM deviation-band training set (framework structure, NO rupee penalty).

    A day-ahead persistence baseline (yesterday's same-hour GHI) is the 'scheduled'
    injection proxy; actual GHI is the 'realised' injection proxy. The deviation %
    is classified into KERC/CERC-style bands. This trains a breach-risk classifier;
    it does NOT compute money.
    """
    df = weather.sort_values("timestamp_local").reset_index(drop=True).copy()
    df = _cyclical(df)
    # Day-ahead persistence forecast: same hour, previous day (24 rows back on hourly data).
    df["scheduled_ghi_wm2"] = df["shortwave_radiation_wm2"].shift(24)
    df = df.dropna(subset=["scheduled_ghi_wm2", "shortwave_radiation_wm2"])
    df = df[df["is_daylight"] == 1].copy()
    denom = df["scheduled_ghi_wm2"].where(df["scheduled_ghi_wm2"].abs() > 1e-6, np.nan)
    df["deviation_percent"] = ((df["shortwave_radiation_wm2"] - df["scheduled_ghi_wm2"]) / denom) * 100.0
    df = df.dropna(subset=["deviation_percent"])

    def band(dev: float) -> str:
        if abs(dev) <= DSM_DEVIATION_BAND_PERCENT:
            return "WITHIN_BAND"
        return "OVER_INJECTION" if dev > 0 else "UNDER_INJECTION"

    df["deviation_band"] = df["deviation_percent"].apply(band)
    df["breach_risk"] = (df["deviation_band"] != "WITHIN_BAND").astype(int)
    feature_cols = [
        "hour_sin",
        "hour_cos",
        "doy_sin",
        "doy_cos",
        "cloud_cover_percent",
        "relative_humidity_percent",
        "wind_speed_mps",
        "surface_pressure_hpa",
        "precipitation_mm",
        "scheduled_ghi_wm2",
    ]
    keep = [
        *feature_cols,
        "deviation_percent",
        "deviation_band",
        "breach_risk",
        "timestamp_local",
        "date",
    ]
    out = df[keep].reset_index(drop=True)
    out["prediction_type"] = "dsm_deviation_band"
    out["source_label"] = REAL_COORDINATE_BASED
    out["band_definition_percent"] = DSM_DEVIATION_BAND_PERCENT
    path = prov.write_parquet(out, F_DSM)
    _log(f"Wrote {F_DSM}: {len(out)} rows; breach rate {out['breach_risk'].mean():.3f}")
    return {
        "status": "OK",
        "rows": int(len(out)),
        "file": str(path),
        "features": feature_cols,
        "target": "breach_risk",
        "band_percent": DSM_DEVIATION_BAND_PERCENT,
        "breach_rate": round(float(out["breach_risk"].mean()), 4) if len(out) else 0.0,
        "prediction_type": "dsm_deviation_band",
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def build_all(
    region_key: str,
    data_mode: str,
    start_year: int,
    end_year: int,
    attempt_kaggle_load: bool = True,
) -> dict:
    if data_mode not in (prov.DATA_MODE_REAL, prov.DATA_MODE_DEMO):
        raise ValueError(f"data_mode must be 'real' or 'demo', got '{data_mode}'")
    region = get_region(region_key)
    prov.ensure_dirs()
    _log(f"=== Phase 1.7 dataset build | region={region.display_name} | mode={data_mode} ===")

    report: dict = {
        "region": region.display_name,
        "coordinates": [region.latitude, region.longitude],
        "data_mode": data_mode,
        "built_at": datetime.now(UTC).isoformat(),
        "datasets": {},
    }

    # 1. Weather/solar history (foundation). In real mode a failure here is fatal.
    weather_res = build_weather_solar_history(region, start_year, end_year, data_mode)
    report["datasets"]["weather_solar_history"] = weather_res

    weather = prov.read_parquet(F_WEATHER)
    if weather is None or weather.empty:
        raise prov.SyntheticFallbackError(
            "No real weather/solar history available; refusing to synthesise in real mode."
        )

    # 2. Substations / grid
    report["datasets"]["substations"] = build_substations(region, data_mode)

    # 3. Load history (best effort; honest)
    report["datasets"]["load_history"] = build_load_history(region, data_mode, attempt_kaggle_load)

    # 4. Derived training sets from real history
    report["datasets"]["solar_agent_training"] = build_solar_training(weather)
    report["datasets"]["cloud_agent_training"] = build_cloud_training(weather)
    report["datasets"]["dsm_agent_training"] = build_dsm_training(weather)

    # 5. RL environment dataset: requires real load + official tariff -> honest skip.
    load_ok = report["datasets"]["load_history"]["status"] == "OK"
    report["datasets"]["rl_environment_dataset"] = {
        "status": NOT_AVAILABLE,
        "rows": 0,
        "file": None,
        "reason": (
            "RL environment needs real local load time series AND official tariff/DSM "
            "rupee terms. Load="
            + ("present(non-local India)" if load_ok else "absent")
            + "; official tariff rupees=absent (NEEDS_OFFICIAL_TARIFF_SOURCE). "
            "Refusing to synthesise a reward environment."
        ),
    }

    # Persist the build manifest for the training scripts + final report.
    manifest_path = prov.ml_data_dir() / "dataset_build_manifest.json"
    prov.save_json(report, manifest_path)
    _log(f"Wrote manifest -> {manifest_path}")
    return report


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Phase 1.7 real-data ML datasets.")
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    p.add_argument("--start-year", type=int, default=2022)
    p.add_argument("--end-year", type=int, default=2024)
    p.add_argument("--no-kaggle-load", action="store_true", help="Skip the Kaggle load-data attempt")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        report = build_all(
            region_key=args.region,
            data_mode=args.data_mode,
            start_year=args.start_year,
            end_year=args.end_year,
            attempt_kaggle_load=not args.no_kaggle_load,
        )
    except prov.SyntheticFallbackError as exc:
        _log(f"REAL-MODE ABORT: {exc}")
        return 2
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
