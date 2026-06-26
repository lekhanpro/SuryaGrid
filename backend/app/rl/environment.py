"""Digital twin Gymnasium environment for RL training.

State: [hour_sin, hour_cos, cloud_cover, production_ratio, target_ratio,
        consumption_ratio, current_penalty_rate, current_bonus_rate]

Action (continuous, Box): [delta_penalty_rate, delta_bonus_rate, delta_discount_rate]
  Clipped to [min_rate, max_rate] after applying.

Reward:
  + target_met_bonus (if production >= target)
  + grid_balance (less surplus waste)
  + consumer_satisfaction (discount given)
  - penalty_incurred (owner penalized)
  - deficit (unmet consumption)
"""

from __future__ import annotations

import math

import gymnasium as gym
import numpy as np
from gymnasium import spaces

# Rate bounds (INR/kWh)
MIN_PENALTY_RATE = 2.0
MAX_PENALTY_RATE = 20.0
MIN_BONUS_RATE = 1.0
MAX_BONUS_RATE = 12.0
MIN_DISCOUNT_RATE = 0.5
MAX_DISCOUNT_RATE = 6.0

# Reward weights (from PROJECT_PLAN section 6)
W_TARGET_MET = 2.0
W_GRID_BALANCE = 1.0
W_CONSUMER_SAT = 0.5
W_PENALTY = -1.5
W_DEFICIT = -1.0
W_CURTAILMENT = -0.3


class SolarSettlementEnv(gym.Env):
    """A single-site, single-day digital twin (24 steps per episode)."""

    metadata = {"render_modes": []}

    def __init__(self, capacity_kw: float = 50_000.0, seed: int | None = None):
        super().__init__()
        self.capacity_kw = capacity_kw
        self._rng = np.random.default_rng(seed)

        # State: 8 dimensions, all normalized 0-1 (approximately)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(8,), dtype=np.float32)
        # Action: 3 rate deltas, normalized [-1, 1]
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)

        self._hour = 0
        self._penalty_rate = 8.0
        self._bonus_rate = 4.0
        self._discount_rate = 2.0
        self._cloud_profile: np.ndarray = np.zeros(24)
        self._consumption_profile: np.ndarray = np.zeros(24)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self._hour = 0
        self._penalty_rate = 8.0
        self._bonus_rate = 4.0
        self._discount_rate = 2.0

        # Generate random cloud profile for the day
        self._cloud_profile = self._rng.uniform(5, 80, size=24).astype(np.float32)
        # Generate consumption (commercial-like)
        self._consumption_profile = np.array(
            [self._commercial_load(h) for h in range(24)], dtype=np.float32
        )

        return self._obs(), {}

    def step(self, action: np.ndarray):
        # Apply action: adjust rates
        delta_p, delta_b, delta_d = action.astype(float)
        self._penalty_rate = float(
            np.clip(self._penalty_rate + delta_p * 2.0, MIN_PENALTY_RATE, MAX_PENALTY_RATE)
        )
        self._bonus_rate = float(
            np.clip(self._bonus_rate + delta_b * 1.5, MIN_BONUS_RATE, MAX_BONUS_RATE)
        )
        self._discount_rate = float(
            np.clip(self._discount_rate + delta_d * 1.0, MIN_DISCOUNT_RATE, MAX_DISCOUNT_RATE)
        )

        # Simulate production for this hour
        cloud = self._cloud_profile[self._hour]
        production = self._simulate_production(self._hour, cloud)
        target = self._simulate_target(self._hour)
        consumption = self._consumption_profile[self._hour]

        # Settlement
        shortfall = max(0.0, target - production)
        surplus = max(0.0, production - target)
        deficit = max(0.0, consumption - production)
        shifted_load = min(surplus, consumption)

        penalty_cost = self._penalty_rate * shortfall
        bonus_earned = self._bonus_rate * surplus
        discount_given = self._discount_rate * shifted_load

        # Reward signal
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
        truncated = False

        return (
            self._obs(),
            float(reward),
            terminated,
            truncated,
            {
                "production_kw": production,
                "target_kw": target,
                "consumption_kw": consumption,
                "penalty_rate": self._penalty_rate,
                "bonus_rate": self._bonus_rate,
                "discount_rate": self._discount_rate,
                "penalty_cost": penalty_cost,
                "bonus_earned": bonus_earned,
                "discount_given": discount_given,
            },
        )

    def _obs(self) -> np.ndarray:
        h = min(self._hour, 23)
        hour_sin = (math.sin(2 * math.pi * h / 24) + 1) / 2
        hour_cos = (math.cos(2 * math.pi * h / 24) + 1) / 2
        cloud = self._cloud_profile[h] / 100.0
        prod_ratio = self._simulate_production(h, self._cloud_profile[h]) / self.capacity_kw
        target_ratio = self._simulate_target(h) / self.capacity_kw
        cons_ratio = self._consumption_profile[h] / self.capacity_kw
        pr_norm = (self._penalty_rate - MIN_PENALTY_RATE) / (MAX_PENALTY_RATE - MIN_PENALTY_RATE)
        br_norm = (self._bonus_rate - MIN_BONUS_RATE) / (MAX_BONUS_RATE - MIN_BONUS_RATE)
        return np.array(
            [hour_sin, hour_cos, cloud, prod_ratio, target_ratio, cons_ratio, pr_norm, br_norm],
            dtype=np.float32,
        )

    def _simulate_production(self, hour: int, cloud_pct: float) -> float:
        """Simple bell-curve production with cloud attenuation."""
        if hour < 6 or hour > 18:
            return 0.0
        bell = math.sin(math.pi * (hour - 6) / 12)
        cloud_loss = 1.0 - (cloud_pct / 100.0) * 0.75
        return self.capacity_kw * bell * cloud_loss * 0.85

    def _simulate_target(self, hour: int) -> float:
        """Clear-sky-like target (what the owner committed)."""
        if hour < 6 or hour > 18:
            return 0.0
        bell = math.sin(math.pi * (hour - 6) / 12)
        return self.capacity_kw * bell * 0.7

    def _commercial_load(self, hour: int) -> float:
        """Commercial consumption pattern."""
        base = self.capacity_kw * 0.3
        if 9 <= hour <= 18:
            return base * (0.8 + 0.2 * math.exp(-0.5 * ((hour - 13.5) / 3) ** 2))
        return base * 0.2
