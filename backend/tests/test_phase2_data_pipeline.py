"""Phase 2 - regional load parser, capacity matcher, local-PV ingestion schema.

All offline and fixture-driven: no external data has been granted, so these tests
prove the machinery is honest (strict rejection, provenance, planned vs
commissioned, measured vs estimated) rather than asserting real values exist.

Run: python -m pytest tests/test_phase2_data_pipeline.py -q
"""

from app.data_pipeline import kptcl_capacity as cap
from app.data_pipeline import local_pv_schema as pv
from app.data_pipeline.ingest_regional_load import (
    FORMAT_STATUS,
    parse_regional_load_csv,
)

# --------------------------------------------------------------------------- #
# Regional load parser
# --------------------------------------------------------------------------- #
_GOOD_CSV = (
    "timestamp,region,demand_mw\n"
    "2026-07-01T00:00:00+05:30,Karnataka,8250.5\n"
    "2026-07-01T00:15:00+05:30,Karnataka,8190.0\n"
)


def test_regional_load_parses_good_rows_with_provenance():
    out = parse_regional_load_csv(
        _GOOD_CSV, source_name="Fixture SLDC", source_url="https://example.invalid"
    )
    assert out["accepted"] == 2
    assert out["rejected"] == []
    assert out["provenance"]["format_status"] == FORMAT_STATUS
    assert out["provenance"]["source_name"] == "Fixture SLDC"


def test_regional_load_rejects_bad_rows_without_coercion():
    csv_text = (
        "timestamp,region,demand_mw\n"
        "not-a-time,Karnataka,100\n"  # bad timestamp
        "2026-07-01T00:00:00,Karnataka,100\n"  # naive timestamp
        "2026-07-01T00:00:00+05:30,Karnataka,-5\n"  # negative
        "2026-07-01T00:00:00+05:30,,100\n"  # empty region
        "2026-07-01T00:00:00+05:30,Karnataka,abc\n"  # unparseable demand
    )
    out = parse_regional_load_csv(csv_text, source_name="x", source_url="y")
    assert out["accepted"] == 0
    assert len(out["rejected"]) == 5
    reasons = " ".join(r["reason"] for r in out["rejected"])
    assert "timestamp" in reasons and "negative" in reasons and "region" in reasons


def test_regional_load_unexpected_format_raises():
    try:
        parse_regional_load_csv("foo,bar\n1,2\n", source_name="x", source_url="y")
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("expected ValueError on unknown format")


# --------------------------------------------------------------------------- #
# KPTCL capacity matcher
# --------------------------------------------------------------------------- #
_CATALOG = [
    {
        "substation_id": "S1",
        "name": "Whitefield Substation",
        "latitude": 12.97,
        "longitude": 77.75,
        "voltage_kv": 66.0,
    },
    {
        "substation_id": "S2",
        "name": "Hebbal",
        "latitude": 13.03,
        "longitude": 77.59,
        "voltage_kv": 220.0,
    },
    {
        "substation_id": "S3",
        "name": "Whitefield",
        "latitude": 12.99,
        "longitude": 77.72,
        "voltage_kv": 66.0,
    },
]


def test_capacity_unique_match_marks_commissioned_usable():
    recs = [
        cap.CapacityRecord(
            station_name="Hebbal SS",
            voltage_kv=220.0,
            capacity_mva=100.0,
            status=cap.STATUS_COMMISSIONED,
            source_name="KPTCL fixture",
            source_url="https://example.invalid",
            latitude=13.03,
            longitude=77.59,
        )
    ]
    out = cap.match_capacity_records(recs, _CATALOG)
    assert len(out["matched"]) == 1
    assert out["matched"][0]["substation_id"] == "S2"
    assert out["matched"][0]["usable_capacity"] is True


def test_capacity_planned_status_is_not_usable():
    recs = [
        cap.CapacityRecord(
            station_name="Hebbal",
            voltage_kv=220.0,
            capacity_mva=50.0,
            status=cap.STATUS_PLANNED,
            source_name="KPTCL fixture",
            source_url="https://example.invalid",
            latitude=13.03,
            longitude=77.59,
        )
    ]
    out = cap.match_capacity_records(recs, _CATALOG)
    assert out["matched"][0]["usable_capacity"] is False  # planned augmentation, not on ground


def test_capacity_ambiguous_match_goes_to_manual_review():
    recs = [
        cap.CapacityRecord(
            station_name="Whitefield",
            voltage_kv=66.0,
            capacity_mva=40.0,
            status=cap.STATUS_COMMISSIONED,
            source_name="KPTCL fixture",
            source_url="https://example.invalid",
            latitude=12.98,
            longitude=77.73,
        )
    ]
    out = cap.match_capacity_records(recs, _CATALOG)
    assert out["matched"] == []
    assert len(out["needs_manual_review"]) == 1
    assert set(out["needs_manual_review"][0]["candidates"]) == {"S1", "S3"}


def test_capacity_no_candidate_is_unmatched():
    recs = [
        cap.CapacityRecord(
            station_name="Nowhere Grid",
            voltage_kv=400.0,
            capacity_mva=500.0,
            status=cap.STATUS_COMMISSIONED,
            source_name="KPTCL fixture",
            source_url="https://example.invalid",
        )
    ]
    out = cap.match_capacity_records(recs, _CATALOG)
    assert len(out["unmatched"]) == 1


# --------------------------------------------------------------------------- #
# Local PV ingestion schema
# --------------------------------------------------------------------------- #
def test_local_pv_accepts_good_measured_reading():
    reading, reason = pv.validate_reading(
        {
            "timestamp": "2026-07-01T12:00:00+05:30",
            "plant_id": "PLANT-1",
            "ac_power_kw": 4200.0,
            "dc_power_kw": 4400.0,
            "irradiance_wm2": 910.0,
            "inverter_state": "running",
            "quality_flag": "good",
            "meter_id": "M-1",
            "meter_source": "BESCOM ABT meter",
        }
    )
    assert reason is None
    assert reading is not None
    assert reading.generation_type == "MEASURED_LOCAL_PV"
    assert reading.actual_generation_available is True


def test_local_pv_rejects_missing_provenance_and_bad_values():
    batch = pv.validate_batch(
        [
            {
                "timestamp": "2026-07-01T12:00:00+05:30",
                "plant_id": "P",
                "quality_flag": "GOOD",
                "inverter_state": "RUNNING",
                "meter_id": "",
                "meter_source": "",
            },  # no provenance
            {
                "timestamp": "2026-07-01T12:00:00",
                "plant_id": "P",
                "quality_flag": "GOOD",
                "inverter_state": "RUNNING",
                "meter_id": "M",
                "meter_source": "x",
                "ac_power_kw": 1,
            },  # naive ts
            {
                "timestamp": "2026-07-01T12:00:00+05:30",
                "plant_id": "P",
                "quality_flag": "GOOD",
                "inverter_state": "RUNNING",
                "meter_id": "M",
                "meter_source": "x",
            },  # GOOD but no power
            {
                "timestamp": "2026-07-01T12:00:00+05:30",
                "plant_id": "P",
                "quality_flag": "BOGUS",
                "inverter_state": "RUNNING",
                "meter_id": "M",
                "meter_source": "x",
                "ac_power_kw": 1,
            },  # bad quality
        ]
    )
    assert batch["accepted_count"] == 0
    assert len(batch["rejected"]) == 4
    reasons = " ".join(r["reason"] for r in batch["rejected"])
    assert "provenance" in reasons and "timezone-aware" in reasons and "GOOD but no" in reasons
