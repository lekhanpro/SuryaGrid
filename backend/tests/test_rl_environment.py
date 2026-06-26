"""Tests for the RL digital twin environment."""

import numpy as np

from app.rl.environment import SolarSettlementEnv


def test_env_resets_and_steps():
    env = SolarSettlementEnv(capacity_kw=50_000)
    obs, info = env.reset(seed=42)
    assert obs.shape == (8,)
    assert all(0.0 <= x <= 1.0 for x in obs)

    action = np.array([0.0, 0.0, 0.0], dtype=np.float32)
    obs2, reward, terminated, truncated, info = env.step(action)
    assert obs2.shape == (8,)
    assert isinstance(reward, float)
    assert not terminated  # first step of 24


def test_episode_terminates_after_24_steps():
    env = SolarSettlementEnv(capacity_kw=10_000)
    env.reset(seed=7)
    for _i in range(24):
        action = np.zeros(3, dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
    assert terminated


def test_action_affects_rates():
    env = SolarSettlementEnv()
    env.reset(seed=1)
    # Push penalty rate up
    action = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    _, _, _, _, info = env.step(action)
    assert info["penalty_rate"] > 8.0  # started at 8, pushed up


def test_info_contains_settlement_data():
    env = SolarSettlementEnv()
    env.reset(seed=99)
    action = np.zeros(3, dtype=np.float32)
    _, _, _, _, info = env.step(action)
    for key in ["production_kw", "target_kw", "consumption_kw", "penalty_cost", "bonus_earned"]:
        assert key in info


if __name__ == "__main__":
    test_env_resets_and_steps()
    test_episode_terminates_after_24_steps()
    test_action_affects_rates()
    test_info_contains_settlement_data()
    print("All RL environment tests PASSED")
