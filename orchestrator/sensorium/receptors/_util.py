from __future__ import annotations

import time
from typing import Any

from orchestrator.signals.envelope import Signal

METH_LEGACY = "2222222222222222222222222222222222222222222222222222222222222222"


def sense_signal(
    *,
    kind: str,
    receptor_id: str,
    value: Any,
    methodology_hash: str = METH_LEGACY,
    confidence: float = 1.0,
    band: str | None = None,
    schema_version: int = 1,
) -> Signal:
    return Signal(
        kind=kind,
        source=receptor_id,
        value=value,
        timestamp_utc_ns=time.time_ns(),
        methodology_hash=methodology_hash,
        confidence=confidence,
        band=band,
        schema_version=schema_version,
    )
