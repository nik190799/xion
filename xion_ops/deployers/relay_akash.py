"""End-to-end Relay deployment on Akash."""

from __future__ import annotations

from pathlib import Path

from xion_ops.deployers.base import Deployer
from xion_ops.services.akash import AkashService
from xion_ops.services.arweave import ArweaveService
from xion_ops.types import DeployContext, DeploymentResult, VerifyReport


class RelayAkashDeployer(Deployer):
    name = "relay-akash"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        super().__init__(repo_root=repo_root)
        self.akash = AkashService(repo_root=self.repo_root)
        self.arweave = ArweaveService(repo_root=self.repo_root)

    def prepare(self, ctx: DeployContext) -> None:
        shortfalls = [report for report in self.akash.balances() if report.status != "ok"]
        if shortfalls:
            ids = ", ".join(report.wallet.id for report in shortfalls)
            raise RuntimeError(f"Akash funding shortfall before relay deploy: {ids}")

    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        sdl_path = Path(ctx.params.get("sdl_path", "infra/akash/relay-deployment.yaml"))
        prefer_provider = ctx.params.get("prefer_provider")
        result = self.akash.deploy_relay(self.repo_root / sdl_path, prefer_provider=prefer_provider)
        if result.ok:
            registry_tx = self.arweave.publish_relay_registry(ctx.params.get("registry_path", "ledgers/RELAY_REGISTRY.json"))
            details = dict(result.details)
            details["relay_registry_tx"] = registry_tx.id
            result = DeploymentResult(
                service=result.service,
                ok=True,
                id=result.id,
                url=result.url,
                tx=registry_tx.id,
                dseq=result.dseq,
                provider=result.provider,
                details=details,
            )
        return result

    def verify(self, result: DeploymentResult) -> VerifyReport:
        return VerifyReport(ok=result.ok and bool(result.url), command="akash health + relay registry publish")

    def rollback(self, result: DeploymentResult) -> None:
        if result.dseq:
            self.akash.close_deployment(result.dseq)

