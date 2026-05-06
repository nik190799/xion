"""End-to-end Relay deployment on Chutes."""

from __future__ import annotations

import json
from pathlib import Path

from xion_ops.deployers.base import Deployer
from xion_ops.services.arweave import ArweaveService
from xion_ops.services.chutes import DEFAULT_CHUTE_REF, ChutesService, verify_module_relative_path
from xion_ops.types import DeployContext, DeploymentRecord, DeploymentResult, VerifyReport


def _registry_chutes_https_base(repo_root: Path, *, registry_path: str) -> str | None:
    """Return ``relays[1].endpoint`` when the committed registry row is a Chutes HTTPS base."""

    path = repo_root / registry_path
    if not path.is_file():
        return None
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    relays = data.get("relays")
    if not isinstance(relays, list) or len(relays) < 2:
        return None
    row = relays[1]
    if not isinstance(row, dict) or row.get("substrate") != "chutes":
        return None
    ep = str(row.get("endpoint") or "").strip().rstrip("/")
    return ep if ep.startswith("https://") else None


class RelayChutesDeployer(Deployer):
    name = "relay-chutes"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        super().__init__(repo_root=repo_root)
        self.chutes = ChutesService(repo_root=self.repo_root)
        self.arweave = ArweaveService(repo_root=self.repo_root)

    def prepare(self, ctx: DeployContext) -> None:
        chute_or_path = ctx.params.get("module_path", DEFAULT_CHUTE_REF)
        vpath = verify_module_relative_path(str(chute_or_path))
        verify = self.chutes.verify_import(vpath)
        if not verify.ok:
            raise RuntimeError(f"Chutes module import preflight failed: {verify.details}")

    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        chute_ref = str(ctx.params.get("module_path", DEFAULT_CHUTE_REF))
        accept_fee = bool(ctx.params.get("accept_fee", False))
        public = bool(ctx.params.get("public", False))
        debug = bool(ctx.params.get("debug", False))
        raw_logo = ctx.params.get("logo")
        logo = str(raw_logo).strip() if isinstance(raw_logo, str) and raw_logo.strip() else None
        raw_cp = ctx.params.get("config_path")
        config_path = str(raw_cp).strip() if isinstance(raw_cp, str) and raw_cp.strip() else None

        details: dict[str, object] = {}

        build_wait = bool(ctx.params.get("build_wait", False))
        include_cwd = bool(ctx.params.get("include_cwd", False))

        if build_wait:
            bres = self.chutes.build_chute_image(
                chute_ref,
                wait=True,
                public=public,
                debug=debug,
                logo=logo,
                include_cwd=include_cwd,
                config_path=config_path,
            )
            details["build"] = dict(bres.details or {})
            details["build_ok"] = bres.ok
            if not bres.ok:
                return DeploymentResult(
                    service="chutes",
                    ok=False,
                    id=bres.id,
                    url=None,
                    details=details,
                )

        result = self.chutes.deploy_chute(
            chute_ref,
            accept_fee=accept_fee,
            public=public,
            debug=debug,
            logo=logo,
            config_path=config_path,
        )
        details.update(dict(result.details or {}))
        details["deploy_command_ok"] = result.ok

        if not result.ok:
            return DeploymentResult(
                service=result.service,
                ok=False,
                id=result.id,
                url=result.url,
                details=details,
            )

        warm_max = ctx.params.get("warmup_max_wait_seconds")
        warm_interval = ctx.params.get("warmup_interval_seconds")
        raw_slug = ctx.params.get("platform_warmup_slug")
        plat_slug = str(raw_slug).strip() if isinstance(raw_slug, str) and raw_slug.strip() else None

        mx = float(warm_max) if isinstance(warm_max, (int, float)) else None
        iv = float(warm_interval) if isinstance(warm_interval, (int, float)) else None

        reg_path = str(ctx.params.get("registry_path", "ledgers/RELAY_REGISTRY.json"))
        warm_url = ((result.url or "").strip() or self.chutes.base_url().strip()) or None
        if not warm_url:
            warm_url = _registry_chutes_https_base(self.repo_root, registry_path=reg_path)
        warm = self.chutes.warmup_until_cords_green(
            warm_url,
            max_wait_seconds=mx if mx is not None else None,
            interval_seconds=iv if iv is not None else None,
            platform_warmup_slug=plat_slug,
        )
        details["warmup_ok"] = warm.ok
        details["warmup"] = dict(warm.details)

        publish = bool(ctx.params.get("publish_registry", True))
        tx_id = None

        if not warm.ok:
            return DeploymentResult(
                service=result.service,
                ok=False,
                id=result.id,
                url=result.url or warm_url or None,
                tx=None,
                details=details,
            )

        overall_ok = True
        out_url = result.url or warm_url or None

        if publish:
            try:
                registry_tx = self.arweave.publish_relay_registry(str(ctx.params.get("registry_path", "ledgers/RELAY_REGISTRY.json")))
                tx_id = registry_tx.id
                details["relay_registry_tx"] = registry_tx.id
            except Exception as exc:  # pragma: no cover — network / wallet paths
                details["relay_registry_publish_error"] = str(exc)
                overall_ok = False
        else:
            details["relay_registry_publish_skipped"] = True

        return DeploymentResult(
            service=result.service,
            ok=overall_ok,
            id=result.id,
            url=out_url,
            tx=tx_id,
            details=details,
        )

    def verify(self, result: DeploymentResult) -> VerifyReport:
        target = result.url or self.chutes.base_url()
        if not target:
            return VerifyReport(ok=False, command="chutes verify-cords", output="missing url")
        cords = self.chutes.verify_cords(target.rstrip("/"))
        return VerifyReport(ok=cords.ok, command="chutes verify-cords", output=str(cords.details))

    def rollback(self, result: DeploymentResult) -> None:
        if result.id:
            self.chutes.rollback_chute(result.id)

    def run(self, ctx: DeployContext) -> DeploymentRecord:
        """Like :meth:`Deployer.run` but do not rollback on warmup/cord-timeout alone (live deploy exists)."""

        self.prepare(ctx)
        outcome = self.deploy(ctx)
        if outcome.details.get("deploy_command_ok") is False:
            self.rollback(outcome)
        verify = self.verify(outcome)
        return self.record(outcome, verify, ctx)
