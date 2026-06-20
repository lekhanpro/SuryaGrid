"""API routes for synthetic weather data generation (Phase 1 local data provider)."""

from datetime import date
from fastapi import APIRouter, Query
from app.agents.synthetic_data_agent import SyntheticDataAgent
from app.utils.response import success_response

router = APIRouter()
_agent = SyntheticDataAgent()

# In-memory store of generated data per site
_data_store: dict[str, list[dict]] = {}


async def _generate(site_id: str, target_date: date, capacity_mw: float, interval_minutes: int, seed: int | None):
    if target_date is None:
        target_date = date.today()

    points = _agent.generate_site_day(
        site_id=site_id, target_date=target_date,
        capacity_mw=capacity_mw, interval_minutes=interval_minutes, seed=seed,
    )

    data = [
        {
            "timestamp": p.timestamp.isoformat(),
            "irradiance_w_m2": p.irradiance_w_m2,
            "cloud_cover_percent": p.cloud_cover_percent,
            "temperature_c": p.temperature_c,
            "humidity_percent": p.humidity_percent,
            "wind_speed_mps": p.wind_speed_mps,
            "rain_probability_percent": p.rain_probability_percent,
        }
        for p in points
    ]
    _data_store[site_id] = data
    return {"site_id": site_id, "date": target_date.isoformat(), "readings_count": len(data), "readings": data}


@router.post("/synthetic-data/generate")
async def generate_synthetic_data(
    site_id: str = Query(...),
    target_date: date = Query(default=None),
    capacity_mw: float = Query(default=50.0, gt=0),
    interval_minutes: int = Query(default=30, ge=5, le=60),
    seed: int | None = Query(default=None),
):
    result = await _generate(site_id, target_date, capacity_mw, interval_minutes, seed)
    return success_response(data=result, message="Synthetic weather data generated")


# Backward compatibility endpoint
@router.post("/toy-data/generate")
async def generate_toy_data_compat(
    site_id: str = Query(...),
    target_date: date = Query(default=None),
    capacity_mw: float = Query(default=50.0, gt=0),
    interval_minutes: int = Query(default=30, ge=5, le=60),
    seed: int | None = Query(default=None),
):
    result = await _generate(site_id, target_date, capacity_mw, interval_minutes, seed)
    return success_response(data=result, message="Synthetic weather data generated")


@router.get("/synthetic-data/{site_id}")
async def get_synthetic_data(site_id: str):
    data = _data_store.get(site_id, [])
    return success_response(data={"site_id": site_id, "readings_count": len(data), "readings": data})


# Backward compatibility endpoint
@router.get("/toy-data/{site_id}")
async def get_toy_data_compat(site_id: str):
    data = _data_store.get(site_id, [])
    return success_response(data={"site_id": site_id, "readings_count": len(data), "readings": data})
