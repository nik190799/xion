"""Local alert log provider."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LocalLogAlerter:
    """Append alerts to a local JSONL operator log."""

    provider_id: str = "local-log"
    path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("XION_ALERT_LOG", "ledgers/ALERT_LOG.jsonl")
        )
    )

    def notify(self, level: str, summary: str, body: str) -> None:
        row = {
            "schema_version": 1,
            "provider_id": self.provider_id,
            "level": level,
            "summary": summary,
            "body": body,
            "as_of_utc_ns": time.time_ns(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


__all__ = ["LocalLogAlerter"]
