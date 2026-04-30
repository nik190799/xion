"""ntfy.sh alerting provider."""

from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class NtfyAlerter:
    """Send alerts to ntfy when an operator topic is configured."""

    provider_id: str = "ntfy"
    topic_url: str = field(default_factory=lambda: os.environ.get("XION_NTFY_TOPIC_URL", ""))
    token: str = field(default_factory=lambda: os.environ.get("XION_NTFY_TOKEN", ""))

    def notify(self, level: str, summary: str, body: str) -> None:
        if not self.topic_url:
            raise NotImplementedError(
                "ntfy alerting provider requires XION_NTFY_TOPIC_URL; "
                "KW-ALERT-001 remains residual until hosted alert credentials "
                "are configured in operator posture."
            )
        payload = body.encode("utf-8")
        headers = {"Title": summary, "Priority": _priority(level)}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            self.topic_url,
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"ntfy alert failed with HTTP {response.status}")


def _priority(level: str) -> str:
    return "urgent" if level.lower() in {"critical", "error"} else "default"


__all__ = ["NtfyAlerter"]
