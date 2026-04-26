"""Operator profile registry.

Profiles are runtime postures, not feature flags. They name which trust
surfaces are allowed before the API process accepts traffic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ProfileName = Literal["local_only", "sovereign"]


@dataclass(frozen=True)
class OperatorProfile:
    name: ProfileName
    allows_centralized_fallbacks: bool


LOCAL_ONLY = OperatorProfile(name="local_only", allows_centralized_fallbacks=False)
SOVEREIGN = OperatorProfile(name="sovereign", allows_centralized_fallbacks=False)
_PROFILES: dict[str, OperatorProfile] = {
    LOCAL_ONLY.name: LOCAL_ONLY,
    SOVEREIGN.name: SOVEREIGN,
}


class ProfileConfigError(RuntimeError):
    """Raised when XION_PROFILE names an unknown runtime posture."""


def current_profile() -> OperatorProfile:
    raw = os.environ.get("XION_PROFILE", "").strip().lower()
    if raw == "":
        return LOCAL_ONLY
    try:
        return _PROFILES[raw]
    except KeyError as exc:
        raise ProfileConfigError(
            f"unknown XION_PROFILE={raw!r}; expected one of {sorted(_PROFILES)}"
        ) from exc


__all__ = [
    "LOCAL_ONLY",
    "SOVEREIGN",
    "OperatorProfile",
    "ProfileConfigError",
    "ProfileName",
    "current_profile",
]
