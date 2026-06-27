"""Karnataka solar site registry.

Real utility-scale solar parks and Bangalore-area locations across Karnataka,
used to seed the platform with realistic sites under the BESCOM/KERC framework.
Coordinates are approximate park centroids; capacities are public figures.
"""

from __future__ import annotations

# Karnataka is in IST and the northern hemisphere → panels face south (azimuth 180).
# Tilt ~ latitude is a reasonable fixed-tilt default.
KARNATAKA_SITES: list[dict] = [
    {
        "name": "Pavagada Solar Park (Shakti Sthala)",
        "latitude": 14.10,
        "longitude": 77.28,
        "capacity_mw": 2050.0,
        "tilt": 14.0,
        "region": "Tumakuru",
        "discom": "BESCOM",
    },
    {
        "name": "Bidar Solar Park",
        "latitude": 17.91,
        "longitude": 77.52,
        "capacity_mw": 150.0,
        "tilt": 18.0,
        "region": "Bidar",
        "discom": "GESCOM",
    },
    {
        "name": "Koppal Solar Park",
        "latitude": 15.35,
        "longitude": 76.15,
        "capacity_mw": 200.0,
        "tilt": 15.0,
        "region": "Koppal",
        "discom": "GESCOM",
    },
    {
        "name": "Bangalore — Peenya Industrial Rooftop Cluster",
        "latitude": 13.03,
        "longitude": 77.52,
        "capacity_mw": 25.0,
        "tilt": 13.0,
        "region": "Bengaluru Urban",
        "discom": "BESCOM",
    },
    {
        "name": "Bangalore — Electronic City Solar",
        "latitude": 12.85,
        "longitude": 77.66,
        "capacity_mw": 40.0,
        "tilt": 13.0,
        "region": "Bengaluru Urban",
        "discom": "BESCOM",
    },
    {
        "name": "Bangalore — Kempegowda Airport Solar",
        "latitude": 13.20,
        "longitude": 77.71,
        "capacity_mw": 40.0,
        "tilt": 13.0,
        "region": "Bengaluru Rural",
        "discom": "BESCOM",
    },
]


def to_site_payload(entry: dict) -> dict:
    """Map a registry entry to the SiteCreateRequest payload (KERC ±5% band)."""
    return {
        "name": entry["name"],
        "latitude": entry["latitude"],
        "longitude": entry["longitude"],
        "timezone": "Asia/Kolkata",
        "capacity_mw": entry["capacity_mw"],
        "tilt": entry["tilt"],
        "azimuth": 180.0,
        "allowed_dsm_threshold_percent": 5.0,  # KERC solar DSM band
        "penalty_rate_per_mwh": 12000.0,
    }
