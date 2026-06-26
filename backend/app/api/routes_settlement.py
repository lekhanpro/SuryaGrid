"""Settlement API - reward/penalty/discount engine + RL (real-data trained)."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.reward_agent import RewardAgent
from app.db import repository
from app.db.session import get_db
from app.rl.policy import RLPolicy
from app.services.consumption_service import generate_consumption_day
from app.services.forecast_service import ForecastService
from app.services.site_resolver import resolve_site
from app.utils.response import success_response

router = APIRouter()
_reward = RewardAgent()
_service = ForecastService()
_policy = RLPolicy()


@router.post("/settle")
async def settle_interval(
    target_kw: float = Query(gt=0),
    actual_kw: float = Query(ge=0),
    consumption_kw: float = Query(default=0.0, ge=0),
    window_hours: float = Query(default=1.0, gt=0),
    use_rl_rates: bool = Query(default=False),
):
    penalty_rate = bonus_rate = discount_rate = None
    if use_rl_rates:
        rates = _policy.get_rates(np.zeros(8, dtype=np.float32))
        penalty_rate = rates["penalty_rate"]
        bonus_rate = rates["bonus_rate"]
        discount_rate = rates["discount_rate"]

    result = _reward.settle(
        target_kw=target_kw,
        actual_kw=actual_kw,
        window_hours=window_hours,
        consumption_kw=consumption_kw,
        penalty_rate=penalty_rate,
        bonus_rate=bonus_rate,
        discount_rate=discount_rate,
    )
    return success_response(
        data={
            "target_kw": result.target_kw,
            "actual_kw": result.actual_kw,
            "shortfall_kw": result.shortfall_kw,
            "surplus_kw": result.surplus_kw,
            "penalty_amount": result.penalty_amount,
            "bonus_amount": result.bonus_amount,
            "discount_amount": result.discount_amount,
            "net_owner": result.net_owner,
            "rates": {
                "penalty_rate": result.penalty_rate,
                "bonus_rate": result.bonus_rate,
                "discount_rate": result.discount_rate,
            },
        }
    )


@router.post("/settle/day/{site_id}")
async def settle_day(
    site_id: str,
    latitude: float = Query(default=28.6, ge=-90, le=90),
    longitude: float = Query(default=77.2, ge=-180, le=180),
    timezone_str: str = Query(default="Asia/Kolkata", alias="timezone"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    consumption_profile: str = Query(default="commercial"),
    consumption_base_kw: float = Query(default=5000.0, gt=0),
    use_rl_rates: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    resolved = await resolve_site(
        db, site_id, latitude, longitude, timezone_str, capacity_mw, tilt, azimuth
    )
    result = await _service.build_timeline(
        site=resolved.config,
        scheduled_generation_mw=None,
        allowed_dsm_threshold_percent=resolved.threshold_percent,
        penalty_rate_per_mwh=resolved.penalty_rate_per_mwh,
    )
    timeline = result["timeline"]
    actuals = [e["predicted_generation_mw"] * 1000 for e in timeline]
    targets = [e["scheduled_generation_mw"] * 1000 for e in timeline]

    consumption_day = generate_consumption_day(
        profile=consumption_profile, base_kw=consumption_base_kw, hours=len(timeline)
    )
    consumptions = [c["consumption_kw"] for c in consumption_day]

    rates = _policy.get_rates(np.zeros(8, dtype=np.float32)) if use_rl_rates else {}
    settlement = _reward.settle_day(
        targets=targets,
        actuals=actuals,
        consumptions=consumptions,
        penalty_rate=rates.get("penalty_rate"),
        bonus_rate=rates.get("bonus_rate"),
        discount_rate=rates.get("discount_rate"),
    )
    settlement["site_id"] = site_id
    settlement["capacity_mw"] = resolved.config.capacity_mw
    settlement["consumption_profile"] = consumption_profile
    settlement["rl_rates"] = rates if use_rl_rates else None

    # Persist settlements when the site is registered.
    if resolved.site_uuid is not None:
        rows = []
        for i, e in enumerate(settlement["settlements"]):
            ts = datetime.fromisoformat(timeline[i]["timestamp"])
            rows.append(
                {
                    "window_start": ts,
                    "window_end": None,
                    "target_kw": e["target_kw"],
                    "actual_kw": e["actual_kw"],
                    "penalty": e["penalty"],
                    "bonus": e["bonus"],
                    "discount": e["discount"],
                    "net_owner": e["net_owner"],
                    "penalty_rate": rates.get("penalty_rate", 0.0),
                    "bonus_rate": rates.get("bonus_rate", 0.0),
                    "discount_rate": rates.get("discount_rate", 0.0),
                }
            )
        await repository.save_settlements(db, resolved.site_uuid, rows)
        settlement["persisted"] = True

    return success_response(data=settlement)


@router.get("/settlements/{site_id}")
async def list_settlements(site_id: str, db: AsyncSession = Depends(get_db)):
    site = await repository.get_site(db, site_id)
    if site is None:
        return success_response(data={"site_id": site_id, "settlements": []})
    rows = await repository.list_settlements(db, site.id)
    return success_response(
        data={
            "site_id": site_id,
            "count": len(rows),
            "settlements": [
                {
                    "window_start": s.window_start.isoformat(),
                    "target_kw": s.target_kw,
                    "actual_kw": s.actual_kw,
                    "penalty": s.penalty,
                    "bonus": s.bonus,
                    "discount": s.discount,
                    "net_owner": s.net_owner,
                }
                for s in rows
            ],
        }
    )


@router.get("/rl/rates")
async def get_rl_rates():
    rates = _policy.get_rates(np.zeros(8, dtype=np.float32))
    return success_response(data=rates)


@router.get("/rl/runs")
async def list_runs(db: AsyncSession = Depends(get_db)):
    runs = await repository.list_training_runs(db)
    return success_response(
        data=[
            {
                "id": str(r.id),
                "algorithm": r.algorithm,
                "episodes": r.episodes,
                "data_source": r.data_source,
                "best_reward": r.best_reward,
                "mean_reward": r.mean_reward,
                "final_rates": r.final_rates,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    )


@router.post("/rl/train")
async def train_rl(
    episodes: int = Query(default=300, ge=10, le=3000),
    use_real_data: bool = Query(default=True),
    latitude: float = Query(default=27.53, ge=-90, le=90),
    longitude: float = Query(default=71.91, ge=-180, le=180),
    timezone_str: str = Query(default="Asia/Kolkata", alias="timezone"),
    capacity_mw: float = Query(default=50.0, gt=0),
    days_back: int = Query(default=90, ge=14, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Train the RL policy. Defaults to REAL historical data (Open-Meteo archive)."""
    global _policy
    from app.rl.train import train, train_real

    data_source = "synthetic-twin"
    dataset_days = 0
    if use_real_data:
        from app.rl.data import build_real_dataset

        dataset = await build_real_dataset(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone_str,
            capacity_mw=capacity_mw,
            days_back=days_back,
        )
        dataset_days = len(dataset)
        if dataset_days >= 10:
            metrics = train_real(
                dataset=dataset, capacity_kw=capacity_mw * 1000, episodes=episodes, verbose=False
            )
            data_source = f"open-meteo-archive ({dataset_days} real days)"
        else:
            policy = train(episodes=episodes, verbose=False)
            metrics = {"policy": policy, "best_reward": 0.0, "mean_reward": 0.0}
    else:
        policy = train(episodes=episodes, verbose=False)
        metrics = {"policy": policy, "best_reward": 0.0, "mean_reward": 0.0}

    _policy = metrics["policy"]
    final_rates = _policy.get_rates(np.zeros(8, dtype=np.float32))

    run = await repository.save_training_run(
        db,
        {
            "algorithm": "REINFORCE",
            "episodes": episodes,
            "data_source": data_source,
            "best_reward": metrics.get("best_reward", 0.0),
            "mean_reward": metrics.get("mean_reward", 0.0),
            "final_rates": final_rates,
            "notes": f"trained_at={datetime.now(UTC).isoformat()}",
        },
    )

    return success_response(
        data={
            "run_id": str(run.id),
            "episodes": episodes,
            "data_source": data_source,
            "real_days_used": dataset_days,
            "best_reward": metrics.get("best_reward", 0.0),
            "mean_reward": metrics.get("mean_reward", 0.0),
            "final_rates": final_rates,
        },
        message="RL policy trained",
    )
