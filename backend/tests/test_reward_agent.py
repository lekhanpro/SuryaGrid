"""Tests for the RewardAgent settlement engine."""

from app.agents.reward_agent import RewardAgent

agent = RewardAgent()


def test_surplus_earns_bonus():
    r = agent.settle(target_kw=100, actual_kw=120, window_hours=1.0)
    assert r.shortfall_kw == 0.0
    assert r.surplus_kw == 20.0
    assert r.bonus_amount > 0
    assert r.penalty_amount == 0.0
    assert r.net_owner > 0


def test_shortfall_incurs_penalty():
    r = agent.settle(target_kw=100, actual_kw=60, window_hours=1.0)
    assert r.shortfall_kw == 40.0
    assert r.surplus_kw == 0.0
    assert r.penalty_amount > 0
    assert r.bonus_amount == 0.0
    assert r.net_owner < 0


def test_exact_target_zero_settlement():
    r = agent.settle(target_kw=100, actual_kw=100, window_hours=1.0)
    assert r.shortfall_kw == 0.0
    assert r.surplus_kw == 0.0
    assert r.penalty_amount == 0.0
    assert r.bonus_amount == 0.0
    assert r.net_owner == 0.0


def test_discount_only_on_surplus_absorbed():
    # Surplus exists (actual > target) and consumer absorbs part
    r = agent.settle(target_kw=100, actual_kw=150, consumption_kw=30, window_hours=1.0)
    assert r.discount_amount > 0
    # Discount is bounded by the surplus (50) and consumption (30) → min = 30
    assert r.discount_amount == 2.0 * 30 * 1.0  # default discount_rate * shifted_load * hours


def test_settle_day_aggregates():
    targets = [100, 100, 100]
    actuals = [80, 120, 100]
    result = agent.settle_day(targets=targets, actuals=actuals)
    assert result["intervals"] == 3
    assert result["total_penalty"] > 0  # first interval has shortfall
    assert result["total_bonus"] > 0  # second interval has surplus
    assert len(result["settlements"]) == 3


if __name__ == "__main__":
    test_surplus_earns_bonus()
    test_shortfall_incurs_penalty()
    test_exact_target_zero_settlement()
    test_discount_only_on_surplus_absorbed()
    test_settle_day_aggregates()
    print("All RewardAgent tests PASSED")
