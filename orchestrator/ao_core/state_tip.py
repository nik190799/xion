"""Pure helpers for height/root validation."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_state_root(state: dict[str, Any]) -> str:
    """Compute a deterministic hash of the state dict."""
    canonical = json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()

__all__ = ["compute_state_root"]
