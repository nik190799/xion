"""Observability gateway Protocols and provider loader."""

from __future__ import annotations

import os
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from orchestrator.observability.providers import (
    HostedObservabilityStub,
    StdoutObservability,
)


@runtime_checkable
class MetricsEmitter(Protocol):
    provider_id: str

    def emit(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Emit one metric sample."""


@runtime_checkable
class LogSink(Protocol):
    provider_id: str

    def log(self, level: str, message: str, fields: dict[str, Any] | None = None) -> None:
        """Emit one structured log event."""


@runtime_checkable
class TraceExporter(Protocol):
    provider_id: str

    def span(self, name: str, fields: dict[str, Any] | None = None) -> AbstractContextManager[None]:
        """Return a context manager representing one trace span."""


@dataclass(frozen=True, slots=True)
class Observability:
    metrics: MetricsEmitter
    logs: LogSink
    traces: TraceExporter


@dataclass(frozen=True, slots=True)
class ObservabilitySettings:
    provider: str = "stdout"

    @classmethod
    def from_env(cls) -> ObservabilitySettings:
        return cls(
            provider=os.environ.get("XION_OBSERVABILITY_PROVIDER", "stdout")
            .strip()
            .lower()
            or "stdout"
        )


def get_observability(settings: ObservabilitySettings | None = None) -> Observability:
    """Load the configured observability provider bundle."""

    resolved = settings or ObservabilitySettings.from_env()
    if resolved.provider in {"", "stdout", "local", "json"}:
        provider = StdoutObservability()
    elif resolved.provider in {"hosted", "prometheus-grafana-loki-tempo"}:
        provider = HostedObservabilityStub()
    else:
        raise ValueError(
            f"unsupported XION_OBSERVABILITY_PROVIDER={resolved.provider!r}; "
            "expected stdout or hosted"
        )
    return Observability(metrics=provider, logs=provider, traces=provider)


__all__ = [
    "LogSink",
    "MetricsEmitter",
    "Observability",
    "ObservabilitySettings",
    "TraceExporter",
    "get_observability",
]
