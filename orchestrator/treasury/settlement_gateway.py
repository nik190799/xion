"""Settlement-chain gateway Protocol and provider loader."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


@runtime_checkable
class SettlementChain(Protocol):
    """Read-only settlement-chain boundary used by verifiers and runtime code."""

    provider_id: str

    def total_supply(self) -> str:
        """Return the token contract address whose cap/supply verifier checks."""

    def liquidity_locked(self) -> str:
        """Return the liquidity-lock contract address."""

    def authorities_root(self) -> dict[str, str]:
        """Return authority-bearing contract addresses."""

    def egress_window_used(self) -> int:
        """Return current egress-window usage if tracked by this chain."""


@dataclass(frozen=True, slots=True)
class BaseEvmSettlementChain:
    """Base Sepolia/Base EVM settlement-chain provider."""

    repo_root: Path
    provider_id: str = "base-evm"
    manifest_relpath: str = "genesis/CONTRACT_ADDRESSES.json"

    def _manifest(self) -> dict[str, object]:
        path = self.repo_root / self.manifest_relpath
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "testnet":
            raise RuntimeError(
                f"{self.manifest_relpath} status is {data.get('status')!r}, expected 'testnet'"
            )
        for field in ("xion_token", "imprint", "emission_controller", "liquidity_lock"):
            value = data.get(field)
            if not isinstance(value, str) or not _ADDRESS_RE.fullmatch(value):
                raise RuntimeError(f"{field} is not populated with an EVM address")
        return data

    def total_supply(self) -> str:
        return str(self._manifest()["xion_token"])

    def liquidity_locked(self) -> str:
        return str(self._manifest()["liquidity_lock"])

    def authorities_root(self) -> dict[str, str]:
        manifest = self._manifest()
        return {
            "xion_token": str(manifest["xion_token"]),
            "imprint": str(manifest["imprint"]),
            "emission_controller": str(manifest["emission_controller"]),
            "liquidity_lock": str(manifest["liquidity_lock"]),
        }

    def egress_window_used(self) -> int:
        return 0


@dataclass(frozen=True, slots=True)
class ArweaveSettlementChain:
    """Arweave-native settlement rail for AR-denominated operating runway."""

    repo_root: Path
    provider_id: str = "arweave-native"
    manifest_relpath: str = "genesis/TREASURY_VAULTS.json"

    def total_supply(self) -> str:
        return "AR:native-supply"

    def liquidity_locked(self) -> str:
        return "AR:not-applicable"

    def authorities_root(self) -> dict[str, str]:
        manifest_path = self.repo_root / self.manifest_relpath
        if not manifest_path.is_file():
            return {"arweave": "AR:manifest-missing"}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tx_id = str(manifest.get("arweave_registry_tx", "AR:registry-pending"))
        return {"arweave": tx_id, "treasury_manifest": self.manifest_relpath}

    def egress_window_used(self) -> int:
        return 0


@dataclass(frozen=True, slots=True)
class SettlementChainSettings:
    chain: str = "base"
    repo_root: Path = Path(".")

    @classmethod
    def from_env(cls, *, repo_root: Path | None = None) -> SettlementChainSettings:
        return cls(
            chain=os.environ.get("XION_SETTLEMENT_CHAIN", "base").strip().lower()
            or "base",
            repo_root=repo_root or Path("."),
        )


def get_settlement_chain(
    settings: SettlementChainSettings | None = None,
) -> SettlementChain:
    resolved = settings or SettlementChainSettings.from_env()
    if resolved.chain in {"", "base", "base-evm", "evm"}:
        return BaseEvmSettlementChain(repo_root=resolved.repo_root)
    if resolved.chain in {"ar", "arweave", "arweave-native"}:
        return ArweaveSettlementChain(repo_root=resolved.repo_root)
    raise ValueError(
        f"unsupported XION_SETTLEMENT_CHAIN={resolved.chain!r}; "
        "expected base or arweave"
    )


__all__ = [
    "ArweaveSettlementChain",
    "BaseEvmSettlementChain",
    "SettlementChain",
    "SettlementChainSettings",
    "get_settlement_chain",
]
