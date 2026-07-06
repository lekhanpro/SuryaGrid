"""Tests for the real data-source layer (registry + providers)."""

import asyncio

from app.data_sources import source_registry as sr
from app.data_sources.kaggle_solar_provider import KaggleSolarProvider
from app.data_sources.live_weather_provider import LiveWeatherProvider
from app.data_sources.substation_provider import SubstationProvider
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider


def test_source_registry_complete_and_valid():
    assert len(sr.SOURCES) >= 6
    for rec in sr.list_sources():
        assert rec.url, f"{rec.id} missing url"
        assert rec.classification in sr.VALID_CLASSIFICATIONS
    om = sr.get_source("SRC-OPENMETEO-001")
    assert om.type == "weather" and "shortwave_radiation" in om.fields.values()


def test_cite_builds_reference_array():
    cites = sr.cite("SRC-PVLIB-001", "SRC-KAGGLE-SOLAR-001", "UNKNOWN")
    assert [c["id"] for c in cites] == ["SRC-PVLIB-001", "SRC-KAGGLE-SOLAR-001"]
    assert all("reference" in c for c in cites)


def test_kaggle_reports_not_loaded_when_absent(tmp_path):
    prov = KaggleSolarProvider(data_dir=tmp_path)
    assert prov.is_loaded() is False
    st = prov.status().to_dict()
    assert st["loaded"] is False
    assert st["detail"] == "Kaggle dataset not loaded"


def test_kaggle_ingest_without_credentials_is_graceful(tmp_path, monkeypatch):
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    prov = KaggleSolarProvider(data_dir=tmp_path)
    result = prov.ingest_via_api()
    assert result["ingested"] is False
    assert result["reason"] == "missing_credentials"


def test_kaggle_normalizes_manual_csv(tmp_path):
    csv = (
        "UNIXTime,Data,Time,Radiation,Temperature,Pressure,Humidity,WindDirection(Degrees),Speed\n"
        "1472724008,9/29/2016 12:00:00 AM,23:55:26,1.21,48,30.46,59,177.39,5.62\n"
        "1472724307,9/29/2016 12:00:00 AM,00:00:07,1.21,48,30.46,58,176.78,3.37\n"
    )
    (tmp_path / "SolarPrediction.csv").write_text(csv, encoding="utf-8")
    prov = KaggleSolarProvider(data_dir=tmp_path)
    assert prov.is_loaded() is True
    df = prov.load_dataframe()
    assert "irradiance_w_m2" in df.columns
    # Temperature 48F -> ~8.9C ; pressure inHg->hPa ~1031 ; speed mph->m/s
    assert abs(df["temperature_c"].iloc[0] - (48 - 32) * 5 / 9) < 0.01
    assert df["pressure_hpa"].iloc[0] > 1000
    assert df["wind_speed_mps"].iloc[0] < df["irradiance_w_m2"].iloc[0] + 10  # sane


def test_synthetic_provider_is_deterministic_and_labelled():
    prov = SyntheticWeatherProvider()
    pts1 = asyncio.run(prov.fetch_forecast(12.9, 77.5, "Asia/Kolkata", forecast_days=1))
    pts2 = asyncio.run(prov.fetch_forecast(12.9, 77.5, "Asia/Kolkata", forecast_days=1))
    assert len(pts1) == 24
    assert [p.ghi_w_m2 for p in pts1] == [p.ghi_w_m2 for p in pts2]  # deterministic
    assert prov.status().mode == "synthetic"


def test_live_weather_horizon_notes_hourly_limitation():
    hours, note = LiveWeatherProvider.resolve_horizon("15min")
    assert hours == 1 and "hourly" in note.lower()
    hours24, _ = LiveWeatherProvider.resolve_horizon("24h")
    assert hours24 == 24


def test_substation_csv_parse_keeps_source_and_confidence():
    csv = "name,voltage_level,operator,latitude,longitude\nX SS,220000,KPTCL,12.9,77.6\nbad,,,,\n"
    recs = SubstationProvider.parse_csv(csv)
    assert len(recs) == 1  # bad row (no coords) skipped, never invented
    assert recs[0]["source_confidence"] == 1.0
    assert recs[0]["latitude"] == 12.9
