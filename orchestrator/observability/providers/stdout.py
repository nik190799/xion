"""Stdout/local structured observability provider."""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class StdoutObservability:
    """Emit metrics, logs, and trace spans as structured JSON to stdout."""

    provider_id: str = "stdout"

    def emit(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        self._write({"kind": "metric", "name": name, "value": value, "tags": tags or {}})

    def log(self, level: str, message: str, fields: dict[str, Any] | None = None) -> None:
        self._write(
            {"kind": "log", "level": level, "message": message, "fields": fields or {}}
        )

    @contextmanager
    def span(self, name: str, fields: dict[str, Any] | None = None) -> Iterator[None]:
        started = time.monotonic_ns()
        self._write({"kind": "span_start", "name": name, "fields": fields or {}})
        try:
            yield
        finally:
            self._write(
                {
                    "kind": "span_end",
                    "name": name,
                    "duration_ns": time.monotonic_ns() - started,
                    "fields": fields or {},
                }
            )

    def _write(self, payload: dict[str, Any]) -> None:
        row = {
            "schema_version": 1,
            "provider_id": self.provider_id,
            "as_of_utc_ns": time.time_ns(),
            **payload,
        }
        print(json.dumps(row, sort_keys=True, separators=(",", ":")), file=sys.stdout)


__all__ = ["StdoutObservability"]
