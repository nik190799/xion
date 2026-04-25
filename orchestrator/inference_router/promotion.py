"""ModelPromotion ceremony state machine (Phase 6.9)."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PromotionState = Literal["audition", "canary", "primary", "retired"]
_ORDER: dict[PromotionState, int] = {
    "audition": 0,
    "canary": 1,
    "primary": 2,
    "retired": 3,
}


@dataclass(frozen=True)
class PromotionEvidence:
    model_slug: str
    from_state: PromotionState | None
    to_state: PromotionState
    evidence_bundle_hash: str
    approver: str
    cost_delta: float | None = None
    quality_delta: float | None = None
    refusal_delta: float | None = None


def validate_transition(from_state: PromotionState | None, to_state: PromotionState) -> None:
    if from_state is None:
        if to_state != "audition":
            raise ValueError("new model must enter at audition")
        return
    if _ORDER[to_state] != _ORDER[from_state] + 1:
        raise ValueError(f"invalid transition {from_state!r} -> {to_state!r}")


def append_promotion_row(path: Path, evidence: PromotionEvidence) -> dict[str, object]:
    validate_transition(evidence.from_state, evidence.to_state)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp_utc_ns": time.time_ns(),
        "model_slug": evidence.model_slug,
        "from_state": evidence.from_state,
        "to_state": evidence.to_state,
        "evidence_bundle_hash": evidence.evidence_bundle_hash,
        "approver": evidence.approver,
        "cost_delta": evidence.cost_delta,
        "quality_delta": evidence.quality_delta,
        "refusal_delta": evidence.refusal_delta,
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
    finally:
        os.close(fd)
    return row


__all__ = ["PromotionEvidence", "PromotionState", "append_promotion_row", "validate_transition"]
