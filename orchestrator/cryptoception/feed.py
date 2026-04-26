"""Active crypto policy feed for Invariant 14 checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def active_crypto_policy(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "genesis" / "crypto_policy_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["active_crypto_policy"]
