"""Environment-backed development vault provider."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnvVault:
    """Vault provider that makes the existing env-secret posture explicit."""

    provider_id: str = "env"

    def unlock(self, name: str) -> str | None:
        value = os.environ.get(name, "")
        return value if value.strip() else None

    def is_sealed(self) -> bool:
        return False

    def posture(self) -> str:
        return "env-development"


__all__ = ["EnvVault"]
