"""Aleph Cloud (aleph.im) service wrapper.

Drives the ``aleph`` Python CLI (aleph-client) installed inside WSL, mirroring
the WSL-bridge pattern used by :mod:`xion_ops.services.akash`. Instances on
Aleph are full QEMU VMs: deployment is ``instance create`` + SSH provisioning,
not an SDL manifest.

Payment: tier hold (default) or PAYG. The account key lives at
``~/.aleph-im/private-keys/xion-aleph.key`` inside WSL; funding the account is
an operator action and is never performed here.
"""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

from xion_ops.commands import CommandResult, run_command
from xion_ops.exceptions import OpsError

_WSL_PATH_PREFIX = 'export PATH="$HOME/.local/bin:$PATH"; '


class AlephCloudService:
    name = "aleph"

    def __init__(self, *, repo_root: Path | str = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.ssh_key_path = os.environ.get("XION_ALEPH_SSH_KEY", "$HOME/.ssh/xion-aleph")

    # -- low-level -----------------------------------------------------------

    def _wsl(self, command: str, *, timeout: int = 300) -> CommandResult:
        return run_command(
            ["wsl", "bash", "-lc", _WSL_PATH_PREFIX + command],
            cwd=self.repo_root,
            timeout=timeout,
        )

    def cli_available(self) -> bool:
        try:
            self._wsl("aleph --version >/dev/null 2>&1 || aleph --help >/dev/null 2>&1", timeout=60)
            return True
        except Exception:
            return False

    def account_address(self) -> str:
        result = self._wsl("aleph account show 2>/dev/null | grep -oE '0x[a-fA-F0-9]{40}' | head -1", timeout=60)
        address = result.stdout.strip()
        if not address.startswith("0x"):
            raise OpsError("aleph account not configured in WSL; run `aleph account create`")
        return address

    # -- instance lifecycle --------------------------------------------------

    def list_instances(self) -> list[dict[str, Any]]:
        # `aleph instance list` exits 1 when the account has zero instances;
        # fold that into an empty result instead of raising.
        result = self._wsl("out=$(aleph instance list --json 2>&1); rc=$?; printf '%s' \"$out\"; "
                           "case \"$out\" in *'No instance found'*) exit 0;; esac; exit $rc", timeout=180)
        raw = result.stdout.strip()
        if "No instance found" in raw:
            return []
        if not raw:
            return []
        start = raw.find("[")
        if start < 0:
            return []
        try:
            payload = json.loads(raw[start:])
        except json.JSONDecodeError as exc:
            raise OpsError(f"aleph instance list returned unparseable JSON: {raw[:200]}") from exc
        return payload if isinstance(payload, list) else []

    def top_crn_url(self, *, min_score: float = 0.97) -> str:
        """Pick the highest-scored CRN; override with XION_ALEPH_CRN_URL."""

        return self.top_crn(min_score=min_score)[0]

    def top_crn(self, *, min_score: float = 0.97) -> tuple[str, str]:
        """Return (url, hash) of the best CRN; override with XION_ALEPH_CRN_URL/_HASH."""

        override = os.environ.get("XION_ALEPH_CRN_URL")
        if override:
            return override, os.environ.get("XION_ALEPH_CRN_HASH", "")
        result = self._wsl("aleph node compute --json 2>/dev/null", timeout=180)
        raw = result.stdout
        payload = json.loads(raw[raw.find("[") if raw.find("[") >= 0 else raw.find("{"):])
        nodes = payload.get("nodes") if isinstance(payload, dict) else payload
        candidates = [
            n for n in (nodes or [])
            if isinstance(n, dict) and (n.get("score") or 0) >= min_score and n.get("address")
        ]
        if not candidates:
            raise OpsError(f"no CRN with score >= {min_score} found")
        candidates.sort(key=lambda n: -(n.get("score") or 0))
        best = candidates[0]
        return str(best["address"]).rstrip("/"), str(best.get("hash") or "")

    def create_instance(
        self,
        name: str,
        *,
        compute_units: int = 2,
        payment_type: str | None = None,
        payment_chain: str | None = None,
        rootfs: str | None = "ubuntu24",
        crn_url: str | None = None,
    ) -> CommandResult:
        # Aleph retired hold-tier for instances (error 202 / "credits only",
        # verified 2026-07-18); credits are the working payment mode.
        payment = payment_type or os.environ.get("XION_ALEPH_PAYMENT_TYPE", "credit")
        chain = payment_chain or os.environ.get("XION_ALEPH_PAYMENT_CHAIN", "BASE")
        parts = [
            "aleph instance create",
            f"--name {shlex.quote(name)}",
            f"--compute-units {int(compute_units)}",
            f"--payment-type {shlex.quote(payment)}",
            f"--payment-chain {shlex.quote(chain)}",
            f"--ssh-pubkey-file {self.ssh_key_path}.pub",
            "--skip-volume",
            "--crn-auto-tac",
        ]
        if rootfs:
            parts.append(f"--rootfs {shlex.quote(rootfs)}")
        parts.append(f"--rootfs-size {int(os.environ.get('XION_ALEPH_ROOTFS_MIB', '40960'))}")
        if crn_url:
            parts.append(f"--crn-url {shlex.quote(crn_url)}")
        else:
            url, crn_hash = self.top_crn()
            parts.append(f"--crn-url {shlex.quote(url)}")
            if crn_hash:
                parts.append(f"--crn-hash {shlex.quote(crn_hash)}")
        return self._wsl(" ".join(parts), timeout=600)

    def delete_instance(self, item_hash: str) -> CommandResult:
        return self._wsl(f"aleph instance delete {shlex.quote(item_hash)}", timeout=300)

    def instance_logs(self, item_hash: str) -> str:
        try:
            return self._wsl(f"aleph instance logs {shlex.quote(item_hash)} 2>&1 | tail -50", timeout=120).stdout
        except Exception as exc:  # logs are best-effort evidence
            return f"<logs unavailable: {exc}>"

    # -- provisioning --------------------------------------------------------

    def ssh_provision(self, host: str, script_repo_path: str, *, user: str = "root", timeout: int = 900) -> CommandResult:
        """Push a provisioning script to the VM over SSH and execute it."""

        wsl_repo = "/mnt/" + str(self.repo_root).replace("\\", "/").replace(":", "", 1).lower()[0] + str(
            self.repo_root
        ).replace("\\", "/")[2:]
        script = f"{wsl_repo}/{script_repo_path}"
        ssh_opts = (
            f"-i {self.ssh_key_path} -o StrictHostKeyChecking=accept-new "
            "-o ConnectTimeout=20 -o BatchMode=yes"
        )
        target = f"{user}@{host}" if ":" not in host else f"{user}@{host}"
        command = f"ssh {ssh_opts} {shlex.quote(target)} 'bash -s' < {shlex.quote(script)}"
        return self._wsl(command, timeout=timeout)
