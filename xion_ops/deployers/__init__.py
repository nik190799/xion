"""High-level deployers composed from service primitives."""

from __future__ import annotations

from xion_ops.deployers.base import Deployer
from xion_ops.deployers.base_contracts import BaseContractsDeployer
from xion_ops.deployers.relay_akash import RelayAkashDeployer
from xion_ops.deployers.relay_chutes import RelayChutesDeployer

ALL_DEPLOYERS: dict[str, type[Deployer]] = {
    RelayAkashDeployer.name: RelayAkashDeployer,
    RelayChutesDeployer.name: RelayChutesDeployer,
    BaseContractsDeployer.name: BaseContractsDeployer,
}

__all__ = ["ALL_DEPLOYERS", "BaseContractsDeployer", "Deployer", "RelayAkashDeployer", "RelayChutesDeployer"]

