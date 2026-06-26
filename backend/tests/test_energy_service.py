"""Tests for the energy balance service."""

from app.services.energy_service import compute_energy_balance


def test_surplus_and_deficit():
    prod = [100, 0, 50]
    cons = [30, 80, 50]
    result = compute_energy_balance(prod, cons)
    assert result["intervals"] == 3
    assert result["total_surplus_kwh"] == 70.0  # 100-30=70, 0, 0
    assert result["total_deficit_kwh"] == 80.0  # 0, 80, 0
    assert result["total_self_consumed_kwh"] == 30 + 0 + 50


def test_zero_production():
    prod = [0, 0, 0]
    cons = [10, 20, 30]
    result = compute_energy_balance(prod, cons)
    assert result["total_production_kwh"] == 0
    assert result["total_grid_import_kwh"] == 60
    assert result["self_consumption_percent"] == 0.0


def test_no_consumption():
    prod = [100, 200, 150]
    cons = [0, 0, 0]
    result = compute_energy_balance(prod, cons)
    assert result["total_grid_export_kwh"] == 450
    assert result["total_deficit_kwh"] == 0


if __name__ == "__main__":
    test_surplus_and_deficit()
    test_zero_production()
    test_no_consumption()
    print("All energy service tests PASSED")
