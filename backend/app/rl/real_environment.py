"""RL environment that trains on real historical days.

Each episode samples one real day from the dataset (built from Open-Meteo
archive + pvlib) and steps hour by hour. The agent sets penalty/bonus/discount
rates; reward reflects grid balance, fairness and cost using real production.
"""

from __future__ import annotations

import math

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from app.rl.environment import (
    MAX_BONUS_RATE,
    MAX_DISCOUNT_RATE,
    MAX_PENALTY_RATE,
    MIN_BONUS_RATE,
    MIN_DISCOUNT_RATE,
    MIN_PENALTY_RATE,
    W_CONSUMER_SAT,
    W_CURTAILMENT,
    W_DEFICIT,
    W_GRID_BALANCE,
    W_PENALTY,
    W_TARGET_MET,
)


class RealDataSettlementEnv(gym.Env):
    """Digital twin driven by real historical production/target/consumption."""

    metadata = {"render_modes": []}

    def __init__(self, dataset: list[dict], capacity_kw: float, seed: int | None = None):
        super().__init__()
        if not dataset:
            raise ValueError("RealDataSettlementEnv requires a non-empty dataset")
        self.dataset = dataset
        self.capacity_kw = max(capacity_kw, 1.0)
        self._rng = np.random.default_rng(seed)

        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(8,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        self._hour = 0
        self._day: dict | None = None
        self._penalty_rate = 8.0
        self._bonus_rate = 4.0
        self._discount_rate = 2.0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._day = self.dataset[int(self._rng.integers(0, len(self.dataset)))]
        self._hour = 0
        self._penalty_rate = 8.0
        self._bonus_rate = 4.0
        self._discount_rate = 2.0
        return self._obs(), {}

    def step(self, action: np.ndarray):
        dp, db, dd = action.astype(float)
        self._penalty_rate = float(
            np.clip(self._penalty_rate + dp * 2.0, MIN_PENALTY_RATE, MAX_PENALTY_RATE)
        )
        self._bonus_rate = float(
            np.clip(self._bonus_rate + db * 1.5, MIN_BONUS_RATE, MAX_BONUS_RATE)
        )
        self._discount_rate = float(
            np.clip(self._discount_rate + dd * 1.0, MIN_DISCOUNT_RATE, MAX_DISCOUNT_RATE)
        )

        h = self._hour
        production = float(self._day["production_kw"][h])
        target = float(self._day["target_kw"][h])
        consumption = float(self._day["consumption_kw"][h])

        shortfall = max(0.0, target - production)
        surplus = max(0.0, production - target)
        deficit = max(0.0, consumption - production)
        shifted_load = min(surplus, consumption)

        penalty_cost = self._penalty_rate * shortfall

        target_met = 1.0 if production >= target else 0.0
        grid_balance = 1.0 - min(1.0, abs(surplus - deficit) / max(self.capacity_kw * 0.1, 1.0))
        consumer_sat = shifted_load / max(consumption, 1.0)

        reward = (
            W_TARGET_MET * target_met
            + W_GRID_BALANCE * grid_balance
            + W_CONSUMER_SAT * consumer_sat
            + W_PENALTY * (penalty_cost / 1000.0)
            + W_DEFICIT * (deficit / self.capacity_kw)
            + W_CURTAILMENT * (max(0.0, surplus - consumption) / self.capacity_kw)
        )

        self._hour += 1
        terminated = self._hour >= 24
        return (
            self._obs(),
            float(reward),
            terminated,
            False,
            {
                "production_kw": production,
                "target_kw": target,
                "consumption_kw": consumption,
                "penalty_rate": self._penalty_rate,
                "bonus_rate": self._bonus_rate,
                "discount_rate": self._discount_rate,
            },
        )

    def _obs(self) -> np.ndarray:
        h = min(self._hour, 23)
        day = self._day
        hour_sin = (math.sin(2 * math.pi * h / 24) + 1) / 2
        hour_cos = (math.cos(2 * math.pi * h / 24) + 1) / 2
        cloud = float(day["cloud"][h]) / 100.0
        prod_ratio = float(day["production_kw"][h]) / self.capacity_kw
        target_ratio = float(day["target_kw"][h]) / self.capacity_kw
        cons_ratio = float(day["consumption_kw"][h]) / self.capacity_kw
        pr_norm = (self._penalty_rate - MIN_PENALTY_RATE) / (MAX_PENALTY_RATE - MIN_PENALTY_RATE)
        br_norm = (self._bonus_rate - MIN_BONUS_RATE) / (MAX_BONUS_RATE - MIN_BONUS_RATE)
        return np.array(
            [hour_sin, hour_cos, cloud, prod_ratio, target_ratio, cons_ratio, pr_norm, br_norm],
            dtype=np.float32,
        ).clip(0.0, 1.0)
