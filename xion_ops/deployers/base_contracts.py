"""Base EVM contract deployment orchestration."""

from __future__ import annotations

from pathlib import Path

from xion_ops.deployers.base import Deployer
from xion_ops.services.arweave import ArweaveService
from xion_ops.services.base_evm import BaseEvmService
from xion_ops.types import DeployContext, DeploymentResult, VerifyReport


class BaseContractsDeployer(Deployer):
    name = "base-contracts"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        super().__init__(repo_root=repo_root)
        self.base_evm = BaseEvmService(repo_root=self.repo_root)
        self.arweave = ArweaveService(repo_root=self.repo_root)

    def prepare(self, ctx: DeployContext) -> None:
        network = ctx.params.get("network", "base-sepolia")
        shortfalls = [
            report
            for report in self.base_evm.balances()
            if report.wallet.network == network and report.status != "ok"
        ]
        if shortfalls:
            ids = ", ".join(report.wallet.id for report in shortfalls)
            raise RuntimeError(f"Base EVM funding shortfall before contract deploy: {ids}")

    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        network = ctx.params.get("network", "base-sepolia")
        mode = ctx.params.get("mode", "full")
        if mode == "treasury-rotation":
            return self.redeploy_treasury_with_rotation(network)
        return self.deploy_full(network)

    def deploy_full(self, network: str) -> DeploymentResult:
        treasury = self.base_evm.deploy_treasury(network)
        return DeploymentResult(
            service=self.base_evm.name,
            ok=treasury.ok,
            id="base-contracts",
            details={"network": network, "treasury": treasury.details},
        )

    def redeploy_treasury_with_rotation(self, network: str) -> DeploymentResult:
        treasury = self.base_evm.deploy_treasury(network)
        audit_tx = self.arweave.publish_treasury_audit()
        return DeploymentResult(
            service=self.base_evm.name,
            ok=treasury.ok,
            id="base-contracts-rotation",
            tx=audit_tx.id,
            details={"network": network, "treasury": treasury.details, "audit_tx": audit_tx.id},
        )

    def verify(self, result: DeploymentResult) -> VerifyReport:
        return VerifyReport(ok=result.ok, command="xion-verify treasury treasury-flow authorities")

    def rollback(self, _result: DeploymentResult) -> None:
        # EVM broadcasts are one-way doors. Rollback is documentary only.
        return None

