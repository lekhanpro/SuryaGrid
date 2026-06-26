"""RL trainer - REINFORCE policy gradient.

Trains the lightweight numpy policy on either the synthetic digital twin or a
real-data environment built from Open-Meteo archive history.
Run standalone: `python -m app.rl.train`
"""

from __future__ import annotations

import numpy as np

from app.rl.environment import SolarSettlementEnv
from app.rl.policy import RLPolicy, _forward, _init_weights

ACTION_DIM = 3


def _train_env(
    env,
    episodes: int = 500,
    lr: float = 0.003,
    gamma: float = 0.99,
    seed: int = 42,
    verbose: bool = True,
) -> dict:
    """Core REINFORCE loop over a Gymnasium env. Returns metrics + weights."""
    rng = np.random.default_rng(seed)
    w1, b1, w2, b2, log_std = _init_weights(rng)

    best_reward = -float("inf")
    best_weights = (w1.copy(), b1.copy(), w2.copy(), b2.copy(), log_std.copy())
    episode_rewards: list[float] = []

    for ep in range(episodes):
        states, actions, rewards = [], [], []
        state, _ = env.reset(seed=int(rng.integers(0, 1_000_000)))
        done = False

        while not done:
            mean = _forward(state, w1, b1, w2, b2)
            std = np.exp(log_std)
            action = np.clip(
                mean + rng.normal(0, 1, ACTION_DIM).astype(np.float32) * std, -1.0, 1.0
            )
            next_state, reward, terminated, truncated, _ = env.step(action)
            done = terminated or truncated
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            state = next_state

        returns = np.zeros(len(rewards), dtype=np.float32)
        g = 0.0
        for t in reversed(range(len(rewards))):
            g = rewards[t] + gamma * g
            returns[t] = g
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)

        for t in range(len(states)):
            s = states[t]
            a = actions[t]
            mean = _forward(s, w1, b1, w2, b2)
            std = np.exp(log_std)
            err = (a - mean) / (std**2 + 1e-8)
            h = np.tanh(s @ w1 + b1)
            dtanh = 1 - np.tanh(h @ w2 + b2) ** 2

            w2 += (np.outer(h, err * dtanh) * returns[t] * lr).astype(np.float32)
            b2 += (err * dtanh * returns[t] * lr).astype(np.float32)
            log_std += (((a - mean) ** 2 / (std**2 + 1e-8) - 1) * returns[t] * lr * 0.1).astype(
                np.float32
            )

            d_hidden = (err * dtanh) @ w2.T * (1 - h**2)
            w1 += (np.outer(s, d_hidden) * returns[t] * lr).astype(np.float32)
            b1 += (d_hidden * returns[t] * lr).astype(np.float32)

        ep_reward = float(sum(rewards))
        episode_rewards.append(ep_reward)
        if ep_reward > best_reward:
            best_reward = ep_reward
            best_weights = (w1.copy(), b1.copy(), w2.copy(), b2.copy(), log_std.copy())

        if verbose and ep % 50 == 0:
            print(f"  Episode {ep:4d} | reward {ep_reward:8.2f} | best {best_reward:8.2f}")

    policy = RLPolicy.__new__(RLPolicy)
    policy.w1, policy.b1, policy.w2, policy.b2, policy.log_std = best_weights
    policy.trained = True
    policy.save()

    return {
        "policy": policy,
        "best_reward": round(best_reward, 3),
        "mean_reward": round(float(np.mean(episode_rewards[-50:])), 3),
        "episodes": episodes,
    }


def train(episodes: int = 500, verbose: bool = True, **kwargs) -> RLPolicy:
    """Train on the synthetic digital twin."""
    env = SolarSettlementEnv(capacity_kw=50_000.0)
    result = _train_env(env, episodes=episodes, verbose=verbose, **kwargs)
    if verbose:
        print(f"  Done. best={result['best_reward']} mean(last50)={result['mean_reward']}")
    return result["policy"]


def train_real(dataset, capacity_kw: float, episodes: int = 400, verbose: bool = True) -> dict:
    """Train on real historical days. Returns metrics dict."""
    from app.rl.real_environment import RealDataSettlementEnv

    env = RealDataSettlementEnv(dataset=dataset, capacity_kw=capacity_kw)
    result = _train_env(env, episodes=episodes, verbose=verbose)
    return result


if __name__ == "__main__":
    print("=== Suryagrid AI - RL Policy Training (synthetic twin) ===")
    train(episodes=500, verbose=True)
