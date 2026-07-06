"""Train the cloud agent - an irradiance-drop-risk classifier for Bengaluru.

Label: irradiance_drop_risk = 1 when the clearness index kt = GHI / clearsky_GHI
(pvlib Ineichen) falls below 0.5 during daylight hours (clearsky_GHI > 50 W/m2).
This is an IRRADIANCE drop, not a PV-output drop (no real PV dataset exists).
Threshold logic is documented in docs/formulas.md.
"""

from __future__ import annotations

import argparse
import json
import sys

from sklearn.ensemble import RandomForestClassifier

from app.ml import provenance as prov
from app.ml import train_utils as tu
from app.ml.build_ml_datasets import CLEARNESS_DROP_THRESHOLD, F_CLOUD
from app.ml.provenance import REAL_COORDINATE_BASED

MODEL_PKL = "cloud_risk_classifier.pkl"
CARD_JSON = "cloud_risk_classifier_card.json"

FEATURES = [
    "hour_sin",
    "hour_cos",
    "doy_sin",
    "doy_cos",
    "cloud_cover_percent",
    "relative_humidity_percent",
    "temperature_c",
    "wind_speed_mps",
    "surface_pressure_hpa",
    "precipitation_mm",
]
TARGET = "irradiance_drop_risk"
ORDER_COL = "timestamp_local"
MIN_ROWS = 1000
F1_PRODUCTION_THRESHOLD = 0.5


def train(data_mode: str = "real") -> dict:
    df = tu.load_training_frame(F_CLOUD)
    if df is None or len(df) < MIN_ROWS:
        return _skip(f"cloud training data missing or < {MIN_ROWS} rows")
    if df[TARGET].nunique() < 2:
        return _skip("cloud target has a single class; cannot train a classifier honestly")

    x_tr, x_te, y_tr, y_te, split = tu.chronological_split(
        df, FEATURES, TARGET, order_col=ORDER_COL
    )
    clf = RandomForestClassifier(
        n_estimators=250,
        max_depth=16,
        class_weight="balanced",
        random_state=tu.RANDOM_STATE,
        n_jobs=-1,
    )
    clf.fit(x_tr, y_tr)
    proba = clf.predict_proba(x_te)[:, 1]
    metrics = tu.classification_metrics(y_te, clf.predict(x_te), proba)

    bundle = {
        "estimator": clf,
        "feature_columns": FEATURES,
        "target": TARGET,
        "prediction_type": "irradiance_drop_risk",
        "unit": "probability",
        "model_type": "random_forest_classifier",
        "clearness_drop_threshold": CLEARNESS_DROP_THRESHOLD,
    }
    pkl_path = tu.save_pkl(bundle, MODEL_PKL)

    production_ready = metrics["f1"] >= F1_PRODUCTION_THRESHOLD
    card = prov.ModelCard(
        model_name="cloud_risk_classifier",
        training_data_files=[F_CLOUD, "bengaluru_weather_solar_history.parquet"],
        training_data_sources=[
            {
                "name": "Open-Meteo Historical Weather Archive",
                "url": "https://open-meteo.com/en/docs/historical-weather-api",
                "label": REAL_COORDINATE_BASED,
                "geography": "Bengaluru coordinates (12.9716, 77.5946)",
            },
            {
                "name": "pvlib Ineichen clear-sky (label basis)",
                "url": "https://pvlib-python.readthedocs.io/",
                "label": prov.ESTIMATED_FROM_REAL,
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
        metrics={"positive_rate": round(float(df[TARGET].mean()), 4), **metrics},
        limitations=[
            "Predicts IRRADIANCE drop risk (clearness index kt<0.5), not PV-output drop.",
            f"Label derived from pvlib clear-sky; threshold kt<{CLEARNESS_DROP_THRESHOLD} is a "
            "documented modelling choice (docs/formulas.md), not a regulatory definition.",
            "Only daylight hours (clearsky GHI > 50 W/m2) are labelled/trained.",
        ],
        production_ready=production_ready,
        reason_if_not_production_ready=(
            None if production_ready else f"F1 {metrics['f1']} < {F1_PRODUCTION_THRESHOLD}."
        ),
        uses_synthetic_data=False,
        synthetic_percentage=0.0,
        uses_non_local_data=False,
        non_local_data_percentage=0.0,
        prediction_type="irradiance_drop_risk",
        model_type="random_forest_classifier",
    )
    card_path = card.save(CARD_JSON)

    print(f"[train_cloud_agent] TRAINED | F1={metrics['f1']} AUC={metrics.get('roc_auc')} "
          f"| production_ready={production_ready}")
    return {
        "agent": "cloud",
        "status": "TRAINED",
        "model_file": str(pkl_path),
        "model_card": str(card_path),
        "prediction_type": "irradiance_drop_risk",
        "metrics": metrics,
        "production_ready": production_ready,
        "rows": split["n"],
    }


def _skip(reason: str) -> dict:
    print(f"[train_cloud_agent] SKIP: {reason}")
    prov.ModelCard(
        model_name="cloud_risk_classifier",
        target="irradiance_drop_risk",
        production_ready=False,
        reason_if_not_production_ready=reason,
        prediction_type="irradiance_drop_risk",
    ).save(CARD_JSON)
    return {"agent": "cloud", "status": "SKIPPED", "reason": reason}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--region", default="bengaluru")
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    print(json.dumps(train(args.data_mode), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
