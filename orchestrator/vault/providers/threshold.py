"""Threshold-unlock vault placeholder."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThresholdVaultStub:
    """Named provider for the future threshold ceremony vault.

    The provider is selectable so operator posture is explicit, but it refuses
    to fake pre-genesis threshold unlock behavior.
    """

    provider_id: str = "threshold"

    def unlock(self, name: str) -> str | None:
        raise NotImplementedError(
            "threshold credential vault is not wired pre-genesis; "
            "KW-VAULT-001 remains open until the threshold-unlock provider "
            "can retrieve secrets through the Vault Protocol."
        )

    def is_sealed(self) -> bool:
        return True

    def posture(self) -> str:
        return "sealed-doctrine-only"


__all__ = ["ThresholdVaultStub"]
