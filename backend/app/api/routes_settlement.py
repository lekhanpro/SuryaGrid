"""Settlement API - reward/penalty/discount engine endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.agents.reward_agent import RewardAgent
from app.rl.policy import RLPolicy
from app.services.consumption_service import generate_consumption_day
from app.services.forecast_service import ForecastService
from app.services.site_store import site_store
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
    """Settle a single interval."""
    penalty_rate = bonus_rate = discount_rate = None
    if use_rl_rates:
        import numpy as np

        state = np.zeros(8, dtype=np.float32)  # simplified state for standalone
        rates = _policy.get_rates(state)
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
    timezone: str = Query(default="Asia/Kolkata"),
    capacity_mw: float = Query(default=50.0, gt=0),
    tilt: float = Query(default=20.0, ge=0, le=90),
    azimuth: float = Query(default=180.0, ge=0, le=360),
    consumption_profile: str = Query(default="commercial"),
    consumption_base_kw: float = Query(default=5000.0, gt=0),
):
    """Run a full day forecast + settlement for a site."""
    from app.agents.forecast_agent import SiteConfig

    try:
        site = site_store.get(site_id)
        config = site_store.to_config(site)
    except Exception:
        config = SiteConfig(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            capacity_mw=capacity_mw,
            tilt=tilt,
            azimuth=azimuth,
        )

    # Get forecast
    result = await _service.build_timeline(
        site=config,
        scheduled_generation_mw=None,  # clear-sky baseline as target
        allowed_dsm_threshold_percent=10.0,
        penalty_rate_per_mwh=12000.0,
    )
    timeline = result["timeline"]

    # Convert MW to kW for settlement
    actuals = [e["predicted_generation_mw"] * 1000 for e in timeline]
    targets = [e["scheduled_generation_mw"] * 1000 for e in timeline]

    # Generate consumption
    consumption_day = generate_consumption_day(
        profile=consumption_profile, base_kw=consumption_base_kw, hours=len(timeline)
    )
    consumptions = [c["consumption_kw"] for c in consumption_day]

    # Settle
    settlement = _reward.settle_day(targets=targets, actuals=actuals, consumptions=consumptions)
    settlement["site_id"] = site_id
    settlement["capacity_mw"] = config.capacity_mw
    settlement["consumption_profile"] = consumption_profile

    return success_response(data=settlement)


@router.get("/rl/rates")
async def get_rl_rates():
    """Get the current RL-suggested rates."""
    import numpy as np

    state = np.zeros(8, dtype=np.float32)
    rates = _policy.get_rates(state)
    return success_response(data=rates)


@router.post("/rl/train")
async def train_rl(episodes: int = Query(default=200, ge=10, le=2000)):
    """Train/retrain the RL policy on the digital twin."""
    global _policy
    from app.rl.train import train

    _policy = train(episodes=episodes, verbose=False)
    return success_response(
        data={"episodes": episodes, "status": "trained", "policy_trained": True},
        message="RL policy trained successfully",
    )
