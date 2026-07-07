"""Train models from the REAL Kaggle training files (Phase 1.7).

Produces kaggle_-prefixed model artifacts + full model cards WITHOUT overwriting the
existing Open-Meteo Phase 1.7 models:

  * kaggle_pv_ac_model.pkl                 REAL_INDIA   PV AC power (irradiation+temp)
  * kaggle_solar_irradiance_bengaluru_model.pkl  REAL_BENGALURU  GHI forecast
  * kaggle_cloud_risk_bengaluru_model.pkl  REAL_BENGALURU  irradiance-drop classifier
  * kaggle_load_forecast_model.pkl         REAL_INDIA   national demand (not local)

Honesty: India-national/plant data is real but not Bengaluru-local -> such models are
marked production_ready=false with an explicit reason. No synthetic data is used.

    python -m app.ml.train_from_kaggle --data-mode real
"""

from __future__ import annotations

import argparse
import json
import sys

from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)

from app.ml import provenance as prov
from app.ml import train_utils as tu

R2_PROD = 0.75
F1_PROD = 0.5


def _src(slug, label, geo):
    return {"name": f"Kaggle: {slug}", "url": f"https://www.kaggle.com/datasets/{slug}",
            "label": label, "geography": geo}


def train_pv(data_mode: str) -> dict:
    df = tu.load_training_frame("kaggle_pv_ac_training.parquet")
    if df is None or len(df) < 1000:
        return {"agent": "kaggle_pv", "status": "SKIPPED", "reason": "no PV training data"}
    feats = ["irradiation", "ambient_temperature_c", "module_temperature_c", "hour_sin", "hour_cos"]
    xtr, xte, ytr, yte, sp = tu.chronological_split(df, feats, "ac_power", order_col="timestamp")
    est = HistGradientBoostingRegressor(max_iter=300, random_state=tu.RANDOM_STATE)
    est.fit(xtr, ytr)
    m = tu.regression_metrics(yte, est.predict(xte))
    tu.save_pkl({"estimator": est, "feature_columns": feats, "target": "ac_power",
                 "prediction_type": "pv_ac_power", "unit": "kW", "model_type": "hist_gradient_boosting"},
                "kaggle_pv_ac_model.pkl")
    prov.ModelCard(
        model_name="kaggle_pv_ac_model",
        training_data_files=["kaggle_pv_ac_training.parquet", "kaggle_pv_generation_processed.parquet"],
        training_data_sources=[_src("anikannal/solar-power-generation-data", prov.REAL_INDIA,
                                    "India (2 plants, site unspecified)")],
        training_geography="India (plant-level, unspecified site)",
        target_geography="Bengaluru, Karnataka, India",
        local_data_available=False, domain_shift_risk="MEDIUM",
        features=feats, target="ac_power", train_rows=sp["n_train"], test_rows=sp["n_test"],
        metrics={"chosen_model": "hist_gradient_boosting", **m},
        limitations=[
            "Real Indian PV plant data but NOT Bengaluru-local; 34-day window (May-Jun 2020), 2 plants.",
            "IRRADIATION is a normalised sensor value (not W/m2); AC target is per-inverter kW.",
            "Plant_1 DC_POWER has a ~10x scaling anomaly; AC power (modelled here) is unaffected.",
        ],
        production_ready=False,
        reason_if_not_production_ready="REAL_INDIA plant-specific, short 34-day window, not validated "
        "for a Bengaluru site (domain shift). Usable as a real PV AC baseline / pretraining.",
        uses_synthetic_data=False, synthetic_percentage=0.0,
        uses_non_local_data=False, non_local_data_percentage=0.0,
        data_mode=data_mode, prediction_type="pv_ac_power", model_type="hist_gradient_boosting",
    ).save("kaggle_pv_ac_model_card.json")
    print(f"[train_from_kaggle] PV AC: R2={m['r2']} RMSE={m['rmse']} kW (REAL_INDIA, prod=False)")
    return {"agent": "kaggle_pv", "status": "TRAINED", "metrics": m, "production_ready": False,
            "geography": "REAL_INDIA", "rows": sp["n"]}


def train_solar(data_mode: str) -> dict:
    df = tu.load_training_frame("kaggle_solar_irradiance_training.parquet")
    if df is None or len(df) < 1000:
        return {"agent": "kaggle_solar", "status": "SKIPPED", "reason": "no Bengaluru GHI data"}
    feats = ["hour_sin", "hour_cos", "doy_sin", "doy_cos", "temperature_c", "pressure_kpa",
             "precip_mm", "solar_zenith_deg"]
    xtr, xte, ytr, yte, sp = tu.chronological_split(df, feats, "ghi_wm2", order_col="timestamp")
    cand = {"random_forest": RandomForestRegressor(n_estimators=200, max_depth=18,
            random_state=tu.RANDOM_STATE, n_jobs=-1),
            "hist_gradient_boosting": HistGradientBoostingRegressor(max_iter=300,
            random_state=tu.RANDOM_STATE)}
    best_n, best_e, best_m = None, None, None
    for n, e in cand.items():
        e.fit(xtr, ytr)
        mm = tu.regression_metrics(yte, e.predict(xte))
        if best_m is None or mm["rmse"] < best_m["rmse"]:
            best_n, best_e, best_m = n, e, mm
    tu.save_pkl({"estimator": best_e, "feature_columns": feats, "target": "ghi_wm2",
                 "prediction_type": "irradiance_forecast", "unit": "W/m2", "model_type": best_n},
                "kaggle_solar_irradiance_bengaluru_model.pkl")
    prod = best_m["r2"] >= R2_PROD
    prov.ModelCard(
        model_name="kaggle_solar_irradiance_bengaluru_model",
        training_data_files=["kaggle_solar_irradiance_training.parquet", "kaggle_solar_processed.parquet"],
        training_data_sources=[_src("meenakshihihihihi/time-series-solar-irradiance-for-indian-cities",
                                    prov.REAL_BENGALURU, "Bengaluru (NASA-POWER-derived)")],
        training_geography="Bengaluru, Karnataka, India", target_geography="Bengaluru, Karnataka, India",
        local_data_available=True, domain_shift_risk="LOW",
        features=feats, target="ghi_wm2", train_rows=sp["n_train"], test_rows=sp["n_test"],
        metrics={"chosen_model": best_n, **best_m},
        limitations=[
            "Predicts GHI (W/m2), not PV output. Bengaluru city extract (NASA POWER); -999 fill dropped.",
            "Separate from the Open-Meteo Bengaluru model, which remains the primary irradiance model.",
        ],
        production_ready=prod,
        reason_if_not_production_ready=None if prod else f"R2 {best_m['r2']} < {R2_PROD}.",
        uses_synthetic_data=False, synthetic_percentage=0.0,
        uses_non_local_data=False, non_local_data_percentage=0.0,
        data_mode=data_mode, prediction_type="irradiance_forecast", model_type=best_n,
    ).save("kaggle_solar_irradiance_bengaluru_model_card.json")
    print(f"[train_from_kaggle] Bengaluru GHI: R2={best_m['r2']} RMSE={best_m['rmse']} (REAL_BENGALURU, prod={prod})")
    return {"agent": "kaggle_solar", "status": "TRAINED", "metrics": best_m,
            "production_ready": prod, "geography": "REAL_BENGALURU", "rows": sp["n"]}


def train_cloud(data_mode: str) -> dict:
    df = tu.load_training_frame("kaggle_cloud_training.parquet")
    if df is None or len(df) < 500 or df["irradiance_drop_risk"].nunique() < 2:
        return {"agent": "kaggle_cloud", "status": "SKIPPED", "reason": "insufficient/one-class cloud data"}
    feats = ["hour_sin", "hour_cos", "doy_sin", "doy_cos", "temperature_c", "pressure_kpa", "precip_mm"]
    xtr, xte, ytr, yte, sp = tu.chronological_split(df, feats, "irradiance_drop_risk", order_col="timestamp")
    clf = RandomForestClassifier(n_estimators=250, max_depth=16, class_weight="balanced",
                                 random_state=tu.RANDOM_STATE, n_jobs=-1)
    clf.fit(xtr, ytr)
    m = tu.classification_metrics(yte, clf.predict(xte), clf.predict_proba(xte)[:, 1])
    tu.save_pkl({"estimator": clf, "feature_columns": feats, "target": "irradiance_drop_risk",
                 "prediction_type": "irradiance_drop_risk", "unit": "probability",
                 "model_type": "random_forest_classifier"}, "kaggle_cloud_risk_bengaluru_model.pkl")
    prod = m["f1"] >= F1_PROD
    prov.ModelCard(
        model_name="kaggle_cloud_risk_bengaluru_model",
        training_data_files=["kaggle_cloud_training.parquet"],
        training_data_sources=[_src("meenakshihihihihi/time-series-solar-irradiance-for-indian-cities",
                                    prov.REAL_BENGALURU, "Bengaluru (NASA-POWER-derived)")],
        training_geography="Bengaluru, Karnataka, India", target_geography="Bengaluru, Karnataka, India",
        local_data_available=True, domain_shift_risk="LOW",
        features=feats, target="irradiance_drop_risk", train_rows=sp["n_train"], test_rows=sp["n_test"],
        metrics={"positive_rate": round(float(df["irradiance_drop_risk"].mean()), 4), **m},
        limitations=[
            "Label = real clearness index (ALLSKY_KT) < 0.5 during daylight; irradiance drop, not PV drop.",
            "Bengaluru NASA-POWER extract; daylight rows only.",
        ],
        production_ready=prod,
        reason_if_not_production_ready=None if prod else f"F1 {m['f1']} < {F1_PROD}.",
        uses_synthetic_data=False, synthetic_percentage=0.0,
        uses_non_local_data=False, non_local_data_percentage=0.0,
        data_mode=data_mode, prediction_type="irradiance_drop_risk", model_type="random_forest_classifier",
    ).save("kaggle_cloud_risk_bengaluru_model_card.json")
    print(f"[train_from_kaggle] Bengaluru cloud: F1={m['f1']} AUC={m.get('roc_auc')} (REAL_BENGALURU, prod={prod})")
    return {"agent": "kaggle_cloud", "status": "TRAINED", "metrics": m, "production_ready": prod,
            "geography": "REAL_BENGALURU", "rows": sp["n"]}


def train_load(data_mode: str) -> dict:
    df = tu.load_training_frame("kaggle_load_training.parquet")
    if df is None or len(df) < 1000:
        prov.ModelCard(model_name="kaggle_load_forecast_model", target="national_demand_mw",
                       training_geography="India", local_data_available=False, domain_shift_risk="HIGH",
                       production_ready=False,
                       reason_if_not_production_ready="INSUFFICIENT_REAL_KAGGLE_LOAD_DATA",
                       data_mode=data_mode, prediction_type="load_forecast").save(
            "kaggle_load_forecast_model_card.json")
        return {"agent": "kaggle_load", "status": "SKIPPED", "reason": "INSUFFICIENT_REAL_KAGGLE_LOAD_DATA"}
    feats = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos", "is_weekend",
             "lag_24h", "lag_168h", "roll_24h_mean"]
    xtr, xte, ytr, yte, sp = tu.chronological_split(df, feats, "national_demand_mw", order_col="timestamp")
    est = HistGradientBoostingRegressor(max_iter=400, random_state=tu.RANDOM_STATE)
    est.fit(xtr, ytr)
    m = tu.regression_metrics(yte, est.predict(xte))
    tu.save_pkl({"estimator": est, "feature_columns": feats, "target": "national_demand_mw",
                 "prediction_type": "load_forecast", "unit": "MW", "model_type": "hist_gradient_boosting"},
                "kaggle_load_forecast_model.pkl")
    prov.ModelCard(
        model_name="kaggle_load_forecast_model",
        training_data_files=["kaggle_load_training.parquet", "kaggle_load_processed.parquet"],
        training_data_sources=[_src("shubhamvashisht/hourly-load-india-electrical-load-forecasting",
                                    prov.REAL_INDIA, "India (National; Southern Region proxy)")],
        training_geography="India (national aggregate demand)", target_geography="Bengaluru, Karnataka, India",
        local_data_available=False, domain_shift_risk="HIGH",
        features=feats, target="national_demand_mw", train_rows=sp["n_train"], test_rows=sp["n_test"],
        metrics={"chosen_model": "hist_gradient_boosting", **m},
        limitations=[
            "Real India NATIONAL hourly demand (2019+), not Karnataka/Bengaluru feeder load.",
            "Southern Region column exists as the closest proxy but is a 5-state aggregate.",
        ],
        production_ready=False,
        reason_if_not_production_ready="REAL_INDIA national demand, not Karnataka-local; high domain "
        "shift. Usable as an India baseline only.",
        uses_synthetic_data=False, synthetic_percentage=0.0,
        uses_non_local_data=False, non_local_data_percentage=0.0,
        data_mode=data_mode, prediction_type="load_forecast", model_type="hist_gradient_boosting",
    ).save("kaggle_load_forecast_model_card.json")
    print(f"[train_from_kaggle] India load: R2={m['r2']} RMSE={m['rmse']} MW (REAL_INDIA, prod=False)")
    return {"agent": "kaggle_load", "status": "TRAINED", "metrics": m, "production_ready": False,
            "geography": "REAL_INDIA", "rows": sp["n"]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--data-mode", default="real", choices=["real", "demo"])
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    if args.data_mode not in ("real", "demo"):
        raise ValueError("bad data-mode")
    prov.ensure_dirs()
    results = {}
    for fn in (train_pv, train_solar, train_cloud, train_load):
        r = fn(args.data_mode)
        results[r["agent"]] = r
    manifest = {"data_mode": args.data_mode, "results": results}
    prov.save_json(manifest, prov.model_metadata_dir() / "kaggle_training_run_manifest.json")
    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
