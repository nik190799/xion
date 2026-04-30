"""Credential vault gateway Protocol and provider loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from orchestrator.vault.providers import EnvVault, ThresholdVaultStub


@runtime_checkable
class Vault(Protocol):
    """Stable credential retrieval boundary for orchestrator startup."""

    provider_id: str

    def unlock(self, name: str) -> str | None:
        """Return a named secret, or None if the provider does not hold it."""

    def is_sealed(self) -> bool:
        """Return whether the vault is unavailable for secret material."""

    def posture(self) -> str:
        """Return an operator-readable custody posture."""


@dataclass(frozen=True, slots=True)
class VaultSettings:
    provider: str = "env"

    @classmethod
    def from_env(cls) -> VaultSettings:
        return cls(
            provider=os.environ.get("XION_VAULT_PROVIDER", "env").strip().lower()
            or "env"
        )


def get_vault(settings: VaultSettings | None = None) -> Vault:
    """Load the configured credential vault provider."""

    resolved = settings or VaultSettings.from_env()
    if resolved.provider in {"", "env", "local", "development"}:
        return EnvVault()
    if resolved.provider in {"threshold", "ceremony"}:
        return ThresholdVaultStub()
    raise ValueError(
        f"unsupported XION_VAULT_PROVIDER={resolved.provider!r}; "
        "expected env or threshold"
    )


__all__ = ["Vault", "VaultSettings", "get_vault"]
