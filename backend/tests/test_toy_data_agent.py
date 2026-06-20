"""Test ToyDataAgent generates correct synthetic data."""

import sys
sys.path.insert(0, ".")

from datetime import date
from app.agents.toy_data_agent import ToyDataAgent


def test_generate_site_day():
    agent = ToyDataAgent()
    points = agent.generate_site_day(
        site_id="test-site",
        target_date=date(2026, 6, 20),
        capacity_mw=50.0,
        interval_minutes=30,
        seed=42,
    )

    # 48 intervals in a day (30 min each)
    assert len(points) == 48, f"Expected 48, got {len(points)}"

    # Night readings should have 0 irradiance
    midnight = points[0]
    assert midnight.irradiance_w_m2 == 0.0

    # Noon (index 24 = hour 12) should have high irradiance
    noon = points[24]
    assert noon.irradiance_w_m2 > 800, f"Noon irradiance too low: {noon.irradiance_w_m2}"

    # All values in valid ranges
    for p in points:
        assert 0 <= p.irradiance_w_m2 <= 1000
        assert 0 <= p.cloud_cover_percent <= 100
        assert -10 <= p.temperature_c <= 55
        assert 0 <= p.humidity_percent <= 100
        assert p.wind_speed_mps >= 0

    print(f"Generated {len(points)} data points")
    print(f"Midnight: irr={midnight.irradiance_w_m2}, cloud={midnight.cloud_cover_percent}%")
    print(f"Noon:     irr={noon.irradiance_w_m2}, cloud={noon.cloud_cover_percent}%, temp={noon.temperature_c}C")


def test_generate_schedule():
    agent = ToyDataAgent()
    schedule = agent.generate_schedule(
        capacity_mw=50.0,
        target_date=date(2026, 6, 20),
        interval_minutes=30,
    )

    assert len(schedule) == 48
    # Night entries should be 0
    assert schedule[0][1] == 0.0
    # Peak should be < capacity (0.7 factor)
    peak = max(mw for _, mw in schedule)
    assert peak <= 50.0 * 0.7 + 0.001
    assert peak > 30.0  # Should be meaningful

    print(f"Schedule peak: {peak} MW")


def test_deterministic_with_seed():
    agent = ToyDataAgent()
    run1 = agent.generate_site_day("s1", date(2026, 6, 20), 50.0, seed=123)
    run2 = agent.generate_site_day("s1", date(2026, 6, 20), 50.0, seed=123)
    for a, b in zip(run1, run2):
        assert a.irradiance_w_m2 == b.irradiance_w_m2
        assert a.cloud_cover_percent == b.cloud_cover_percent
    print("Deterministic seed test PASSED")


if __name__ == "__main__":
    test_generate_site_day()
    test_generate_schedule()
    test_deterministic_with_seed()
    print("\nAll ToyDataAgent tests PASSED")
