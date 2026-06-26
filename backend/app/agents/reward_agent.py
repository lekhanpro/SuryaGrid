"""RewardAgent - settlement engine for the reward/penalty/discount scheme.

Business logic (from PROJECT_PLAN.md section 5):
- Plant owner commits a target T (kW) for a settlement window.
- Actual production P is measured.
- If P >= T: owner earns a bonus proportional to the surplus.
- If P < T: owner pays a penalty proportional to the shortfall.
- Consumers earn a discount for absorbing surplus or demand-response.

The penalty_rate, bonus_rate and discount_rate are set by the RL policy (or
sensible defaults when no trained policy is available).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SettlementResult:
    """Outcome of one settlement window."""

    target_kw: float
    actual_kw: float
    shortfall_kw: float
    surplus_kw: float
    penalty_amount: float
    bonus_amount: float
    discount_amount: float
    net_owner: float  # bonus - penalty (positive = credit)
    penalty_rate: float
    bonus_rate: float
    discount_rate: float
    window_hours: float


# Default rates (INR per kW·h) — conservative starting point.
DEFAULT_PENALTY_RATE = 8.0  # INR/kWh shortfall
DEFAULT_BONUS_RATE = 4.0  # INR/kWh surplus
DEFAULT_DISCOUNT_RATE = 2.0  # INR/kWh shifted consumption


class RewardAgent:
    """Settles one window. Rates come from the RL policy or defaults."""

    def settle(
        self,
        target_kw: float,
        actual_kw: float,
        window_hours: float = 1.0,
        consumption_kw: float = 0.0,
        penalty_rate: float | None = None,
        bonus_rate: float | None = None,
        discount_rate: float | None = None,
    ) -> SettlementResult:
        pr = penalty_rate if penalty_rate is not None else DEFAULT_PENALTY_RATE
        br = bonus_rate if bonus_rate is not None else DEFAULT_BONUS_RATE
        dr = discount_rate if discount_rate is not None else DEFAULT_DISCOUNT_RATE

        shortfall = max(0.0, target_kw - actual_kw)
        surplus = max(0.0, actual_kw - target_kw)

        penalty_amount = pr * shortfall * window_hours
        bonus_amount = br * surplus * window_hours

        # Discount for consumers absorbing surplus energy.
        shifted_load = min(surplus, consumption_kw)
        discount_amount = dr * shifted_load * window_hours

        return SettlementResult(
            target_kw=round(target_kw, 3),
            actual_kw=round(actual_kw, 3),
            shortfall_kw=round(shortfall, 3),
            surplus_kw=round(surplus, 3),
            penalty_amount=round(penalty_amount, 2),
            bonus_amount=round(bonus_amount, 2),
            discount_amount=round(discount_amount, 2),
            net_owner=round(bonus_amount - penalty_amount, 2),
            penalty_rate=pr,
            bonus_rate=br,
            discount_rate=dr,
            window_hours=window_hours,
        )

    def settle_day(
        self,
        targets: list[float],
        actuals: list[float],
        consumptions: list[float] | None = None,
        window_hours: float = 1.0,
        penalty_rate: float | None = None,
        bonus_rate: float | None = None,
        discount_rate: float | None = None,
    ) -> dict:
        """Settle a full day (list of intervals) and return aggregates."""
        n = len(targets)
        if consumptions is None:
            consumptions = [0.0] * n

        results = [
            self.settle(
                target_kw=targets[i],
                actual_kw=actuals[i],
                window_hours=window_hours,
                consumption_kw=consumptions[i],
                penalty_rate=penalty_rate,
                bonus_rate=bonus_rate,
                discount_rate=discount_rate,
            )
            for i in range(n)
        ]

        total_penalty = sum(r.penalty_amount for r in results)
        total_bonus = sum(r.bonus_amount for r in results)
        total_discount = sum(r.discount_amount for r in results)
        total_shortfall = sum(r.shortfall_kw for r in results)
        total_surplus = sum(r.surplus_kw for r in results)

        return {
            "intervals": n,
            "total_penalty": round(total_penalty, 2),
            "total_bonus": round(total_bonus, 2),
            "total_discount": round(total_discount, 2),
            "net_owner": round(total_bonus - total_penalty, 2),
            "total_shortfall_kwh": round(total_shortfall * window_hours, 2),
            "total_surplus_kwh": round(total_surplus * window_hours, 2),
            "settlements": [
                {
                    "target_kw": r.target_kw,
                    "actual_kw": r.actual_kw,
                    "shortfall_kw": r.shortfall_kw,
                    "surplus_kw": r.surplus_kw,
                    "penalty": r.penalty_amount,
                    "bonus": r.bonus_amount,
                    "discount": r.discount_amount,
                    "net_owner": r.net_owner,
                }
                for r in results
            ],
        }
