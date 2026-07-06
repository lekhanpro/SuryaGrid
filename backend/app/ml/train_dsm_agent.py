"""Train the DSM agent - a deviation-breach-risk classifier + a framework rules engine.

Honest scope:
  * Classifier: predicts whether solar injection will breach the +/-15% deviation band
    (a modelling parameter), from weather + the day-ahead scheduled GHI. Trained on REAL
    Bengaluru coordinate history.
  * Rules engine (JSON): maps a deviation band to a FRAMEWORK-ONLY recommendation. It does
    NOT compute rupee penalties - official CERC/KERC rupee rates are market-linked and
    pending (NEEDS_OFFICIAL_TARIFF_SOURCE, see docs/tariff_and_dsm_source_verification.md).
"""

from __future__ import annotations

import argparse
import json
import sys

from sklearn.ensemble import RandomForestClassifier

from app.ml import provenance as prov
from app.ml import train_utils as tu
from app.ml.build_ml_datasets import DSM_DEVIATION_BAND_PERCENT, F_DSM
from app.ml.provenance import REAL_COORDINATE_BASED

MODEL_PKL = "dsm_classifier.pkl"
RULES_JSON = "dsm_rules_engine.json"  # written to backend/models/trained/
CARD_JSON = "dsm_model_card.json"

FEATURES = [
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "cloud_cover_percent",
    "relative_humidity_percent",
    "wind_speed_mps",
    "surface_pressure_hpa",
    "precipitation_mm",
    "scheduled_ghi_wm2",
]
TARGET = "breach_risk"
ORDER_COL = "timestamp_local"
MIN_ROWS = 1000
F1_PRODUCTION_THRESHOLD = 0.55


def _write_rules_engine() -> str:
    """Framework-only DSM rules engine. NO rupee values."""
    rules = {
        "engine": "suryagrid_dsm_framework",
        "version": "1.7",
        "emits_rupee_values": False,
        "band_definition_percent": DSM_DEVIATION_BAND_PERCENT,
        "band_source_label": "FALLBACK_DEFAULT",
        "tariff_status": "NEEDS_OFFICIAL_TARIFF_SOURCE",
        "tariff_reference_file": "backend/data/ml/tariff_dsm_rules_official_or_pending.json",
        "bands": {
            "WITHIN_BAND": {
                "condition": "abs(deviation_percent) <= band",
                "recommendation": "No action required; injection within the modelled band.",
                "rupee_charge": None,
            },
            "OVER_INJECTION": {
                "condition": "deviation_percent > band",
                "recommendation": "Actual injection exceeds schedule beyond the band. Revise "
                "the day-ahead schedule upward / curtail if instructed by SLDC. Rupee "
                "settlement pending official CERC/KERC rate.",
                "rupee_charge": None,
            },
            "UNDER_INJECTION": {
                "condition": "deviation_percent < -band",
                "recommendation": "Actual injection below schedule beyond the band. Revise "
                "the day-ahead schedule downward / arrange balancing. Rupee settlement "
                "pending official CERC/KERC rate.",
                "rupee_charge": None,
            },
        },
        "regulatory_authorities": ["CERC (DSM Regulations, 2024)", "KERC (F&S&DSM Regulations)"],
    }
    path = prov.trained_models_dir() / RULES_JSON
    prov.save_json(rules, path)
    return str(path)


def train(data_mode: str = "real") -> dict:
    rules_path = _write_rules_engine()
    df = tu.load_training_frame(F_DSM)
    if df is None or len(df) < MIN_ROWS or df[TARGET].nunique() < 2:
        return _skip("dsm training data missing, too small, or single-class", rules_path)

    x_tr, x_te, y_tr, y_te, split = tu.chronological_split(
        df, FEATURES, TARGET, order_col=ORDER_COL
    )
    clf = RandomForestClassifier(
        n_estimators=250, max_depth=16, class_weight="balanced",
        random_state=tu.RANDOM_STATE, n_jobs=-1,
    )
    clf.fit(x_tr, y_tr)
    proba = clf.predict_proba(x_te)[:, 1]
    metrics = tu.classification_metrics(y_te, clf.predict(x_te), proba)

    bundle = {
        "estimator": clf,
        "feature_columns": FEATURES,
        "target": TARGET,
        "prediction_type": "dsm_deviation_breach_risk",
        "unit": "probability",
        "model_type": "random_forest_classifier",
        "band_definition_percent": DSM_DEVIATION_BAND_PERCENT,
        "emits_rupee_values": False,
    }
    pkl_path = tu.save_pkl(bundle, MODEL_PKL)

    production_ready = metrics["f1"] >= F1_PRODUCTION_THRESHOLD
    card = prov.ModelCard(
        model_name="dsm_classifier",
        training_data_files=[F_DSM, "bengaluru_weather_solar_history.parquet"],
        training_data_sources=[
            {
                "name": "Open-Meteo Historical Weather Archive (Bengaluru)",
                "url": "https://open-meteo.com/en/docs/historical-weather-api",
                "label": REAL_COORDINATE_BASED,
            },
            {
                "name": "KERC/CERC DSM regulatory framework (structure only, no rupees)",
                "url": "https://kerc.karnataka.gov.in/",
                "label": prov.NEEDS_OFFICIAL_SOURCE,
            },
        ],
        training_geography="Bengaluru, Karnataka, India (coordinate-based)",
        target_geography="Bengaluru, Karnataka, India",
        local_data_available=True,
        domain_shift_risk="LOW",
        features=FEATURES,
        target=TARGET,
        train_rows=split["n_train"],
        test_rows=split["n_test"],
        train_test_split_method="chronological_80_20",
        metrics={"breach_rate": round(float(df[TARGET].mean()), 4), **metrics},
        limitations=[
            "Predicts breach of a +/-15% MODELLING band, not an official KERC/CERC band.",
            "Does NOT compute rupee DSM charges. Official rates are market-linked and pending "
            "(NEEDS_OFFICIAL_TARIFF_SOURCE).",
            "'Scheduled' injection is a day-ahead persistence proxy on irradiance, not a metered "
            "SLDC schedule. No substation-level DSM (no real capacity/feeder-load data).",
        ],
        production_ready=production_ready,
        reason_if_not_production_ready=(
            None
            if production_ready
            else f"F1 {metrics['f1']} < {F1_PRODUCTION_THRESHOLD}; and rupee settlement pending "
            "official tariff source."
        ),
        uses_synthetic_data=False,
        synthetic_percentage=0.0,
        uses_non_local_data=False,
        non_local_data_percentage=0.0,
        prediction_type="dsm_deviation_breach_risk",
        model_type="random_forest_classifier",
        notes=[
            f"rules_engine={rules_path}",
            "emits_rupee_values=false (framework-only DSM recommendations).",
        ],
    )
    card_path = card.save(CARD_JSON)

    print(f"[train_dsm_agent] TRAINED breach classifier | F1={metrics['f1']} "
          f"AUC={metrics.get('roc_auc')} | rupees=OFF | production_ready={production_ready}")
    return {
        "agent": "dsm",
        "status": "TRAINED",
        "model_file": str(pkl_path),
        "rules_engine": rules_path,
        "model_card": str(card_path),
        "prediction_type": "dsm_deviation_breach_risk",
        "metrics": metrics,
        "production_ready": production_ready,
        "emits_rupee_values": False,
        "rows": split["n"],
    }


def _skip(reason: str, rules_path: str) -> dict:
    print(f"[train_dsm_agent] SKIP classifier: {reason} (rules engine still written)")
    prov.ModelCard(
        model_name="dsm_classifier",
        target="breach_risk",
        production_ready=False,
        reason_if_not_production_ready=reason,
        prediction_type="dsm_deviation_breach_risk",
        notes=[f"rules_engine={rules_path}", "emits_rupee_values=false"],
    ).save(CARD_JSON)
    return {"agent": "dsm", "status": "SKIPPED", "reason": reason, "rules_engine": rules_path}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    print(json.dumps(train(args.data_mode), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
