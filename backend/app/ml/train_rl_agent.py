"""Train the RL agent - ONLY if a real, sourced environment exists.

An honest RL environment for DSM optimisation needs ALL of:
  1. Real local (Bengaluru/Karnataka) load time series.
  2. Real Bengaluru solar/weather time series (we have this).
  3. Official tariff / DSM rupee terms for the reward (we do NOT - market-linked & pending).
  4. Sourced action constraints and reward terms.

Because the official rupee reward terms are absent (NEEDS_OFFICIAL_TARIFF_SOURCE) and
local load is absent, we refuse to fabricate a reward environment. No rl_policy.zip is
written; a model card records production_ready=false with the honest reason.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.ml import provenance as prov
from app.ml.build_ml_datasets import F_LOAD_HISTORY, F_WEATHER
from app.ml.provenance import REAL_COORDINATE_BASED

CARD_JSON = "rl_policy_card.json"
POLICY_ZIP = "rl_policy.zip"


def _tariff_rupees_available() -> bool:
    path = prov.ml_data_dir() / "tariff_dsm_rules_official_or_pending.json"
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    return bool(data.get("meta", {}).get("emits_rupee_values", False))


def _local_load_available() -> bool:
    hist = prov.read_parquet(F_LOAD_HISTORY)
    if hist is None or hist.empty:
        return False
    scope = str(hist.get("region_scope").iloc[0]).lower() if "region_scope" in hist else ""
    return "bengaluru" in scope or "karnataka" in scope


def train(data_mode: str = "real") -> dict:
    weather = prov.read_parquet(F_WEATHER)
    have_weather = weather is not None and len(weather) > 0
    have_local_load = _local_load_available()
    have_official_tariff = _tariff_rupees_available()

    preconditions = {
        "real_bengaluru_weather": have_weather,
        "real_local_load": have_local_load,
        "official_tariff_rupee_reward": have_official_tariff,
    }
    ready = all(preconditions.values())

    if not ready:
        missing = [k for k, v in preconditions.items() if not v]
        reason = (
            "INSUFFICIENT_REAL_ENVIRONMENT_DATA: missing " + ", ".join(missing) + ". "
            "An RL reward requires official DSM/tariff rupee terms and real local load; "
            "these are pending (NEEDS_OFFICIAL_TARIFF_SOURCE) / not local. Refusing to "
            "synthesise a reward environment or a fake policy."
        )
        _write_card(preconditions, reason, ready=False)
        print(f"[train_rl_agent] SKIP (honest): {reason}")
        return {
            "agent": "rl",
            "status": "SKIPPED",
            "reason": reason,
            "preconditions": preconditions,
            "policy_file": None,
        }

    # Not reached in Phase 1.7 (kept for when a sourced environment exists).
    _write_card(preconditions, None, ready=True)
    return {"agent": "rl", "status": "READY_BUT_NOT_IMPLEMENTED", "preconditions": preconditions}


def _write_card(preconditions: dict, reason: str | None, *, ready: bool) -> None:
    prov.ModelCard(
        model_name="rl_policy",
        training_data_files=[F_WEATHER],
        training_data_sources=[
            {
                "name": "Open-Meteo Bengaluru weather (environment state, partial)",
                "url": "https://open-meteo.com/en/docs/historical-weather-api",
                "label": REAL_COORDINATE_BASED,
            },
            {
                "name": "Official DSM/tariff rupee reward terms",
                "url": "docs/DSM_RULE_SOURCES.md",
                "label": prov.NEEDS_OFFICIAL_SOURCE,
                "status": "absent",
            },
        ],
        training_geography="Bengaluru, Karnataka, India",
        target_geography="Bengaluru, Karnataka, India",
        local_data_available=preconditions.get("real_local_load", False),
        domain_shift_risk="HIGH",
        features=["solar_state", "load_state", "tariff_reward(missing)"],
        target="dsm_dispatch_policy",
        train_rows=0,
        test_rows=0,
        train_test_split_method="n/a (not trained)",
        metrics={},
        limitations=[
            "No RL policy trained: reward requires official rupee DSM/tariff terms + real local load.",
            "Training a policy on fabricated rewards would produce misleading dispatch actions.",
        ],
        production_ready=ready,
        reason_if_not_production_ready=reason,
        uses_synthetic_data=False,
        synthetic_percentage=0.0,
        uses_non_local_data=False,
        non_local_data_percentage=0.0,
        prediction_type="rl_dispatch_policy",
        model_type="none",
        notes=[f"preconditions={preconditions}", "policy_zip_written=false"],
    ).save(CARD_JSON)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    print(json.dumps(train(args.data_mode), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
