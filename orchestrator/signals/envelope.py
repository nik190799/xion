from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Signal:
    """A single observation on the SignalBus (Phase 6.4.b)."""

    kind: str
    source: str
    value: Any
    timestamp_utc_ns: int
    methodology_hash: str
    confidence: float
    band: str | None
    schema_version: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Signal":
        return Signal(
            kind=str(d["kind"]),
            source=str(d["source"]),
            value=d["value"],
            timestamp_utc_ns=int(d["timestamp_utc_ns"]),
            methodology_hash=str(d["methodology_hash"]),
            confidence=float(d["confidence"]),
            band=None if d.get("band") is None else str(d["band"]),
            schema_version=int(d["schema_version"]),
        )
