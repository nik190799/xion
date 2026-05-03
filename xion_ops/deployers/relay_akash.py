"""End-to-end Relay deployment on Akash."""

from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path

from xion_ops.deployers.base import Deployer
from xion_ops.services.akash import AkashService
from xion_ops.services.arweave import ArweaveService
from xion_ops.types import DeployContext, DeploymentResult, VerifyReport


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name)
    return bool(raw and raw.strip().lower() in ("1", "true", "yes", "on"))


class RelayAkashDeployer(Deployer):
    name = "relay-akash"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        super().__init__(repo_root=repo_root)
        self.akash = AkashService(repo_root=self.repo_root)
        self.arweave = ArweaveService(repo_root=self.repo_root)

    def prepare(self, ctx: DeployContext) -> None:
        if _env_truthy("XION_AKASH_PREPARE_WAIT_BME"):
            if not self.akash.wait_for_ledger_executed():
                raise RuntimeError(
                    "BME ledger still has non-executed rows (XION_AKASH_PREPARE_WAIT_BME); "
                    "wait for mint-act to settle or tune XION_AKASH_BME_TIMEOUT_SEC."
                )
        if _env_truthy("XION_AKASH_REQUIRE_UACT"):
            minimum = float(os.environ.get("XION_AKASH_MIN_UACT", "1"))
            if self.akash.uact_balance() < minimum:
                raise RuntimeError(
                    f"Akash uact below XION_AKASH_MIN_UACT ({minimum}); "
                    "fund escrow via BME mint-act (see docs/runbooks/AKASH_RELAY_DEPLOY.md)."
                )
        shortfalls = [report for report in self.akash.balances() if report.status != "ok"]
        if shortfalls:
            ids = ", ".join(report.wallet.id for report in shortfalls)
            raise RuntimeError(f"Akash funding shortfall before relay deploy: {ids}")

    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        sdl_path = Path(ctx.params.get("sdl_path", "infra/akash/relay-deployment.yaml"))
        prefer_raw = ctx.params.get("prefer_provider")
        prefer_provider = prefer_raw if isinstance(prefer_raw, str) else None
        rejected_raw = ctx.params.get("rejected_providers") or ctx.params.get("exclude_provider")
        rejected_providers: set[str] | None = None
        if isinstance(rejected_raw, set):
            rejected_providers = {str(x) for x in rejected_raw}
        elif isinstance(rejected_raw, (list, tuple)):
            rejected_providers = {str(x) for x in rejected_raw}
        result = self.akash.deploy_relay(
            self.repo_root / sdl_path,
            prefer_provider=prefer_provider,
            rejected_providers=rejected_providers,
        )
        if result.ok and ctx.params.get("publish_registry", True):
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
            with suppress(Exception):
                # `AkashService.deploy_relay` already attempts rollback on
                # failure. A second close can legitimately return "Deployment
                # closed"; keep the original deployment evidence visible.
                self.akash.close_deployment(result.dseq)

