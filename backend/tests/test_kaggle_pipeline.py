"""Tests for the Phase 1.7 Kaggle ingestion/training pipeline.

Contract tests always run (real-mode guard, missing-file behavior). Artifact/API tests
skip if the download+ingest+train has not been run in this checkout.
"""

import asyncio
import json

import pytest

from app.data_pipeline import _common as C
from app.ml import provenance as prov


# ---------------- contract (no artifacts needed) ---------------- #
def test_require_real_mode_rejects_bad_mode():
    with pytest.raises(ValueError):
        C.require_real_mode("bogus")
    C.require_real_mode("real")  # no raise
    C.require_real_mode("demo")


def test_real_mode_blocks_synthetic_label():
    with pytest.raises(prov.SyntheticFallbackError):
        prov.assert_real_mode_allows(prov.SYNTHETIC_AUGMENTED_FROM_REAL,
                                     data_mode="real", context="kaggle")


def test_builder_raises_on_missing_processed_file():
    from app.ml import build_kaggle_ml_datasets as B

    with pytest.raises(FileNotFoundError):
        B._read("this_processed_file_does_not_exist.parquet")


def test_stamp_metadata_marks_real_not_synthetic():
    import pandas as pd

    df = C.stamp_metadata(pd.DataFrame({"x": [1, 2]}), source_name="s", kaggle_slug="a/b",
                          source_url="u", geography="India", source_label=prov.REAL_INDIA,
                          data_type="t")
    assert df["is_real"].all() and (~df["is_synthetic"]).all()
    assert (df["source_label"] == prov.REAL_INDIA).all()


# ---------------- artifact tests (skip if not built) ---------------- #
def _processed_or_skip(name):
    import pandas as pd

    p = C.processed_kaggle_dir() / name
    if not p.exists():
        pytest.skip(f"{name} not built; run the ingest scripts")
    return pd.read_parquet(p)


def test_raw_kaggle_files_present():
    base = C.raw_kaggle_dir()
    anik = base / "pv_generation/anikannal_solar_power_generation" / "Plant_1_Generation_Data.csv"
    beng = base / "solar/india_cities_irradiance" / "Bengluru solar irradiance.csv"
    if not anik.exists() or not beng.exists():
        pytest.skip("Kaggle raw files not downloaded in this checkout")
    assert anik.stat().st_size > 0 and beng.stat().st_size > 0


def test_processed_files_are_real():
    for name in ("kaggle_pv_generation_processed.parquet", "kaggle_solar_processed.parquet",
                 "kaggle_load_processed.parquet"):
        df = _processed_or_skip(name)
        for col in ("is_real", "is_synthetic", "source_name", "kaggle_slug", "source_url",
                    "data_geography", "source_label", "data_type"):
            assert col in df.columns, f"{name} missing {col}"
        assert bool(df["is_real"].all())
        assert not bool(df["is_synthetic"].any())


def test_ml_training_files_exist():
    for name in ("kaggle_pv_ac_training.parquet", "kaggle_solar_irradiance_training.parquet",
                 "kaggle_cloud_training.parquet", "kaggle_load_training.parquet"):
        if not prov.ml_file_exists(name):
            pytest.skip(f"{name} not built")
        df = prov.read_parquet(name)
        assert len(df) > 100


def test_kaggle_model_cards_complete_and_honest():
    cards = {
        "kaggle_pv_ac_model_card.json": False,
        "kaggle_solar_irradiance_bengaluru_model_card.json": True,
        "kaggle_cloud_risk_bengaluru_model_card.json": True,
        "kaggle_load_forecast_model_card.json": False,
    }
    any_present = False
    for name, expect_prod in cards.items():
        p = prov.model_metadata_dir() / name
        if not p.exists():
            continue
        any_present = True
        d = json.loads(p.read_text(encoding="utf-8"))
        for f in prov.REQUIRED_MODEL_CARD_FIELDS:
            assert f in d, f"{name} missing {f}"
        assert d["uses_synthetic_data"] is False
        assert d["data_mode"] == "real"
        assert d["production_ready"] == expect_prod, f"{name} prod mismatch"
        if not d["production_ready"]:
            assert d["reason_if_not_production_ready"]
    if not any_present:
        pytest.skip("Kaggle model cards not present; run train_from_kaggle")


# ---------------- API tests ---------------- #
async def _call(method, path, **kw):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await getattr(c, method)(path, **kw)


def test_api_kaggle_status_has_slug_and_prod_flag():
    async def run():
        r = await _call("get", "/api/v1/kaggle/status")
        assert r.status_code == 200
        models = r.json()["data"]["models"]
        assert "pv_ac" in models
        if not models["pv_ac"].get("model_present"):
            pytest.skip("kaggle pv model not trained")
        assert models["pv_ac"]["kaggle_dataset_slug"]
        assert models["pv_ac"]["production_ready"] is False  # REAL_INDIA plant
        assert models["solar_irradiance"]["training_geography"].startswith("Bengaluru")
    asyncio.run(run())


def test_api_kaggle_pv_estimate_has_provenance():
    if not (prov.trained_models_dir() / "kaggle_pv_ac_model.pkl").exists():
        pytest.skip("kaggle pv model not trained")

    async def run():
        r = await _call("post", "/api/v1/kaggle/pv/estimate",
                        json={"irradiation": 0.8, "ambient_temperature_c": 32,
                              "module_temperature_c": 45, "hour_of_day": 12})
        assert r.status_code == 200
        d = r.json()["data"]
        for k in ("prediction_type", "prediction_value", "model_file", "model_version",
                  "kaggle_dataset_slug", "training_geography", "target_geography",
                  "uses_non_local_data", "production_ready", "limitations", "data_mode"):
            assert k in d, f"pv estimate missing {k}"
        assert d["prediction_value"] >= 0.0
        assert d["production_ready"] is False
    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
