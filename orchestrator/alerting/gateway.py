"""Operational alerting gateway Protocol and provider loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from orchestrator.alerting.providers import LocalLogAlerter, NtfyAlerter, PushoverAlerter


@runtime_checkable
class Alerter(Protocol):
    """Stable boundary for operator-visible alerts."""

    provider_id: str

    def notify(self, level: str, summary: str, body: str) -> None:
        """Emit an alert or raise a provider-specific failure."""


@dataclass(frozen=True, slots=True)
class AlerterSettings:
    provider: str = "local-log"

    @classmethod
    def from_env(cls) -> AlerterSettings:
        return cls(
            provider=os.environ.get("XION_ALERT_PROVIDER", "local-log")
            .strip()
            .lower()
            or "local-log"
        )


def get_alerter(settings: AlerterSettings | None = None) -> Alerter:
    """Load the configured alerting provider."""

    resolved = settings or AlerterSettings.from_env()
    if resolved.provider in {"", "local", "local-log", "file"}:
        return LocalLogAlerter()
    if resolved.provider == "ntfy":
        return NtfyAlerter()
    if resolved.provider == "pushover":
        return PushoverAlerter()
    raise ValueError(
        f"unsupported XION_ALERT_PROVIDER={resolved.provider!r}; "
        "expected local-log, ntfy, or pushover"
    )


__all__ = ["Alerter", "AlerterSettings", "get_alerter"]
