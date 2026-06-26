"""Synthetic consumption (load) profiles.

Phase 0 uses deterministic load profiles for residential, commercial and
industrial consumers. Later phases wire in real meter data.
"""

from __future__ import annotations

import math


def _bell(hour: float, peak_hour: float, width: float) -> float:
    return math.exp(-0.5 * ((hour - peak_hour) / width) ** 2)


def residential_load_kw(hour: float, base_kw: float = 2.0) -> float:
    """Typical Indian residential pattern: morning + evening peaks."""
    morning = _bell(hour, 7.5, 1.5) * 1.5
    evening = _bell(hour, 19.5, 2.0) * 2.5
    overnight = 0.3 if hour < 6 or hour > 22 else 0.0
    return base_kw * (0.4 + morning + evening + overnight)


def commercial_load_kw(hour: float, base_kw: float = 50.0) -> float:
    """Office/retail: flat 9-18, lower outside."""
    if 9 <= hour <= 18:
        return base_kw * (0.8 + 0.2 * _bell(hour, 13.5, 3))
    return base_kw * 0.2


def industrial_load_kw(hour: float, base_kw: float = 200.0) -> float:
    """Factory: two shifts (6-14, 14-22), low overnight."""
    if 6 <= hour <= 22:
        return base_kw * (0.7 + 0.3 * _bell(hour, 10, 4))
    return base_kw * 0.25


PROFILES = {
    "residential": residential_load_kw,
    "commercial": commercial_load_kw,
    "industrial": industrial_load_kw,
}


def generate_consumption_day(
    profile: str = "commercial",
    base_kw: float = 50.0,
    hours: int = 24,
) -> list[dict]:
    """Generate an hourly consumption profile for one day."""
    fn = PROFILES.get(profile, commercial_load_kw)
    return [{"hour": h, "consumption_kw": round(fn(float(h), base_kw), 2)} for h in range(hours)]
