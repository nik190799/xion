"""Hosted observability provider placeholder."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HostedObservabilityStub:
    """Selectable placeholder for Prometheus/Grafana/Loki/Tempo wiring."""

    provider_id: str = "prometheus-grafana-loki-tempo"

    def emit(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        raise NotImplementedError(
            "hosted observability stack is not wired pre-genesis; "
            "KW-OBS-001 remains open until Prometheus/Grafana/Loki/Tempo "
            "providers land behind the observability gateway."
        )

    def log(self, level: str, message: str, fields: dict[str, Any] | None = None) -> None:
        raise NotImplementedError(
            "hosted observability stack is not wired pre-genesis; "
            "KW-OBS-001 remains open until Prometheus/Grafana/Loki/Tempo "
            "providers land behind the observability gateway."
        )

    @contextmanager
    def span(self, name: str, fields: dict[str, Any] | None = None) -> Iterator[None]:
        raise NotImplementedError(
            "hosted observability stack is not wired pre-genesis; "
            "KW-OBS-001 remains open until Prometheus/Grafana/Loki/Tempo "
            "providers land behind the observability gateway."
        )
        yield  # pragma: no cover


__all__ = ["HostedObservabilityStub"]
