"""End-to-end Relay deployment on Chutes."""

from __future__ import annotations

from pathlib import Path

from xion_ops.deployers.base import Deployer
from xion_ops.services.arweave import ArweaveService
from xion_ops.services.chutes import ChutesService
from xion_ops.types import DeployContext, DeploymentResult, VerifyReport


class RelayChutesDeployer(Deployer):
    name = "relay-chutes"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        super().__init__(repo_root=repo_root)
        self.chutes = ChutesService(repo_root=self.repo_root)
        self.arweave = ArweaveService(repo_root=self.repo_root)

    def prepare(self, ctx: DeployContext) -> None:
        module_path = ctx.params.get("module_path", "xion_relay_chute.py")
        verify = self.chutes.verify_import(module_path)
        if not verify.ok:
            raise RuntimeError(f"Chutes module import preflight failed: {verify.details}")

    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        module_path = ctx.params.get("module_path", "xion_relay_chute.py")
        result = self.chutes.deploy_chute(module_path)
        if result.ok:
            warm = self.chutes.warmup(result.url)
            registry_tx = self.arweave.publish_relay_registry(ctx.params.get("registry_path", "ledgers/RELAY_REGISTRY.json"))
            details = dict(result.details)
            details.update({"warmup_ok": warm.ok, "relay_registry_tx": registry_tx.id})
            result = DeploymentResult(
                service=result.service,
                ok=warm.ok,
                id=result.id,
                url=result.url,
                tx=registry_tx.id,
                details=details,
            )
        return result

    def verify(self, result: DeploymentResult) -> VerifyReport:
        if not result.url:
            return VerifyReport(ok=False, command="chutes verify-cords", output="missing url")
        cords = self.chutes.verify_cords(result.url)
        return VerifyReport(ok=cords.ok, command="chutes verify-cords", output=str(cords.details))

    def rollback(self, result: DeploymentResult) -> None:
        if result.id:
            self.chutes.rollback_chute(result.id)

