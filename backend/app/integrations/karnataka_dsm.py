"""Karnataka (KERC / BESCOM) Deviation Settlement Mechanism engine.

Implements the Karnataka intra-state DSM framework for solar generators under the
KERC Forecasting, Scheduling & Deviation Settlement regulations:

- Deviation is computed against available capacity (KERC Reg. 6(2)(a)).
- Solar tolerance band is +/- 5% (KERC retained +/-5% for solar, 2026).
- Charges apply only to the deviation BEYOND the band, on a slab basis: the
  further the deviation, the higher the per-unit charge.

Slab rates are configurable (KERC revises them by order); the defaults below
encode the documented band and a representative escalating slab schedule in
INR per kWh. This is the regulatory math layer — a live BESCOM/SLDC telemetry
feed (real metered injection) plugs in via BescomConnector when a data-sharing
agreement is in place.
"""

from __future__ import annotations

from dataclasses import dataclass

# KERC solar DSM tolerance band (percent of available capacity).
KERC_SOLAR_BAND_PERCENT = 5.0

# Escalating slab charges (INR per kWh) applied to deviation energy beyond the
# band. (lower_pct_inclusive, upper_pct_exclusive, rate_inr_per_kwh)
# Representative of the KERC slab structure; override per the latest KERC order.
DEFAULT_SLABS: list[tuple[float, float, float]] = [
    (5.0, 10.0, 2.0),
    (10.0, 15.0, 4.0),
    (15.0, 100.0, 6.0),
]


@dataclass(slots=True)
class KarnatakaDSMResult:
    available_capacity_mw: float
    actual_mw: float
    scheduled_mw: float
    deviation_mw: float
    deviation_percent: float  # of available capacity
    within_band: bool
    band_percent: float
    chargeable_energy_mwh: float
    dsm_charge_inr: float
    direction: str  # "under-injection" | "over-injection" | "balanced"
    slab_breakdown: list[dict]


class KarnatakaDSM:
    def __init__(
        self,
        band_percent: float = KERC_SOLAR_BAND_PERCENT,
        slabs: list[tuple[float, float, float]] | None = None,
    ):
        self.band_percent = band_percent
        self.slabs = slabs or DEFAULT_SLABS

    def settle(
        self,
        actual_mw: float,
        scheduled_mw: float,
        available_capacity_mw: float,
        interval_hours: float = 0.25,  # KERC settles in 15-min blocks
    ) -> KarnatakaDSMResult:
        cap = max(available_capacity_mw, 1e-9)
        deviation_mw = actual_mw - scheduled_mw
        abs_dev_mw = abs(deviation_mw)
        # KERC: deviation as % of available capacity.
        deviation_percent = (abs_dev_mw / cap) * 100.0

        direction = (
            "balanced"
            if abs(deviation_mw) < 1e-9
            else ("over-injection" if deviation_mw > 0 else "under-injection")
        )

        within_band = deviation_percent <= self.band_percent
        chargeable_energy_mwh = 0.0
        charge = 0.0
        breakdown: list[dict] = []

        if not within_band:
            # Charge each slab on the portion of deviation-% within that slab.
            for low, high, rate in self.slabs:
                slab_low = max(low, self.band_percent)
                if deviation_percent <= slab_low:
                    continue
                slab_hi = min(high, deviation_percent)
                if slab_hi <= slab_low:
                    continue
                pct_in_slab = slab_hi - slab_low
                energy_mwh = (pct_in_slab / 100.0) * cap * interval_hours
                slab_charge = energy_mwh * rate * 1000.0  # MWh→kWh × INR/kWh
                chargeable_energy_mwh += energy_mwh
                charge += slab_charge
                breakdown.append(
                    {
                        "slab_percent": f"{slab_low:.0f}-{slab_hi:.0f}%",
                        "rate_inr_per_kwh": rate,
                        "energy_mwh": round(energy_mwh, 4),
                        "charge_inr": round(slab_charge, 2),
                    }
                )

        return KarnatakaDSMResult(
            available_capacity_mw=round(available_capacity_mw, 3),
            actual_mw=round(actual_mw, 3),
            scheduled_mw=round(scheduled_mw, 3),
            deviation_mw=round(deviation_mw, 4),
            deviation_percent=round(deviation_percent, 2),
            within_band=within_band,
            band_percent=self.band_percent,
            chargeable_energy_mwh=round(chargeable_energy_mwh, 4),
            dsm_charge_inr=round(charge, 2),
            direction=direction,
            slab_breakdown=breakdown,
        )
