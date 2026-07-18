"""Xion Relay deployment on Aleph Cloud (tertiary substrate leg).

Flow: ``aleph instance create`` (hold-tier by default) -> poll ``instance
list`` for allocation + IP -> SSH provision (docker + relay container) ->
health probe. Registry publication stays manual/operator-gated: the discovery
verifier pins relays[0]=akash and relays[1]=chutes; the Aleph row appends as
relays[2] via ``--publish-registry`` only after both health gates pass.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from xion_ops.deployers.base import Deployer
from xion_ops.services.aleph_cloud import AlephCloudService
from xion_ops.types import DeployContext, DeploymentResult, VerifyReport

_PROVISION_SCRIPT = "infra/aleph/provision-relay.sh"


class RelayAlephDeployer(Deployer):
    name = "relay-aleph"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        super().__init__(repo_root=repo_root)
        self.aleph = AlephCloudService(repo_root=self.repo_root)

    def prepare(self, ctx: DeployContext) -> None:
        if not self.aleph.cli_available():
            raise RuntimeError("aleph CLI unavailable in WSL; pipx install aleph-client")
        address = self.aleph.account_address()
        ctx.params["aleph_address"] = address

    def deploy(self, ctx: DeployContext) -> DeploymentResult:
        name = str(ctx.params.get("instance_name") or "xion-relay-aleph")
        compute_units = int(ctx.params.get("compute_units") or 2)
        details: dict[str, object] = {"instance_name": name, "compute_units": compute_units}

        existing = self._find_instance(name)
        if existing is None:
            create = self.aleph.create_instance(name, compute_units=compute_units)
            details["create_stdout_tail"] = create.stdout[-2000:]
            existing = self._wait_for_instance(name, timeout_s=int(os.environ.get("XION_ALEPH_ALLOC_WAIT_SEC", "600")))
        item_hash = str(existing.get("item_hash") or existing.get("hash") or "")
        details["item_hash"] = item_hash
        host = self._instance_host(existing)
        details["host"] = host
        if not host:
            details["instance_raw"] = json.dumps(existing)[:2000]
            return DeploymentResult(service="aleph", ok=False, id=item_hash or name, url=None, tx=None, details=details)

        provision = self.aleph.ssh_provision(host, _PROVISION_SCRIPT)
        details["provision_tail"] = provision.stdout[-1500:]
        provision_ok = "provision-relay: OK" in provision.stdout

        url = f"http://[{host}]:8443" if ":" in host else f"http://{host}:8443"
        return DeploymentResult(
            service="aleph",
            ok=provision_ok,
            id=item_hash or name,
            url=url if provision_ok else None,
            tx=None,
            details=details,
        )

    def verify(self, result: DeploymentResult) -> VerifyReport:
        return VerifyReport(
            ok=result.ok and bool(result.url),
            command="aleph instance create + ssh provision + local /health",
        )

    def rollback(self, result: DeploymentResult) -> None:
        # Hold-tier instances cost nothing while broken (tokens are held, not
        # spent); keep the VM for diagnosis instead of deleting evidence.
        return

    # -- helpers -------------------------------------------------------------

    def _find_instance(self, name: str) -> dict | None:
        for item in self.aleph.list_instances():
            metadata = item.get("metadata") or {}
            if name in (item.get("name"), metadata.get("name")):
                return item
        return None

    def _wait_for_instance(self, name: str, *, timeout_s: int = 600) -> dict:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            found = self._find_instance(name)
            if found is not None and self._instance_host(found):
                return found
            time.sleep(15)
        found = self._find_instance(name)
        if found is None:
            raise RuntimeError(f"aleph instance {name!r} not visible after create")
        return found

    @staticmethod
    def _instance_host(item: dict) -> str:
        allocation = item.get("allocation") or {}
        for key in ("ipv6", "ipv6_ip", "vm_ipv6", "ip"):
            value = allocation.get(key) or item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().split("/")[0]
        return ""
