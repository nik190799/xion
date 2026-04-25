"""BillingProvider Protocol for inference-credit telemetry (Phase 6.9)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Balance:
    provider_id: str
    balance_usd: float
    balance_tao: float | None
    payment_address: str | None
    as_of_utc_ns: int


@dataclass(frozen=True)
class Payment:
    provider_id: str
    amount_tao: float
    amount_usd: float | None
    tx_hash: str | None
    timestamp_utc_ns: int


@dataclass(frozen=True)
class RunwayDays:
    days: float | None
    burn_rate_usd_per_day: float | None


@runtime_checkable
class BillingProvider(Protocol):
    provider_id: str

    def balance(self) -> Balance: ...

    def recent_payments(self, window_s: int) -> list[Payment]: ...

    def forecast_runway(self, burn_rate_usd_per_day: float | None) -> RunwayDays: ...


__all__ = ["Balance", "BillingProvider", "Payment", "RunwayDays"]
