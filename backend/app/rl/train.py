"""RL trainer - REINFORCE policy gradient on the digital twin.

Trains the lightweight numpy policy on the SolarSettlementEnv.
Run standalone: `python -m app.rl.train`
"""

from __future__ import annotations

import numpy as np

from app.rl.environment import SolarSettlementEnv
from app.rl.policy import (
    ACTION_DIM,
    RLPolicy,
    _forward,
    _init_weights,
)


def train(
    episodes: int = 500,
    lr: float = 0.003,
    gamma: float = 0.99,
    seed: int = 42,
    verbose: bool = True,
) -> RLPolicy:
    """Train with REINFORCE and return the policy."""
    rng = np.random.default_rng(seed)
    w1, b1, w2, b2, log_std = _init_weights(rng)
    env = SolarSettlementEnv(capacity_kw=50_000.0)

    best_reward = -float("inf")
    best_weights = (w1.copy(), b1.copy(), w2.copy(), b2.copy(), log_std.copy())

    for ep in range(episodes):
        states, actions, rewards = [], [], []
        state, _ = env.reset(seed=int(rng.integers(0, 100_000)))
        done = False

        while not done:
            # Forward pass
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

        # Compute discounted returns
        returns = np.zeros(len(rewards), dtype=np.float32)
        g = 0.0
        for t in reversed(range(len(rewards))):
            g = rewards[t] + gamma * g
            returns[t] = g
        # Normalize
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)

        # Policy gradient update
        for t in range(len(states)):
            s = states[t]
            a = actions[t]
            mean = _forward(s, w1, b1, w2, b2)
            std = np.exp(log_std)
            # d log_pi / d params (simplified REINFORCE)
            err = (a - mean) / (std**2 + 1e-8)

            # Hidden layer
            h = np.tanh(s @ w1 + b1)
            dtanh = 1 - np.tanh(h @ w2 + b2) ** 2  # d_tanh for output

            # Gradient for w2, b2
            dw2 = np.outer(h, err * dtanh) * returns[t] * lr
            db2 = err * dtanh * returns[t] * lr

            # Gradient for log_std
            d_log_std = ((a - mean) ** 2 / (std**2 + 1e-8) - 1) * returns[t] * lr * 0.1

            w2 += dw2.astype(np.float32)
            b2 += db2.astype(np.float32)
            log_std += d_log_std.astype(np.float32)

            # Gradient for w1, b1 (backprop through tanh)
            d_hidden = (err * dtanh) @ w2.T * (1 - h**2)
            dw1 = np.outer(s, d_hidden) * returns[t] * lr
            db1 = d_hidden * returns[t] * lr
            w1 += dw1.astype(np.float32)
            b1 += db1.astype(np.float32)

        ep_reward = sum(rewards)
        if ep_reward > best_reward:
            best_reward = ep_reward
            best_weights = (w1.copy(), b1.copy(), w2.copy(), b2.copy(), log_std.copy())

        if verbose and ep % 50 == 0:
            print(f"  Episode {ep:4d} | reward {ep_reward:.2f} | best {best_reward:.2f}")

    # Build policy from best weights
    policy = RLPolicy.__new__(RLPolicy)
    policy.w1, policy.b1, policy.w2, policy.b2, policy.log_std = best_weights
    policy.trained = True
    policy.save()
    if verbose:
        print(f"  Training complete. Best episode reward: {best_reward:.2f}")
        print("  Model saved.")
    return policy


if __name__ == "__main__":
    print("=== Suryagrid AI - RL Policy Training ===")
    train(episodes=500, verbose=True)
