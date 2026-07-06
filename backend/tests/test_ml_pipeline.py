"""Tests for the ML pipeline: augmented dataset, quality, training, prediction."""

import asyncio

from app.agents.forecast_agent import ForecastAgent, SiteConfig
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider
from app.ml import data_quality, dataset_builder, model_registry, train_model
from app.ml.feature_engineering import AUGMENTED_COLUMNS
from app.ml.predict_model import ModelPredictor


def _augmented(days=20):
    prov = SyntheticWeatherProvider(cloudiness=0.4)
    pts = asyncio.run(prov.fetch_forecast(12.97, 77.59, "Asia/Kolkata", forecast_days=days))
    src = dataset_builder.weather_points_to_frame(pts, "synthetic")
    return dataset_builder.build_augmented(
        src, latitude=12.97, longitude=77.59, site_capacity_mw=50.0
    )


def test_augmented_schema_and_quality():
    df, report = _augmented(2)
    assert list(df.columns) == AUGMENTED_COLUMNS
    assert report["total_flagged"] == 0
    assert (df["quality_flag"] == 1).all()


def test_quality_flags_impossible_values():
    df, _ = _augmented(2)
    df.loc[0, "irradiance_w_m2"] = 5000.0  # impossible
    df.loc[1, "latitude"] = 999.0  # bad coordinate
    rep = data_quality.run_quality_checks(df, capacity_mw=50)
    assert rep["issues"]["impossible_irradiance"] >= 1
    assert rep["issues"]["bad_coordinates"] >= 1
    assert rep["passed"] is False


def test_train_predict_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("SURYAGRID_MODELS_DIR", str(tmp_path))
    assert model_registry.is_trained() is False
    df, _ = _augmented(20)
    meta = train_model.train(df, model_name="random_forest", dataset_name="test")
    assert meta["target"] == "irradiance_w_m2"
    assert meta["target_type"] == "irradiance"
    assert {"mae", "rmse", "r2"}.issubset(meta["metrics"].keys())
    assert meta["source_references"]
    assert "limitations" in meta
    assert model_registry.is_trained() is True

    p = ModelPredictor()
    assert p.is_available()
    out = p.predict_one(
        {
            "hour_of_day": 12,
            "day_of_year": 150,
            "month": 5,
            "temperature_c": 30,
            "humidity_percent": 40,
            "wind_speed_mps": 3,
            "pressure_hpa": 1008,
            "latitude": 12.97,
            "longitude": 77.59,
            "site_capacity_mw": 50,
            "panel_efficiency": 0.18,
            "nearest_substation_distance_km": 3,
        }
    )
    assert out is not None and out["value"] >= 0
    model_registry.clear()


def test_train_insufficient_samples_raises():
    df, _ = _augmented(20)
    try:
        train_model.train(df.head(5))
        raise AssertionError("expected ValueError for too few samples")
    except ValueError:
        pass


def test_forecast_formula_fallback_without_model(tmp_path, monkeypatch):
    monkeypatch.setenv("SURYAGRID_MODELS_DIR", str(tmp_path))  # empty -> untrained
    fa = ForecastAgent()
    site = SiteConfig(latitude=12.97, longitude=77.59, timezone="Asia/Kolkata", capacity_mw=50)
    pts = asyncio.run(
        SyntheticWeatherProvider().fetch_forecast(12.97, 77.59, "Asia/Kolkata", forecast_days=1)
    )
    out = fa.forecast_timeline(site, pts, mode="auto", predictor=ModelPredictor())
    assert out[0].forecast_mode == "formula"
    assert "formula" in out[0].source_used
