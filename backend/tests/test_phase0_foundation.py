"""Phase 0 - Foundation hardening (execution roadmap).

Guard rails that must never regress:

  * No unapproved currency output: the app source never contains a rupee symbol and
    never sets emits_rupee_values=True (official KERC/CERC tariff is not parsed yet).
  * APP_DATA_MODE defaults to "real"; synthetic data is always labelled synthetic.
  * Every trained model card carries provenance (version + named, URL'd sources).
  * The machine-readable source registry is internally consistent and cite() never
    fabricates a record for an unknown source id.

Run: python -m pytest tests/test_phase0_foundation.py -q
"""

from pathlib import Path

from app.config import Settings
from app.data_sources import source_registry as reg
from app.data_sources.base_provider import TYPE_SYNTHETIC
from app.data_sources.synthetic_weather_provider import SyntheticWeatherProvider
from app.ml import provenance as prov

APP_DIR = Path(__file__).resolve().parents[1] / "app"
CARDS_DIR = Path(__file__).resolve().parents[1] / "models" / "metadata"

ALLOWED_CLASSIFICATIONS = {
    reg.OFFICIAL_SOURCE,
    reg.DATASET_DERIVED,
    reg.MODEL_LEARNED,
    reg.USER_CONFIGURABLE,
    reg.FALLBACK_DEFAULT,
    reg.USER_CONFIGURABLE_PENDING,
}


# --------------------------------------------------------------------------- #
# No unapproved currency
# --------------------------------------------------------------------------- #
# The one module allowed to set emits_rupee_values=True: it is hard-gated on a
# verified official KERC order and ships blocked (see test_phase1 gate tests).
_RUPEE_GATED_FILES = {"kerc_dsm_2026.py"}


def test_no_rupee_symbol_or_rupee_emission_in_app_code():
    offenders: list[str] = []
    for py in APP_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="replace")
        if "₹" in text:  # ₹
            offenders.append(f"{py}: rupee symbol")
        if py.name not in _RUPEE_GATED_FILES and (
            "emits_rupee_values=True" in text.replace(" ", "")
            or '"emits_rupee_values":True' in text.replace(" ", "")
        ):
            offenders.append(f"{py}: emits_rupee_values set True")
    assert not offenders, offenders


# --------------------------------------------------------------------------- #
# Data-mode behavior matrix
# --------------------------------------------------------------------------- #
def test_data_mode_defaults_to_real():
    assert Settings().APP_DATA_MODE == prov.DATA_MODE_REAL == "real"


def test_synthetic_provider_is_always_labelled_synthetic():
    p = SyntheticWeatherProvider()
    assert p.name == "synthetic"
    assert p.provider_type == TYPE_SYNTHETIC


# --------------------------------------------------------------------------- #
# Model-card provenance (no orphan sources)
# --------------------------------------------------------------------------- #
def test_every_model_card_has_provenance_or_explicit_untrained_status():
    import json

    cards = sorted(CARDS_DIR.glob("*_card.json"))
    assert cards, "no model cards found"
    for path in cards:
        card = json.loads(path.read_text(encoding="utf-8"))
        srcs = card.get("training_data_sources")
        if srcs:
            for s in srcs:
                assert s.get("name"), f"{path.name}: source without name"
                assert s.get("url"), f"{path.name}: source without url"
                assert s.get("label"), f"{path.name}: source without label"
        else:
            # Untrained/blocked artifacts must say so explicitly, never silently.
            text = json.dumps(card).lower()
            assert any(
                k in text for k in ("untrained", "not_trained", "insufficient", "blocked")
            ), f"{path.name}: no sources and no explicit untrained/blocked status"


# --------------------------------------------------------------------------- #
# Source registry integrity
# --------------------------------------------------------------------------- #
def test_source_registry_records_are_complete_and_classified():
    assert reg.SOURCES, "source registry is empty"
    for sid, rec in reg.SOURCES.items():
        assert rec.id == sid
        assert rec.name and rec.url, f"{sid}: missing name/url"
        assert rec.classification in ALLOWED_CLASSIFICATIONS, f"{sid}: {rec.classification}"


def test_cite_never_fabricates_unknown_sources():
    assert reg.cite("NOT-A-REAL-SOURCE-ID") == []
