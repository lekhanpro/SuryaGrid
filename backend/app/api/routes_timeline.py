"""Timeline and Summary APIs - generates full-day prediction timeline."""

from datetime import date
from fastapi import APIRouter, Query
from app.agents.synthetic_data_agent import SyntheticDataAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.utils.response import success_response

router = APIRouter()
_data_agent = SyntheticDataAgent()
_orchestrator = OrchestratorAgent()


@router.get("/timeline/{site_id}")
async def get_timeline(
    site_id: str,
    target_date: date = Query(default=None),
    capacity_mw: float = Query(default=50.0, gt=0),
    scheduled_mw: float = Query(default=35.0, ge=0),
    threshold_percent: float = Query(default=10.0, ge=0),
    penalty_rate: float = Query(default=15000.0, ge=0),
    seed: int = Query(default=42),
):
    if target_date is None:
        target_date = date.today()

    points = _data_agent.generate_site_day(
        site_id=site_id, target_date=target_date,
        capacity_mw=capacity_mw, interval_minutes=30, seed=seed,
    )
    schedule = _data_agent.generate_schedule(capacity_mw, target_date, interval_minutes=30)
    schedule_map = {ts.isoformat(): mw for ts, mw in schedule}

    timeline = []
    for p in points:
        sched_mw = schedule_map.get(p.timestamp.isoformat(), scheduled_mw)
        if sched_mw <= 0:
            sched_mw = scheduled_mw

        result = _orchestrator.run_prediction_cycle(
            solar_capacity_mw=capacity_mw,
            irradiance_w_m2=p.irradiance_w_m2,
            cloud_cover_percent=p.cloud_cover_percent,
            temperature_c=p.temperature_c,
            scheduled_generation_mw=sched_mw,
            allowed_dsm_threshold_percent=threshold_percent,
            penalty_rate_per_mw=penalty_rate,
        )

        timeline.append({
            "timestamp": p.timestamp.isoformat(),
            "irradiance_w_m2": p.irradiance_w_m2,
            "cloud_cover_percent": p.cloud_cover_percent,
            "temperature_c": p.temperature_c,
            "predicted_generation_mw": result["predicted_generation_mw"],
            "scheduled_generation_mw": sched_mw,
            "deviation_mw": result["deviation_mw"],
            "deviation_percent": result["deviation_percent"],
            "penalty_status": result["penalty_status"],
            "fuzzy_risk_level": result["fuzzy_risk_level"],
        })

    return success_response(data={"site_id": site_id, "date": target_date.isoformat(), "timeline": timeline})


@router.get("/summary/{site_id}")
async def get_summary(
    site_id: str,
    target_date: date = Query(default=None),
    capacity_mw: float = Query(default=50.0, gt=0),
    scheduled_mw: float = Query(default=35.0, ge=0),
    threshold_percent: float = Query(default=10.0, ge=0),
    penalty_rate: float = Query(default=15000.0, ge=0),
    seed: int = Query(default=42),
):
    if target_date is None:
        target_date = date.today()

    points = _data_agent.generate_site_day(
        site_id=site_id, target_date=target_date,
        capacity_mw=capacity_mw, interval_minutes=30, seed=seed,
    )
    schedule = _data_agent.generate_schedule(capacity_mw, target_date, interval_minutes=30)
    schedule_map = {ts.isoformat(): mw for ts, mw in schedule}

    total_predicted = 0.0
    total_scheduled = 0.0
    penalty_count = 0
    max_deviation = 0.0

    for p in points:
        sched_mw = schedule_map.get(p.timestamp.isoformat(), scheduled_mw)
        if sched_mw <= 0:
            sched_mw = scheduled_mw

        result = _orchestrator.run_prediction_cycle(
            solar_capacity_mw=capacity_mw,
            irradiance_w_m2=p.irradiance_w_m2,
            cloud_cover_percent=p.cloud_cover_percent,
            temperature_c=p.temperature_c,
            scheduled_generation_mw=sched_mw,
            allowed_dsm_threshold_percent=threshold_percent,
            penalty_rate_per_mw=penalty_rate,
        )

        total_predicted += result["predicted_generation_mw"]
        total_scheduled += sched_mw
        if result["penalty_status"] == "PENALTY_RISK":
            penalty_count += 1
        max_deviation = max(max_deviation, result["deviation_percent"])

    return success_response(data={
        "site_id": site_id,
        "date": target_date.isoformat(),
        "total_intervals": len(points),
        "total_predicted_mw": round(total_predicted, 3),
        "total_scheduled_mw": round(total_scheduled, 3),
        "penalty_intervals": penalty_count,
        "max_deviation_percent": round(max_deviation, 2),
        "capacity_mw": capacity_mw,
    })
