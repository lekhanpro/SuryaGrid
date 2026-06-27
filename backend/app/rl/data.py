"""Build a real historical training dataset for the RL policy.

Fetches genuine past weather from the Open-Meteo archive, runs it through the
pvlib ForecastAgent to get real production and clear-sky target curves, and
pairs each day with a synthetic consumption profile. The RL environment then
trains on these real days instead of a toy simulation.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

import numpy as np

from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.providers.open_meteo import OpenMeteoProvider
from app.services.consumption_service import generate_consumption_day


async def build_real_dataset(
    latitude: float,
    longitude: float,
    timezone: str,
    capacity_mw: float,
    days_back: int = 120,
    years: int = 0,
    consumption_profile: str = "commercial",
    max_days: int = 1500,
) -> list[dict]:
    """Return a list of real days, each with per-hour arrays (kW).

    Each entry: {"date", "production_kw"[24], "target_kw"[24],
                 "consumption_kw"[24], "cloud"[24]}.

    If ``years`` > 0, fetches that many full years of ERA5 history (chunked by
    year to keep each request small); otherwise uses the trailing ``days_back``.
    """
    provider = OpenMeteoProvider()
    agent = ForecastAgent()
    site = SiteConfig(
        latitude=latitude, longitude=longitude, timezone=timezone, capacity_mw=capacity_mw
    )

    # ERA5 archive has a ~5-7 day delay; end a week ago.
    end = date.today() - timedelta(days=7)

    # Build the list of (start, end) windows to fetch.
    windows: list[tuple[date, date]] = []
    if years and years > 0:
        cursor_end = end
        for _ in range(years):
            cursor_start = cursor_end - timedelta(days=365)
            windows.append((cursor_start, cursor_end))
            cursor_end = cursor_start - timedelta(days=1)
    else:
        windows.append((end - timedelta(days=days_back), end))

    points = []
    for start, win_end in windows:
        chunk = await provider.fetch_archive(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            start_date=start.isoformat(),
            end_date=win_end.isoformat(),
        )
        points.extend(chunk)

    # Group hourly points by local date.
    by_day: dict[date, list] = defaultdict(list)
    for p in points:
        by_day[p.timestamp.date()].append(p)

    base_consumption_kw = capacity_mw * 1000 * 0.3
    consumption_day = generate_consumption_day(
        profile=consumption_profile, base_kw=base_consumption_kw, hours=24
    )
    consumption_arr = [c["consumption_kw"] for c in consumption_day]

    dataset: list[dict] = []
    for day, day_points in sorted(by_day.items()):
        if len(day_points) < 24:
            continue
        day_points = sorted(day_points, key=lambda x: x.timestamp)[:24]
        forecast = agent.forecast_timeline(site, day_points)
        production = [fp.predicted_generation_mw * 1000 for fp in forecast]  # kW
        target = [fp.clearsky_generation_mw * 1000 for fp in forecast]  # kW
        cloud = [fp.cloud_cover_percent for fp in forecast]
        if max(production) <= 0:
            continue
        dataset.append(
            {
                "date": day.isoformat(),
                "production_kw": np.array(production, dtype=np.float32),
                "target_kw": np.array(target, dtype=np.float32),
                "consumption_kw": np.array(consumption_arr, dtype=np.float32),
                "cloud": np.array(cloud, dtype=np.float32),
            }
        )
        if len(dataset) >= max_days:
            break

    return dataset
