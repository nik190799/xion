"""Pushover alerting provider."""

from __future__ import annotations

import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PushoverAlerter:
    """Send alerts through Pushover when operator credentials are configured."""

    provider_id: str = "pushover"
    api_url: str = "https://api.pushover.net/1/messages.json"
    token: str = field(default_factory=lambda: os.environ.get("XION_PUSHOVER_TOKEN", ""))
    user_key: str = field(default_factory=lambda: os.environ.get("XION_PUSHOVER_USER_KEY", ""))

    def notify(self, level: str, summary: str, body: str) -> None:
        if not self.token or not self.user_key:
            raise NotImplementedError(
                "Pushover alerting provider requires XION_PUSHOVER_TOKEN and "
                "XION_PUSHOVER_USER_KEY; KW-ALERT-001 remains residual until "
                "hosted alert credentials are configured in operator posture."
            )
        payload = urllib.parse.urlencode(
            {
                "token": self.token,
                "user": self.user_key,
                "title": summary,
                "message": body,
                "priority": "1" if level.lower() in {"critical", "error"} else "0",
            }
        ).encode("utf-8")
        request = urllib.request.Request(self.api_url, data=payload, method="POST")
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise RuntimeError(f"Pushover alert failed with HTTP {response.status}")


__all__ = ["PushoverAlerter"]
