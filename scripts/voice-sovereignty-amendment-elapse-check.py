"""Check Invariant 18 amendment elapsed-window and cosign readiness."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

REQUIRED_WINDOW_DAYS = 14
REQUIRED_COSIGN = "Cold Root cosign"


def check(path: Path, *, now_ns: int | None = None) -> tuple[bool, str]:
    now = time.time_ns() if now_ns is None else now_ns
    if not path.is_file():
        return False, f"missing amendment ledger: {path}"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("proposal_path") != "docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md":
            continue
        observed = int(row.get("reflection_window_days_observed", 0))
        opened = int(row.get("as_of_utc_ns", now))
        elapsed_days = max(observed, (now - opened) // 86_400_000_000_000)
        requirements = set(row.get("ratification_requirements", []))
        has_cosign = REQUIRED_COSIGN in requirements and row.get("status") == "ratified"
        if elapsed_days >= REQUIRED_WINDOW_DAYS and has_cosign:
            return True, "Invariant 18 amendment elapsed window and Cold Root cosign satisfied"
        return False, "Invariant 18 amendment still pending elapsed window or Cold Root cosign"
    return False, "Invariant 18 amendment row not found"


def main() -> int:
    ok, message = check(Path("ledgers/AMENDMENT_LEDGER.jsonl"))
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
