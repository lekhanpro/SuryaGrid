"""Phase 1.7 tests - real-data ML pipeline honesty & provenance.

Two layers:
  * Contract tests (always run, no network/artifacts): the real-mode synthetic guard,
    model-card required fields, and source_status derivation.
  * Artifact tests (skip if the build/train has not been run in this checkout): datasets
    carry source metadata, cards are complete & honest, trained models exist, the RL
    policy is honestly absent, and the API returns a full provenance envelope with a
    non-fabricated confidence score.

Run: python -m pytest tests/ -q
"""

import asyncio
import json

import pytest

from app.ml import provenance as prov


# --------------------------------------------------------------------------- #
# Contract tests (no artifacts / no network required)
# --------------------------------------------------------------------------- #
def test_real_mode_blocks_synthetic_and_demo():
    for label in (prov.SYNTHETIC_AUGMENTED_FROM_REAL, prov.DEMO_ONLY):
        with pytest.raises(prov.SyntheticFallbackError):
            prov.assert_real_mode_allows(label, data_mode="real", context="test")
    # Real/coordinate labels are allowed in real mode.
    prov.assert_real_mode_allows(prov.REAL_COORDINATE_BASED, data_mode="real", context="test")
    # In demo mode synthetic is permitted (no raise).
    prov.assert_real_mode_allows(prov.SYNTHETIC_AUGMENTED_FROM_REAL, data_mode="demo", context="t")


def test_model_card_has_all_required_fields_incl_data_mode_and_source_status():
    assert "data_mode" in prov.REQUIRED_MODEL_CARD_FIELDS
    assert "source_status" in prov.REQUIRED_MODEL_CARD_FIELDS
    card = prov.ModelCard(
        model_name="unit_test_model",
        training_data_sources=[{"name": "x", "label": prov.REAL_COORDINATE_BASED}],
        target="y",
        production_ready=True,
        domain_shift_risk="LOW",
    )
    d = card.to_dict()
    for field in prov.REQUIRED_MODEL_CARD_FIELDS:
        assert field in d, f"card missing required field {field}"
    assert d["data_mode"] == prov.DATA_MODE_REAL
    card.validate()  # should not raise


def test_source_status_auto_derived_from_sources():
    card = prov.ModelCard(
        model_name="m",
        training_data_sources=[
            {"label": prov.REAL_COORDINATE_BASED},
            {"label": prov.ESTIMATED_FROM_REAL},
            {"label": prov.REAL_COORDINATE_BASED},  # duplicate collapses
        ],
        production_ready=True,
    )
    assert card.source_status == [prov.REAL_COORDINATE_BASED, prov.ESTIMATED_FROM_REAL]


def test_not_production_ready_requires_reason():
    with pytest.raises(ValueError):
        prov.ModelCard(model_name="m", production_ready=False).validate()


def test_real_bengaluru_label_exists():
    assert prov.REAL_BENGALURU in prov.ALL_SOURCE_LABELS
    assert prov.REAL_BENGALURU in prov.PRODUCTION_TRUTH_LABELS


# --------------------------------------------------------------------------- #
# Artifact tests (skip if datasets/models not built in this checkout)
# --------------------------------------------------------------------------- #
def _read_parquet_or_skip(name):
    df = prov.read_parquet(name)
    if df is None or len(df) == 0:
        pytest.skip(f"{name} not built; run app.ml.build_ml_datasets --data-mode real")
    return df


def _card_or_skip(name):
    path = prov.model_metadata_dir() / name
    if not path.exists():
        pytest.skip(f"{name} not present; run app.ml.train_all_agents --data-mode real")
    return json.loads(path.read_text(encoding="utf-8"))


def test_weather_dataset_has_source_metadata():
    df = _read_parquet_or_skip("bengaluru_weather_solar_history.parquet")
    for col in ("source_name", "source_url", "data_geography", "ingestion_time", "quality_score"):
        assert col in df.columns, f"weather missing {col}"
    assert df["shortwave_radiation_wm2"].notna().mean() > 0.9
    # No synthetic label leaked into real dataset.
    assert (df["source"] == prov.REAL_COORDINATE_BASED).all()


def test_substation_dataset_honest_capacity_and_labels():
    df = _read_parquet_or_skip("bengaluru_substations_cleaned.parquet")
    for col in (
        "substation_id",
        "latitude",
        "longitude",
        "voltage_kv",
        "capacity_mva",
        "source",
        "source_url",
        "reliability_score",
        "missing_fields",
        "data_geography",
        "ingestion_time",
    ):
        assert col in df.columns, f"substation missing {col}"
    # Capacity is never invented -> must be entirely null.
    assert df["capacity_mva"].isna().all(), "capacity_mva must stay null (never fabricated)"
    assert set(df["source_label"].unique()) <= {prov.REAL_BENGALURU, prov.REAL_KARNATAKA}


def test_no_synthetic_data_files_in_real_build():
    # Neither the weather nor substation datasets may carry synthetic/demo labels.
    for name, col in (
        ("bengaluru_weather_solar_history.parquet", "source"),
        ("solar_agent_training.parquet", "source_label"),
    ):
        df = _read_parquet_or_skip(name)
        vals = set(df[col].unique())
        assert prov.SYNTHETIC_AUGMENTED_FROM_REAL not in vals
        assert prov.DEMO_ONLY not in vals


def test_all_cards_complete_and_honest():
    for name in (
        "solar_forecast_model_card.json",
        "cloud_risk_classifier_card.json",
        "dsm_model_card.json",
        "load_forecast_model_card.json",
        "rl_policy_card.json",
    ):
        d = _card_or_skip(name)
        for field in prov.REQUIRED_MODEL_CARD_FIELDS:
            assert field in d, f"{name} missing {field}"
        assert d["uses_synthetic_data"] is False
        assert d["synthetic_percentage"] == 0.0
        assert d["data_mode"] == "real"
        if not d["production_ready"]:
            assert d["reason_if_not_production_ready"], f"{name} needs a reason"


def test_solar_and_cloud_models_exist():
    for pkl in ("solar_forecast_model.pkl", "cloud_risk_classifier.pkl"):
        path = prov.trained_models_dir() / pkl
        if not path.exists():
            pytest.skip(f"{pkl} not trained")
        assert path.stat().st_size > 0


def test_load_not_production_ready_and_rl_skipped_honestly():
    load = _card_or_skip("load_forecast_model_card.json")
    assert load["production_ready"] is False
    assert load["reason_if_not_production_ready"]
    assert load["domain_shift_risk"] == "HIGH"

    rl = _card_or_skip("rl_policy_card.json")
    assert rl["production_ready"] is False
    assert "INSUFFICIENT_REAL_ENVIRONMENT_DATA" in rl["reason_if_not_production_ready"]
    # No fabricated RL policy artifact.
    assert not (prov.trained_models_dir() / "rl_policy.zip").exists()


def test_dsm_emits_no_rupees():
    rules_path = prov.trained_models_dir() / "dsm_rules_engine.json"
    if not rules_path.exists():
        pytest.skip("dsm_rules_engine.json not present")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    assert rules["emits_rupee_values"] is False
    for band in rules["bands"].values():
        assert band["rupee_charge"] is None


# --------------------------------------------------------------------------- #
# API provenance tests (skip if solar/cloud models absent)
# --------------------------------------------------------------------------- #
_ENVELOPE_KEYS = (
    "prediction_type",
    "prediction_value",
    "unit",
    "model_file",
    "model_version",
    "training_geography",
    "target_geography",
    "local_data_used",
    "source_status",
    "confidence_components",
    "limitations",
    "production_ready",
    "data_mode",
)


async def _api_call(method, path, **kw):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await getattr(c, method)(path, **kw)
        return r


def test_api_solar_envelope_and_estimated_pv():
    if not (prov.trained_models_dir() / "solar_forecast_model.pkl").exists():
        pytest.skip("solar model not trained")

    async def run():
        r = await _api_call(
            "post",
            "/api/v1/agents/solar/forecast",
            json={
                "timestamp_local": "2024-06-01T12:00:00",
                "cloud_cover_percent": 10,
                "capacity_mw": 50,
            },
        )
        assert r.status_code == 200
        d = r.json()["data"]
        for k in _ENVELOPE_KEYS:
            assert k in d, f"solar envelope missing {k}"
        assert d["prediction_type"] == "irradiance_forecast"
        assert d["unit"] == "W/m2"
        assert d["data_mode"] == "real"
        # PV must be clearly an estimate, not actual generation.
        assert d["pv_estimate"]["estimated_output"] is True
        assert d["pv_estimate"]["is_actual_generation"] is False
        assert d["pv_estimate"]["source_label"] == prov.ESTIMATED_FROM_REAL

    asyncio.run(run())


def test_api_confidence_is_real_model_output_not_decorative():
    if not (prov.trained_models_dir() / "cloud_risk_classifier.pkl").exists():
        pytest.skip("cloud model not trained")

    async def run():
        r = await _api_call(
            "post",
            "/api/v1/agents/cloud/risk",
            json={
                "timestamp_local": "2024-06-01T12:00:00",
                "cloud_cover_percent": 95,
                "relative_humidity_percent": 90,
                "precipitation_mm": 3,
            },
        )
        assert r.status_code == 200
        d = r.json()["data"]
        conf = d["confidence_components"]
        prob = conf["predicted_probability"]
        # Confidence is the model's real probability output (0..1), echoed in the value,
        # NOT a hard-coded/decorative constant.
        assert 0.0 <= prob <= 1.0
        assert abs(prob - d["prediction_value"]["probability"]) < 1e-9
        assert "model_test_f1" in conf  # real held-out metric present

    asyncio.run(run())


def test_api_status_reports_mode_geography_and_warnings():
    async def run():
        r = await _api_call("get", "/api/v1/agents/status")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["data_mode"] == "real"
        assert "Bengaluru" in d["region"]
        assert isinstance(d["warnings"], list) and len(d["warnings"]) >= 1
        assert "agents" in d and "solar" in d["agents"]

    asyncio.run(run())


def test_api_dsm_requires_schedule_and_has_no_rupees():
    if not (prov.trained_models_dir() / "dsm_classifier.pkl").exists():
        pytest.skip("dsm model not trained")

    async def run():
        # Without a schedule -> honest NOT_AVAILABLE.
        r0 = await _api_call(
            "post",
            "/api/v1/agents/dsm/assess",
            json={"timestamp_local": "2024-06-01T12:00:00", "cloud_cover_percent": 50},
        )
        assert r0.json()["data"]["status"] == prov.NOT_AVAILABLE
        # With a schedule -> assessment, no rupees.
        r = await _api_call(
            "post",
            "/api/v1/agents/dsm/assess",
            json={
                "timestamp_local": "2024-06-01T12:00:00",
                "cloud_cover_percent": 50,
                "scheduled_ghi_wm2": 800,
            },
        )
        d = r.json()["data"]
        assert d["emits_rupee_values"] is False
        assert "prediction_value" in d

    asyncio.run(run())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
