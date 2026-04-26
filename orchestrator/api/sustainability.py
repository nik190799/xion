"""GET /sustainability readout backed by the Phase 6.8 cost tracker."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

from orchestrator.cost_tracker import CostTracker, TreasuryBucket, TreasurySnapshot


def default_sustainability_snapshot() -> TreasurySnapshot:
    """Genesis-default local snapshot used until live treasury balances exist."""
    return TreasurySnapshot(
        bucket_balances={
            TreasuryBucket.OPERATING_FLOAT: 12_000.0,
            TreasuryBucket.IMPROVEMENT_FUND: 4_000.0,
            TreasuryBucket.RAINY_DAY_RESERVE: 8_000.0,
            TreasuryBucket.FOUNDATION_RESERVE: 2_000.0,
            TreasuryBucket.TREASURY: 26_000.0,
        },
        weekly_non_discretionary_burn=500.0,
        reserve_floor=6_000.0,
        trailing_recurring_inflow_weekly=1_000.0,
        existing_recurring_burn_weekly=250.0,
        as_of_utc_ns=time.time_ns(),
    )


def sustainability_readout(snapshot: TreasurySnapshot | None = None) -> dict[str, float | int | str]:
    tracker = CostTracker(snapshot or default_sustainability_snapshot())
    return {
        "schema_version": "1.0.0",
        "as_of_utc_ns": tracker._snapshot.as_of_utc_ns,  # intentionally mirrors snapshot timestamp
        "runway_weeks": tracker.runway_weeks(),
        "fraction_of_operating_float": tracker.fraction_of_operating_float(),
        "fraction_of_improvement_fund": tracker.fraction_of_improvement_fund(),
        "distance_to_reserve_floor": tracker.distance_to_reserve_floor(),
        "recurring_burn_ratio": tracker.recurring_burn_ratio(),
    }


def register_sustainability_route(app: FastAPI) -> None:
    @app.get("/sustainability", summary="Cost-pressure and treasury-readiness readout.")
    def get_sustainability() -> dict[str, float | int | str]:
        return sustainability_readout()


__all__ = [
    "default_sustainability_snapshot",
    "register_sustainability_route",
    "sustainability_readout",
]
