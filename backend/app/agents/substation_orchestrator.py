"""SubstationOrchestrator - the substation-driven multi-agent workflow.

A selected substation (``SubstationContext``) is the single context object that flows
through every agent, and each step records what it did in ``agent_trace`` while every
computed number records its formula + provenance in ``calculation_trace``::

    SubstationContext
        -> WeatherAgent          (Open-Meteo @ substation coords, or pvlib clear-sky)
        -> SolarIrradianceAgent  (solar_forecast_model.pkl -> GHI)
        -> CloudRiskAgent        (cloud_risk_classifier.pkl -> drop risk)
        -> GenerationTimelineAgent (GHI + USER plant capacity -> ESTIMATED PV, per hour)
        -> DSMAgent              (deviation-breach risk + honest, framework-only DSM)
        -> orchestrator summary

Honesty (hard rules):
  * PV generation is ESTIMATED_FROM_REAL irradiance + the USER's plant capacity - it is
    never measured, and it never uses the substation's ``capacity_mva`` (null in OSM).
  * capacity/voltage/load/tariff that are unavailable BLOCK the matching DSM calculation
    (recorded in ``blocked_calculations``) instead of being fabricated.
  * No rupee DSM charge is ever emitted (``NEEDS_OFFICIAL_SOURCE``).
  * In ``APP_DATA_MODE=real`` there is no synthetic fallback; if live weather is
    unreachable we degrade to pvlib clear-sky physics (REAL_COORDINATE_BASED), never
    to invented data.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from app.ml import agent_models
from app.ml import provenance as prov
from app.schemas.substation_context import SubstationContext

PERFORMANCE_RATIO = 0.80  # documented PV derate (matches agent_models.predict_solar)
_TZ = "Asia/Kolkata"
_ALTITUDE_M = 920.0
_HOUR_KEY = "%Y-%m-%dT%H"


def _data_mode() -> str:
    try:
        from app.config import get_settings

        return get_settings().APP_DATA_MODE
    except Exception:  # noqa: BLE001
        return prov.DATA_MODE_REAL


def _floor_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def _hourly_timestamps(start: datetime, hours: int) -> list[datetime]:
    start = _floor_hour(start)
    return [start + timedelta(hours=i) for i in range(hours)]


def _clearsky_series(lat: float, lon: float, timestamps: list[datetime]) -> list[float]:
    """pvlib Ineichen clear-sky GHI at the substation's OWN coordinates (offline, real physics)."""
    import pandas as pd
    import pvlib

    loc = pvlib.location.Location(lat, lon, tz=_TZ, altitude=_ALTITUDE_M)
    idx = pd.DatetimeIndex([t.replace(tzinfo=None) for t in timestamps]).tz_localize(
        _TZ, nonexistent="shift_forward", ambiguous="NaT"
    )
    ghi = loc.get_clearsky(idx, model="ineichen")["ghi"]
    return [round(max(0.0, float(x)), 2) for x in ghi.tolist()]


class SubstationOrchestrator:
    """Coordinates the substation-driven workflow over the trained Bengaluru agents."""

    def __init__(self, weather_provider=None):
        self._provider = weather_provider  # inject a WeatherProvider (else OpenMeteo lazily)

    # ------------------------------------------------------------------ #
    # Weather
    # ------------------------------------------------------------------ #
    async def _weather_series(
        self, context: SubstationContext, timestamps: list[datetime], use_live_weather: bool
    ) -> tuple[dict, dict]:
        """Return (per-hour-key -> weather-inputs dict, meta). Never fabricates data."""
        clearsky = _clearsky_series(context.latitude, context.longitude, timestamps)
        cs_by_key = {t.strftime(_HOUR_KEY): c for t, c in zip(timestamps, clearsky, strict=True)}

        meta = {
            "mode": "clearsky",
            "source": f"pvlib clear-sky @ ({context.latitude}, {context.longitude})",
            "source_label": prov.REAL_COORDINATE_BASED,
            "live_error": None,
        }
        live_by_key: dict[str, dict] = {}
        if use_live_weather:
            try:
                provider = self._provider or self._default_provider()
                horizon_days = max(1, math.ceil(len(timestamps) / 24) + 1)
                points = await provider.fetch_forecast(
                    latitude=context.latitude,
                    longitude=context.longitude,
                    timezone=_TZ,
                    forecast_days=min(horizon_days, 16),
                )
                for p in points:
                    live_by_key[p.timestamp.strftime(_HOUR_KEY)] = {
                        "cloud_cover_percent": p.cloud_cover_percent,
                        "temperature_c": p.temperature_c,
                        "relative_humidity_percent": p.humidity_percent,
                        "wind_speed_mps": p.wind_speed_mps,
                        "surface_pressure_hpa": p.pressure_hpa or 910.0,
                        "observed_ghi_wm2": round(float(p.ghi_w_m2), 2),
                    }
                if live_by_key:
                    meta.update(
                        mode="live",
                        source=f"Open-Meteo @ ({context.latitude}, {context.longitude})",
                        source_label=prov.REAL_COORDINATE_BASED,
                    )
            except Exception as exc:  # noqa: BLE001 - degrade to clear-sky, never synthetic
                meta["live_error"] = str(exc)

        inputs_by_key: dict[str, dict] = {}
        for t in timestamps:
            key = t.strftime(_HOUR_KEY)
            w = {
                "timestamp_local": t.replace(tzinfo=None).isoformat(),
                "clearsky_ghi_wm2": cs_by_key[key],
            }
            live = live_by_key.get(key)
            if live:
                w.update(
                    {
                        "cloud_cover_percent": live["cloud_cover_percent"],
                        "temperature_c": live["temperature_c"],
                        "relative_humidity_percent": live["relative_humidity_percent"],
                        "wind_speed_mps": live["wind_speed_mps"],
                        "surface_pressure_hpa": live["surface_pressure_hpa"],
                        "observed_ghi_wm2": live["observed_ghi_wm2"],
                    }
                )
            else:
                # clear-sky assumption: be explicit that weather was not fetched for this hour
                w["cloud_cover_percent"] = 0.0
                w["observed_ghi_wm2"] = None
            inputs_by_key[key] = w
        return inputs_by_key, meta

    @staticmethod
    def _default_provider():
        from app.providers.open_meteo import OpenMeteoProvider

        return OpenMeteoProvider()

    # ------------------------------------------------------------------ #
    # Main workflow
    # ------------------------------------------------------------------ #
    async def run(
        self,
        context: SubstationContext,
        *,
        site_capacity_mw: float | None = None,
        forecast_horizon_hours: int = 6,
        scheduled_generation_mw: float | None = None,
        use_live_weather: bool = True,
        start_time: datetime | None = None,
    ) -> dict:
        horizon = max(1, min(int(forecast_horizon_hours), 48))
        timestamps = _hourly_timestamps(start_time or datetime.now(), horizon)
        trace: list[dict] = []
        calc: dict = {}

        # 1) Substation context ------------------------------------------------
        trace.append(
            {
                "step": 1,
                "agent": "SubstationContextAgent",
                "action": "load selected substation as the workflow context object",
                "status": "ok",
                "source_label": context.source_status,
                "detail": (
                    f"{context.display_label} @ ({context.latitude}, {context.longitude}); "
                    f"missing_fields={context.missing_fields or 'none'}"
                ),
            }
        )

        # 2) Weather -----------------------------------------------------------
        weather_by_key, wmeta = await self._weather_series(context, timestamps, use_live_weather)
        trace.append(
            {
                "step": 2,
                "agent": "WeatherAgent",
                "action": "fetch weather at the substation's own coordinates",
                "status": "ok" if wmeta["mode"] == "live" else "degraded",
                "source_label": wmeta["source_label"],
                "detail": (
                    f"mode={wmeta['mode']}; source={wmeta['source']}"
                    + (f"; live_error={wmeta['live_error']}" if wmeta["live_error"] else "")
                ),
            }
        )
        calc["clearsky_ghi_wm2"] = {
            "formula": "pvlib Ineichen clear-sky GHI at substation (lat, lon)",
            "inputs": {
                "latitude": context.latitude,
                "longitude": context.longitude,
                "altitude_m": _ALTITUDE_M,
                "model": "ineichen",
            },
            "source_label": prov.REAL_COORDINATE_BASED,
        }

        # 3-5) Solar + cloud + generation timeline -----------------------------
        timeline: list[dict] = []
        solar_ok = cloud_ok = True
        for t in timestamps:
            key = t.strftime(_HOUR_KEY)
            w = weather_by_key[key]

            solar_env = agent_models.predict_solar({**w, "capacity_mw": site_capacity_mw})
            if solar_env.get("prediction_type") == "irradiance_forecast":
                forecast_ghi = solar_env.get("prediction_value")
                pv = solar_env.get("pv_estimate")
                est_gen = pv["estimated_pv_mw"] if pv else None
            else:
                solar_ok = False
                forecast_ghi = None
                est_gen = None

            cloud_env = agent_models.predict_cloud(dict(w))
            if cloud_env.get("prediction_type") == "irradiance_drop_risk":
                cloud_risk = cloud_env.get("prediction_value")
            else:
                cloud_ok = False
                cloud_risk = None

            timeline.append(
                {
                    "timestamp": w["timestamp_local"],
                    "substation_id": context.substation_id,  # every row carries the context
                    "substation_label": context.display_label,
                    "clearsky_ghi_wm2": w["clearsky_ghi_wm2"],
                    "forecast_ghi_wm2": forecast_ghi,
                    "observed_ghi_wm2": w.get("observed_ghi_wm2"),
                    "ghi_source": wmeta["source_label"],
                    "cloud_drop_risk": cloud_risk,
                    "estimated_generation_mw": est_gen,
                    "generation_type": "ESTIMATED_FROM_IRRADIANCE",
                    "actual_generation_available": False,
                    "site_capacity_mw": site_capacity_mw,
                }
            )

        trace.append(
            {
                "step": 3,
                "agent": "SolarIrradianceAgent",
                "action": "predict GHI per hour (solar_forecast_model.pkl)",
                "status": "ok" if solar_ok else "not_available",
                "source_label": prov.REAL_BENGALURU,
                "detail": f"{len(timeline)} hourly irradiance predictions",
            }
        )
        calc["forecast_ghi_wm2"] = {
            "formula": "solar_forecast_model.pkl(time-features + weather + clearsky_ghi)",
            "model_file": "backend/models/trained/solar_forecast_model.pkl",
            "source_label": prov.REAL_BENGALURU,
        }
        trace.append(
            {
                "step": 4,
                "agent": "CloudRiskAgent",
                "action": "classify irradiance-drop risk per hour (cloud_risk_classifier.pkl)",
                "status": "ok" if cloud_ok else "not_available",
                "source_label": prov.REAL_BENGALURU,
                "detail": "P(clearness kt < 0.5) per hour",
            }
        )
        calc["cloud_drop_risk"] = {
            "formula": "cloud_risk_classifier.pkl -> P(clearness index kt < 0.5)",
            "model_file": "backend/models/trained/cloud_risk_classifier.pkl",
            "source_label": prov.REAL_BENGALURU,
        }

        summary = self._generation_summary(timeline, site_capacity_mw)
        trace.append(
            {
                "step": 5,
                "agent": "GenerationTimelineAgent",
                "action": "estimate PV generation from irradiance + USER plant capacity",
                "status": "ok" if site_capacity_mw else "blocked",
                "source_label": prov.ESTIMATED_FROM_REAL,
                "detail": (
                    f"peak_estimated_mw={summary['peak_estimated_generation_mw']}, "
                    f"total_estimated_mwh={summary['total_estimated_energy_mwh']}"
                    if site_capacity_mw
                    else "site_capacity_mw not provided -> generation in MW cannot be estimated "
                    "(irradiance only)"
                ),
            }
        )
        if site_capacity_mw:
            calc["estimated_generation_mw"] = {
                "formula": "site_capacity_mw * (forecast_GHI_wm2 / 1000) * performance_ratio",
                "inputs": {
                    "site_capacity_mw": site_capacity_mw,
                    "performance_ratio": PERFORMANCE_RATIO,
                },
                "source_label": prov.ESTIMATED_FROM_REAL,
                "note": (
                    "ESTIMATED, not measured. Uses the USER-provided plant capacity, NOT the "
                    "substation capacity_mva (which is unavailable in OSM)."
                ),
            }

        # 6) DSM ---------------------------------------------------------------
        dsm = self._build_dsm_forecast(
            context=context,
            timeline=timeline,
            summary=summary,
            scheduled_generation_mw=scheduled_generation_mw,
            site_capacity_mw=site_capacity_mw,
            weather_by_key=weather_by_key,
            timestamps=timestamps,
            calc=calc,
        )
        trace.append(
            {
                "step": 6,
                "agent": "DSMAgent",
                "action": "assess deviation-breach risk + framework DSM using the substation context",
                "status": dsm["breach_risk"].get("status", "ok")
                if isinstance(dsm["breach_risk"], dict) and "status" in dsm["breach_risk"]
                else "ok",
                "source_label": prov.NEEDS_OFFICIAL_SOURCE,
                "detail": (
                    f"capacity_status={dsm['capacity_status']}, "
                    f"blocked={[b['calculation'] for b in dsm['blocked_calculations']]}"
                ),
            }
        )

        # 7) Orchestrator summary ---------------------------------------------
        data_sources = self._data_sources(context)
        limitations = self._limitations(context, wmeta, site_capacity_mw, dsm)
        trace.append(
            {
                "step": 7,
                "agent": "OrchestratorAgent",
                "action": "assemble context-linked result with full provenance",
                "status": "ok",
                "source_label": prov.ESTIMATED_FROM_REAL,
                "detail": f"{len(trace)} agent steps, {len(timeline)} timeline rows",
            }
        )

        return {
            "substation": context.model_dump(),
            "workflow": {"agent_trace": trace, "calculation_trace": calc},
            "weather": {
                "mode": wmeta["mode"],
                "source": wmeta["source"],
                "source_label": wmeta["source_label"],
                "hours": len(timestamps),
                "live_error": wmeta["live_error"],
            },
            "generation_timeline": timeline,
            "generation_summary": summary,
            "dsm_forecast": dsm,
            "data_sources": data_sources,
            "limitations": limitations,
            "data_mode": _data_mode(),
            "is_estimated": True,
            "is_synthetic": False,
            "production_ready": False,
        }

    # ------------------------------------------------------------------ #
    # Generation summary
    # ------------------------------------------------------------------ #
    @staticmethod
    def _generation_summary(timeline: list[dict], site_capacity_mw: float | None) -> dict:
        gens = [
            r["estimated_generation_mw"]
            for r in timeline
            if r["estimated_generation_mw"] is not None
        ]
        daylight = sum(1 for r in timeline if (r["forecast_ghi_wm2"] or 0.0) > 1.0)
        return {
            "intervals": len(timeline),
            "daylight_intervals": daylight,
            "peak_estimated_generation_mw": round(max(gens), 4) if gens else None,
            "total_estimated_energy_mwh": round(sum(gens), 4) if gens else None,
            "generation_type": "ESTIMATED_FROM_IRRADIANCE",
            "actual_generation_available": False,
            "site_capacity_mw": site_capacity_mw,
            "note": (
                "Generation is estimated from forecast irradiance; provide site_capacity_mw "
                "to obtain MW/MWh estimates."
                if not site_capacity_mw
                else "MW/MWh are ESTIMATED from irradiance + plant capacity, not measured."
            ),
        }

    # ------------------------------------------------------------------ #
    # DSM (honest, context-gated)
    # ------------------------------------------------------------------ #
    def _build_dsm_forecast(
        self,
        *,
        context: SubstationContext,
        timeline: list[dict],
        summary: dict,
        scheduled_generation_mw: float | None,
        site_capacity_mw: float | None,
        weather_by_key: dict,
        timestamps: list[datetime],
        calc: dict,
    ) -> dict:
        blocked: list[dict] = []

        # Capacity-based substation loading — capacity_mva is null in OSM.
        if context.capacity_mva is None:
            blocked.append(
                {
                    "calculation": "substation_loading_percent",
                    "reason": "substation capacity_mva unavailable (OpenStreetMap has no capacity)",
                    "needs": "official KPTCL/BESCOM substation capacity (MVA)",
                }
            )
            substation_loading_percent = None
        else:
            # Even with capacity we lack real substation load telemetry -> still blocked honestly.
            substation_loading_percent = None
            blocked.append(
                {
                    "calculation": "substation_loading_percent",
                    "reason": "no real substation load telemetry to divide by capacity",
                    "needs": "BESCOM substation/feeder real-time load (MW)",
                }
            )

        # Voltage-band optimisation.
        if context.voltage_kv is None:
            blocked.append(
                {
                    "calculation": "voltage_band_optimisation",
                    "reason": "voltage_kv unavailable for this substation",
                    "needs": "official substation voltage level (kV)",
                }
            )

        # Load-following optimisation.
        blocked.append(
            {
                "calculation": "load_following_optimisation",
                "reason": "no substation-level real-time load/demand feed",
                "needs": "BESCOM feeder/substation load time-series",
            }
        )

        # Rupee DSM charge.
        blocked.append(
            {
                "calculation": "dsm_rupee_charge",
                "reason": "no official KERC/CERC rupee DSM tariff is parsed",
                "needs": "official KERC/CERC DSM tariff order (rupee slabs)",
            }
        )

        # Deviation-breach risk (ML) + framework deviation — only when we can honestly derive
        # a scheduled irradiance from the operator's scheduled MW and the plant capacity.
        breach_risk: dict = {
            "status": prov.NOT_AVAILABLE,
            "reason": "scheduled_generation_mw and site_capacity_mw are required to estimate a "
            "scheduled irradiance for deviation assessment; not provided.",
        }
        deviation_percent = None
        deviation_band = None
        scheduled_ghi_estimate = None
        estimated_energy = summary["total_estimated_energy_mwh"]

        if scheduled_generation_mw is not None and site_capacity_mw:
            scheduled_ghi_estimate = round(
                scheduled_generation_mw / (site_capacity_mw * PERFORMANCE_RATIO) * 1000.0, 2
            )
            # Representative (peak-GHI) hour drives the ML DSM features.
            rep_key = max(
                timestamps, key=lambda t: weather_by_key[t.strftime(_HOUR_KEY)]["clearsky_ghi_wm2"]
            ).strftime(_HOUR_KEY)
            rep_weather = dict(weather_by_key[rep_key])
            breach_risk = agent_models.predict_dsm(
                {**rep_weather, "scheduled_ghi_wm2": scheduled_ghi_estimate}
            )
            calc["scheduled_ghi_estimate_wm2"] = {
                "formula": "scheduled_generation_mw / (site_capacity_mw * performance_ratio) * 1000",
                "inputs": {
                    "scheduled_generation_mw": scheduled_generation_mw,
                    "site_capacity_mw": site_capacity_mw,
                    "performance_ratio": PERFORMANCE_RATIO,
                },
                "source_label": prov.ESTIMATED_FROM_REAL,
                "note": "Scheduled irradiance is BACK-ESTIMATED from the scheduled MW; framework only.",
            }
            if estimated_energy is not None:
                scheduled_energy = scheduled_generation_mw * len(
                    timeline
                )  # constant MW over 1h blocks
                if scheduled_energy > 0:
                    deviation_percent = round(
                        (estimated_energy - scheduled_energy) / scheduled_energy * 100.0, 2
                    )
                    within = abs(deviation_percent) <= 15.0
                    deviation_band = (
                        "WITHIN_MODELLING_BAND(+/-15%)"
                        if within
                        else "EXCEEDS_MODELLING_BAND(+/-15%)"
                    )
                    calc["deviation_percent"] = {
                        "formula": "(estimated_energy_mwh - scheduled_energy_mwh) / scheduled_energy_mwh * 100",
                        "inputs": {
                            "estimated_energy_mwh": estimated_energy,
                            "scheduled_energy_mwh": round(scheduled_energy, 4),
                        },
                        "source_label": prov.ESTIMATED_FROM_REAL,
                        "note": "+/-15% band is a MODELLING parameter, not an official KERC/CERC value.",
                    }

        return {
            "substation_id": context.substation_id,
            "substation_label": context.display_label,
            "generation_type": "ESTIMATED_FROM_IRRADIANCE",
            "actual_generation_available": False,
            "scheduled_generation_mw": scheduled_generation_mw,
            "estimated_energy_mwh": estimated_energy,
            "scheduled_ghi_estimate_wm2": scheduled_ghi_estimate,
            "deviation_percent": deviation_percent,
            "deviation_band": deviation_band,
            "breach_risk": breach_risk,
            "framework_recommendation": breach_risk.get("framework_recommendation")
            if isinstance(breach_risk, dict)
            else None,
            "capacity_status": context.capacity_status,
            "voltage_status": context.voltage_status,
            "load_data_status": context.load_data_status,
            "tariff_status": context.tariff_status,
            "tariff_region": context.tariff_region,
            "substation_loading_percent": substation_loading_percent,
            "emits_rupee_values": False,
            "blocked_calculations": blocked,
            "context_inputs_used": {
                "substation_id": context.substation_id,
                "latitude": context.latitude,
                "longitude": context.longitude,
                "voltage_kv": context.voltage_kv,
                "capacity_mva": context.capacity_mva,
                "source_label": context.source_label,
            },
            "limitations": [
                "Framework-only DSM: no rupee charge is computed (NEEDS_OFFICIAL_SOURCE).",
                "+/-15% deviation band is a modelling parameter, not an official KERC/CERC value.",
                "Substation-level DSM is limited: capacity_mva and real load telemetry are unavailable.",
            ],
        }

    # ------------------------------------------------------------------ #
    # Provenance helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _data_sources(context: SubstationContext) -> list[dict]:
        return [
            {
                "name": "OpenStreetMap (Overpass) substations",
                "url": context.source_url or "https://www.openstreetmap.org",
                "label": context.source_label,
                "geography": context.data_geography or "Bengaluru, Karnataka, India",
            },
            {
                "name": "Open-Meteo weather (queried at substation coordinates)",
                "url": "https://open-meteo.com",
                "label": prov.REAL_COORDINATE_BASED,
                "geography": f"({context.latitude}, {context.longitude})",
            },
            {
                "name": "solar_forecast_model.pkl (Bengaluru irradiance)",
                "url": "backend/models/metadata/solar_forecast_model_card.json",
                "label": prov.REAL_BENGALURU,
                "geography": "Bengaluru, Karnataka, India",
            },
            {
                "name": "cloud_risk_classifier.pkl (Bengaluru)",
                "url": "backend/models/metadata/cloud_risk_classifier_card.json",
                "label": prov.REAL_BENGALURU,
                "geography": "Bengaluru, Karnataka, India",
            },
            {
                "name": "DSM framework (KERC/CERC) - no rupee tariff parsed",
                "url": "docs/DSM_RULE_SOURCES.md",
                "label": prov.NEEDS_OFFICIAL_SOURCE,
                "geography": "Karnataka, India",
            },
        ]

    @staticmethod
    def _limitations(
        context: SubstationContext, wmeta: dict, site_capacity_mw: float | None, dsm: dict
    ) -> list[str]:
        notes = list(context.limitation_notes)
        if wmeta["mode"] != "live":
            notes.append(
                "Live weather was not used for this run; irradiance falls back to pvlib "
                "clear-sky physics at the substation coordinates (REAL_COORDINATE_BASED)."
            )
        if not site_capacity_mw:
            notes.append(
                "No site_capacity_mw provided; generation is reported as irradiance only, "
                "not MW/MWh."
            )
        notes.extend(dsm["limitations"])
        # dedupe, preserve order
        out: list[str] = []
        for n in notes:
            if n not in out:
                out.append(n)
        return out


_orchestrator = SubstationOrchestrator()


def get_substation_orchestrator() -> SubstationOrchestrator:
    return _orchestrator
