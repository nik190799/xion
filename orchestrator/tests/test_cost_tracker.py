from __future__ import annotations

import math

import pytest

from orchestrator.cost_tracker import CostTracker, TreasuryBucket, TreasurySnapshot
from orchestrator.signals.bus import SignalBus


def _snapshot() -> TreasurySnapshot:
    return TreasurySnapshot(
        bucket_balances={
            TreasuryBucket.OPERATING_FLOAT: 1_000.0,
            TreasuryBucket.IMPROVEMENT_FUND: 500.0,
            TreasuryBucket.RAINY_DAY_RESERVE: 700.0,
            TreasuryBucket.FOUNDATION_RESERVE: 300.0,
            TreasuryBucket.TREASURY: 10_000.0,
        },
        weekly_non_discretionary_burn=100.0,
        reserve_floor=800.0,
        trailing_recurring_inflow_weekly=200.0,
        existing_recurring_burn_weekly=20.0,
    )


def test_bucket_attribution_records_debit_time_bucket() -> None:
    tracker = CostTracker(_snapshot())

    first = tracker.record_debit(
        bucket=TreasuryBucket.OPERATING_FLOAT,
        amount=50.0,
        purpose="relay hosting",
        as_of_utc_ns=123,
    )
    tracker.record_debit(bucket="Improvement Fund", amount=25.0, purpose="research")

    assert first.bucket == TreasuryBucket.OPERATING_FLOAT
    assert first.as_of_utc_ns == 123
    assert tracker.total_debits(TreasuryBucket.OPERATING_FLOAT) == 50.0
    assert tracker.total_debits(TreasuryBucket.IMPROVEMENT_FUND) == 25.0


def test_metric_queries() -> None:
    tracker = CostTracker(_snapshot())
    tracker.record_debit(bucket=TreasuryBucket.OPERATING_FLOAT, amount=50.0)
    tracker.record_debit(
        bucket=TreasuryBucket.IMPROVEMENT_FUND,
        amount=25.0,
        recurring_burn_weekly_delta=10.0,
    )

    assert tracker.runway_weeks() == pytest.approx(10.0)
    assert tracker.fraction_of_operating_float() == pytest.approx(0.05)
    assert tracker.fraction_of_improvement_fund() == pytest.approx(0.05)
    assert tracker.distance_to_reserve_floor() == pytest.approx(0.25)
    assert tracker.recurring_burn_ratio() == pytest.approx(0.15)


def test_metric_queries_handle_zero_denominators() -> None:
    tracker = CostTracker(
        TreasurySnapshot(
            bucket_balances={
                TreasuryBucket.OPERATING_FLOAT: 0.0,
                TreasuryBucket.IMPROVEMENT_FUND: 0.0,
            },
            weekly_non_discretionary_burn=0.0,
            reserve_floor=0.0,
        )
    )
    tracker.record_debit(bucket=TreasuryBucket.OPERATING_FLOAT, amount=1.0)

    assert math.isinf(tracker.runway_weeks())
    assert math.isinf(tracker.fraction_of_operating_float())
    assert tracker.distance_to_reserve_floor() == 0.0
    assert tracker.recurring_burn_ratio() == 0.0


def test_financial_vitality_emission_shape() -> None:
    tracker = CostTracker(_snapshot())
    tracker.record_debit(bucket=TreasuryBucket.OPERATING_FLOAT, amount=50.0)
    bus = SignalBus()

    emitted = tracker.emit_financial_vitality(bus)
    by_kind = {signal.kind: signal for signal in emitted}

    assert set(by_kind) == {
        "interoception.cost_pressure",
        "resource.cost_runway_days",
        "resource.runway_weeks",
        "financial.fraction_of_operating_float",
        "financial.fraction_of_improvement_fund",
        "financial.distance_to_reserve_floor",
        "financial.recurring_burn_ratio",
    }
    assert by_kind["resource.runway_weeks"].source == "cost_tracker"
    assert by_kind["resource.runway_weeks"].value == pytest.approx(10.0)
    assert bus.latest("financial.fraction_of_operating_float") is not None
