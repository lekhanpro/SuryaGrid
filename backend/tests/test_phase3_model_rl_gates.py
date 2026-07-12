"""Phase 3 - model/RL gate audit.

Locks the honesty guarantees the roadmap requires:
  * every trained supervised model card declares a chronological split (no leakage);
  * the RL policy is NOT production-ready and its card records the missing-real-data
    reason (no policy trained on fabricated rewards);
  * the RL training gate stays blocked while its preconditions are unmet.

Run: python -m pytest tests/test_phase3_model_rl_gates.py -q
"""

import json
from pathlib import Path

CARDS_DIR = Path(__file__).resolve().parents[1] / "models" / "metadata"

# Supervised agent models the platform actually serves.
_SUPERVISED = [
    "solar_forecast_model_card.json",
    "cloud_risk_classifier_card.json",
    "dsm_model_card.json",
    "load_forecast_model_card.json",
]


def _card(name: str) -> dict:
    return json.loads((CARDS_DIR / name).read_text(encoding="utf-8"))


def test_supervised_models_use_chronological_split():
    for name in _SUPERVISED:
        path = CARDS_DIR / name
        if not path.exists():
            continue
        method = str(_card(name).get("train_test_split_method", "")).lower()
        assert "chronological" in method, f"{name}: split '{method}' is not chronological"


def test_rl_policy_is_not_production_ready_with_honest_reason():
    card = _card("rl_policy_card.json")
    assert card["production_ready"] is False
    reason = card.get("reason_if_not_production_ready", "")
    assert "INSUFFICIENT_REAL_ENVIRONMENT_DATA" in reason
    assert card["uses_synthetic_data"] is False  # never trained on fabricated rewards
    assert card["train_rows"] == 0


def test_rl_training_gate_stays_blocked_when_preconditions_unmet():
    from app.ml import train_rl_agent

    result = train_rl_agent.train(data_mode="real")
    # No official tariff + no local load exist in the repo -> must skip honestly.
    assert result["status"] == "SKIPPED"
    assert result["policy_file"] is None
    assert result["preconditions"]["official_tariff_rupee_reward"] is False
    assert "INSUFFICIENT_REAL_ENVIRONMENT_DATA" in result["reason"]


def test_rl_gate_helpers_are_conservative():
    from app.ml import train_rl_agent

    # Tariff/local-load helpers default to False unless real sources exist.
    assert train_rl_agent._tariff_rupees_available() is False
    assert train_rl_agent._local_load_available() is False
