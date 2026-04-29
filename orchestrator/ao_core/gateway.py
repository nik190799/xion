"""AO Core gateway Protocol and provider loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from orchestrator.ao_core.client import LegacynetAOCoreGateway, LocalnetAOCoreGateway


@runtime_checkable
class AOCoreGateway(Protocol):
    """Stable AO Core boundary used by Relay/runtime code."""

    async def commit_state(
        self,
        tip_height: int,
        state_root_sha256: str,
        correlation_id: str,
    ) -> bool:
        """Commit a state-chain tip to the configured AO substrate."""


@dataclass(frozen=True, slots=True)
class AOCoreGatewaySettings:
    """Operator-selectable AO Core substrate settings."""

    substrate: str = "localnet"
    process_id: str = ""
    aos_binary_path: str = "aos"
    ao_gateway_url: str = "http://localhost:4000"

    @classmethod
    def from_env(cls) -> AOCoreGatewaySettings:
        return cls(
            substrate=os.environ.get("XION_AO_CORE_SUBSTRATE", "localnet")
            .strip()
            .lower(),
            process_id=os.environ.get("XION_AO_PROCESS_ID", "").strip(),
            aos_binary_path=os.environ.get("XION_AOS_BINARY_PATH", "aos").strip()
            or "aos",
            ao_gateway_url=os.environ.get(
                "XION_AO_GATEWAY_URL",
                "http://localhost:4000",
            ).strip()
            or "http://localhost:4000",
        )


def get_ao_core_gateway(
    settings: AOCoreGatewaySettings | None = None,
) -> AOCoreGateway:
    """Load the configured AO Core gateway provider."""

    resolved = settings or AOCoreGatewaySettings.from_env()
    if resolved.substrate in {"", "local", "localnet", "dev"}:
        return LocalnetAOCoreGateway(
            process_id=resolved.process_id,
            aos_binary_path=resolved.aos_binary_path,
        )
    if resolved.substrate in {"legacynet", "mainnet", "ao"}:
        return LegacynetAOCoreGateway(
            process_id=resolved.process_id,
            ao_gateway_url=resolved.ao_gateway_url,
        )
    raise ValueError(
        "unsupported XION_AO_CORE_SUBSTRATE="
        f"{resolved.substrate!r}; expected localnet or legacynet"
    )


__all__ = ["AOCoreGateway", "AOCoreGatewaySettings", "get_ao_core_gateway"]
