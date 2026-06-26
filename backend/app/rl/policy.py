"""Lightweight RL policy (numpy-based, no PyTorch dependency).

Implements a simple policy-gradient actor for the 3-action continuous space.
The trained weights are saved as a .npz file and loaded for inference. This
avoids the heavy PyTorch/CUDA stack while demonstrating the RL loop.

For production scale, replace with Stable-Baselines3 PPO on a GPU machine.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

_MODEL_DIR = Path(__file__).parent / "models"
_MODEL_PATH = _MODEL_DIR / "policy_weights.npz"

# Network: state(8) -> hidden(32) -> action(3) with tanh output
HIDDEN = 32
STATE_DIM = 8
ACTION_DIM = 3


def _init_weights(rng: np.random.Generator | None = None):
    rng = rng or np.random.default_rng(42)
    w1 = rng.normal(0, 0.3, (STATE_DIM, HIDDEN)).astype(np.float32)
    b1 = np.zeros(HIDDEN, dtype=np.float32)
    w2 = rng.normal(0, 0.3, (HIDDEN, ACTION_DIM)).astype(np.float32)
    b2 = np.zeros(ACTION_DIM, dtype=np.float32)
    log_std = np.zeros(ACTION_DIM, dtype=np.float32)
    return w1, b1, w2, b2, log_std


def _forward(state: np.ndarray, w1, b1, w2, b2):
    h = np.tanh(state @ w1 + b1)
    return np.tanh(h @ w2 + b2)


class RLPolicy:
    """Load or init a trained policy and predict actions."""

    def __init__(self, model_path: str | Path | None = None):
        path = Path(model_path) if model_path else _MODEL_PATH
        if path.exists():
            data = np.load(path)
            self.w1 = data["w1"]
            self.b1 = data["b1"]
            self.w2 = data["w2"]
            self.b2 = data["b2"]
            self.log_std = data["log_std"]
            self.trained = True
        else:
            self.w1, self.b1, self.w2, self.b2, self.log_std = _init_weights()
            self.trained = False

    def predict(self, state: np.ndarray, deterministic: bool = True) -> np.ndarray:
        """Return action [-1, 1]^3."""
        mean = _forward(state.astype(np.float32), self.w1, self.b1, self.w2, self.b2)
        if deterministic:
            return mean
        std = np.exp(self.log_std)
        return np.clip(mean + np.random.randn(ACTION_DIM).astype(np.float32) * std, -1.0, 1.0)

    def get_rates(self, state: np.ndarray) -> dict:
        """Map the raw action to actual rate values (used by the settlement API)."""
        from app.rl.environment import (
            MAX_BONUS_RATE,
            MAX_DISCOUNT_RATE,
            MAX_PENALTY_RATE,
            MIN_BONUS_RATE,
            MIN_DISCOUNT_RATE,
            MIN_PENALTY_RATE,
        )

        action = self.predict(state, deterministic=True)
        penalty = float(np.clip(8.0 + action[0] * 2.0, MIN_PENALTY_RATE, MAX_PENALTY_RATE))
        bonus = float(np.clip(4.0 + action[1] * 1.5, MIN_BONUS_RATE, MAX_BONUS_RATE))
        discount = float(np.clip(2.0 + action[2] * 1.0, MIN_DISCOUNT_RATE, MAX_DISCOUNT_RATE))
        return {
            "penalty_rate": round(penalty, 2),
            "bonus_rate": round(bonus, 2),
            "discount_rate": round(discount, 2),
            "policy_trained": self.trained,
        }

    def save(self, path: str | Path | None = None):
        dest = Path(path) if path else _MODEL_PATH
        dest.parent.mkdir(parents=True, exist_ok=True)
        np.savez(dest, w1=self.w1, b1=self.b1, w2=self.w2, b2=self.b2, log_std=self.log_std)
