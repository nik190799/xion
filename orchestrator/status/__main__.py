"""Publish a local/public status snapshot from CLI."""

from __future__ import annotations

import json
import sys
import time

from orchestrator.status import get_status_publisher


def main() -> int:
    raw = sys.stdin.read().strip()
    snapshot = json.loads(raw) if raw else {}
    snapshot.setdefault("as_of_utc_ns", time.time_ns())
    locator = get_status_publisher().publish(snapshot)
    print(f"status-publisher: OK ({locator})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
