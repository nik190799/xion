"""Phase 6.8 cost tracker.

This module measures spend pressure. It does not approve spend, arbitrate
headroom, or write the future Spend Authority ledger.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum

from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.bus import SignalBus
from orchestrator.signals.envelope import Signal


class TreasuryBucket(str, Enum):
    OPERATING_FLOAT = "Operating Float"
    IMPROVEMENT_FUND = "Improvement Fund"
    RAINY_DAY_RESERVE = "Rainy-Day Reserve"
    FOUNDATION_RESERVE = "Foundation Reserve"
    TREASURY = "Treasury"


@dataclass(frozen=True)
class TreasurySnapshot:
    bucket_balances: dict[TreasuryBucket, float]
    weekly_non_discretionary_burn: float
    reserve_floor: float
    trailing_recurring_inflow_weekly: float = 0.0
    existing_recurring_burn_weekly: float = 0.0
    as_of_utc_ns: int = field(default_factory=time.time_ns)

    def balance(self, bucket: TreasuryBucket) -> float:
        return max(0.0, float(self.bucket_balances.get(bucket, 0.0)))


@dataclass(frozen=True)
class DebitAttribution:
    bucket: TreasuryBucket
    amount: float
    purpose: str = ""
    recurring_burn_weekly_delta: float = 0.0
    as_of_utc_ns: int = field(default_factory=time.time_ns)


class CostTracker:
    """Bucket-attributed spend pressure calculator for Phase 6.8."""

    def __init__(self, snapshot: TreasurySnapshot) -> None:
        self._snapshot = snapshot
        self._debits: list[DebitAttribution] = []

    @property
    def debits(self) -> tuple[DebitAttribution, ...]:
        return tuple(self._debits)

    def record_debit(
        self,
        *,
        bucket: TreasuryBucket | str,
        amount: float,
        purpose: str = "",
        recurring_burn_weekly_delta: float = 0.0,
        as_of_utc_ns: int | None = None,
    ) -> DebitAttribution:
        parsed_bucket = bucket if isinstance(bucket, TreasuryBucket) else TreasuryBucket(bucket)
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if recurring_burn_weekly_delta < 0:
            raise ValueError("recurring_burn_weekly_delta must be non-negative")
        debit = DebitAttribution(
            bucket=parsed_bucket,
            amount=float(amount),
            purpose=purpose,
            recurring_burn_weekly_delta=float(recurring_burn_weekly_delta),
            as_of_utc_ns=as_of_utc_ns if as_of_utc_ns is not None else time.time_ns(),
        )
        self._debits.append(debit)
        return debit

    def total_debits(self, bucket: TreasuryBucket | str) -> float:
        parsed_bucket = bucket if isinstance(bucket, TreasuryBucket) else TreasuryBucket(bucket)
        return sum(d.amount for d in self._debits if d.bucket == parsed_bucket)

    def runway_weeks(self) -> float:
        burn = float(self._snapshot.weekly_non_discretionary_burn)
        if burn <= 0.0:
            return math.inf
        return self._snapshot.balance(TreasuryBucket.OPERATING_FLOAT) / burn

    def fraction_of_operating_float(self, amount: float | None = None) -> float:
        return self._fraction_of_bucket(
            TreasuryBucket.OPERATING_FLOAT,
            self.total_debits(TreasuryBucket.OPERATING_FLOAT) if amount is None else amount,
        )

    def fraction_of_improvement_fund(self, amount: float | None = None) -> float:
        return self._fraction_of_bucket(
            TreasuryBucket.IMPROVEMENT_FUND,
            self.total_debits(TreasuryBucket.IMPROVEMENT_FUND) if amount is None else amount,
        )

    def distance_to_reserve_floor(self) -> float:
        floor = float(self._snapshot.reserve_floor)
        reserves = (
            self._snapshot.balance(TreasuryBucket.RAINY_DAY_RESERVE)
            + self._snapshot.balance(TreasuryBucket.FOUNDATION_RESERVE)
        )
        if floor <= 0.0:
            return math.inf if reserves > 0.0 else 0.0
        return (reserves - floor) / floor

    def recurring_burn_ratio(self) -> float:
        recurring_delta = sum(d.recurring_burn_weekly_delta for d in self._debits)
        recurring_total = self._snapshot.existing_recurring_burn_weekly + recurring_delta
        inflow = float(self._snapshot.trailing_recurring_inflow_weekly)
        if inflow > 0.0:
            return recurring_total / inflow
        floor = float(self._snapshot.reserve_floor)
        reserve_headroom = max(0.0, self.distance_to_reserve_floor() * floor)
        if reserve_headroom > 0.0:
            return recurring_total / reserve_headroom
        return math.inf if recurring_total > 0.0 else 0.0

    def financial_vitality_signals(self) -> list[Signal]:
        runway = self.runway_weeks()
        runway_for_bus = 1_000_000.0 if math.isinf(runway) else runway
        cost_pressure = 1.0 - min(1.0, max(0.0, runway_for_bus / 52.0))
        return [
            sense_signal(
                kind="interoception.cost_pressure",
                receptor_id="cost_tracker",
                value=cost_pressure,
            ),
            sense_signal(
                kind="resource.cost_runway_days",
                receptor_id="cost_tracker",
                value=runway_for_bus * 7.0,
            ),
            sense_signal(
                kind="resource.runway_weeks",
                receptor_id="cost_tracker",
                value=runway_for_bus,
            ),
            sense_signal(
                kind="financial.fraction_of_operating_float",
                receptor_id="cost_tracker",
                value=self.fraction_of_operating_float(),
            ),
            sense_signal(
                kind="financial.fraction_of_improvement_fund",
                receptor_id="cost_tracker",
                value=self.fraction_of_improvement_fund(),
            ),
            sense_signal(
                kind="financial.distance_to_reserve_floor",
                receptor_id="cost_tracker",
                value=self._finite_for_bus(self.distance_to_reserve_floor()),
            ),
            sense_signal(
                kind="financial.recurring_burn_ratio",
                receptor_id="cost_tracker",
                value=self._finite_for_bus(self.recurring_burn_ratio()),
            ),
        ]

    def emit_financial_vitality(self, bus: SignalBus) -> list[Signal]:
        return bus.publish(self.financial_vitality_signals())

    def _fraction_of_bucket(self, bucket: TreasuryBucket, amount: float) -> float:
        balance = self._snapshot.balance(bucket)
        if balance <= 0.0:
            return math.inf if amount > 0.0 else 0.0
        return float(amount) / balance

    @staticmethod
    def _finite_for_bus(value: float) -> float:
        if math.isinf(value):
            return 1_000_000.0
        return value


__all__ = [
    "CostTracker",
    "DebitAttribution",
    "TreasuryBucket",
    "TreasurySnapshot",
]
