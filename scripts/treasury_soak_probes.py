#!/usr/bin/env python3
"""Cast-call probes for MasterTreasury (Base Sepolia rehearsal or Base mainnet).

RPC URL follows ``genesis/TREASURY_VAULTS.json`` ``status``: ``mainnet`` uses
``BASE_MAINNET_RPC`` / ``XION_BASE_MAINNET_RPC`` (default ``https://mainnet.base.org``);
otherwise Sepolia env vars (default ``https://sepolia.base.org``).

Uses Foundry **`cast`** when on ``PATH``. Otherwise performs the same three
view calls via JSON-RPC ``eth_call`` (stdlib only), so Windows operators get
real RPC verification without installing ``cast`` on the host PATH.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Keccak selectors for MasterTreasury view methods (``cast sig '<name>'``).
_SEL_GOVERNANCE = "0x5aa6e675"
_SEL_AO_CORE = "0xe580aee7"
_SEL_CHAIN_COUNT = "0xcb4af76b"


def _load_dotenv(root: Path) -> None:
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = val.strip().strip("'\"")


def _eth_call(rpc: str, to: str, data: str, *, timeout: int = 60) -> str:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": to, "data": data}, "latest"],
            "id": 1,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        rpc,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "xion-os/treasury_soak_probes"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"eth_call HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"eth_call network error: {exc}") from exc
    if "error" in body:
        raise RuntimeError(f"eth_call JSON-RPC error: {body['error']}")
    result = body.get("result")
    if not isinstance(result, str) or not result.startswith("0x"):
        raise RuntimeError(f"eth_call unexpected result: {body!r}")
    return result


def _decode_address(ret: str) -> str:
    h = ret.removeprefix("0x")
    if len(h) < 40:
        raise ValueError(f"address return too short: {ret!r}")
    return "0x" + h[-40:]


def _decode_uint(ret: str) -> int:
    return int(ret, 16)


def _run_via_cast(cast: str, master: str, rpc: str) -> None:
    def _cast(args: list[str]) -> None:
        subprocess.run([cast, *args], check=True, timeout=120)

    _cast(["call", master, "governance()(address)", "--rpc-url", rpc])
    _cast(["call", master, "aoCoreAuthority()(address)", "--rpc-url", rpc])
    _cast(["call", master, "registeredChainCount()(uint256)", "--rpc-url", rpc])


def _run_via_rpc(master: str, rpc: str) -> None:
    gov = _decode_address(_eth_call(rpc, master, _SEL_GOVERNANCE))
    ao = _decode_address(_eth_call(rpc, master, _SEL_AO_CORE))
    n = _decode_uint(_eth_call(rpc, master, _SEL_CHAIN_COUNT))
    print(f"[treasury_soak_probes] governance={gov}")
    print(f"[treasury_soak_probes] aoCoreAuthority={ao}")
    print(f"[treasury_soak_probes] registeredChainCount={n}")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    _load_dotenv(root)
    manifest_path = root / "genesis" / "TREASURY_VAULTS.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status", "testnet")
    if status == "mainnet":
        rpc = (
            os.environ.get("BASE_MAINNET_RPC")
            or os.environ.get("XION_BASE_MAINNET_RPC")
            or "https://mainnet.base.org"
        )
    else:
        rpc = (
            os.environ.get("BASE_SEPOLIA_RPC")
            or os.environ.get("XION_BASE_SEPOLIA_RPC")
            or "https://sepolia.base.org"
        )
    master = manifest["master_treasury"]
    print(f"[treasury_soak_probes] rpc={rpc}")
    print(f"[treasury_soak_probes] master_treasury={master}")

    cast = shutil.which("cast")
    if cast:
        print("[treasury_soak_probes] using cast")
        _run_via_cast(cast, master, rpc)
    else:
        print("[treasury_soak_probes] cast not on PATH; using eth_call JSON-RPC")
        _run_via_rpc(master, rpc)
    print("[treasury_soak_probes] OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"[treasury_soak_probes] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except (RuntimeError, ValueError, OSError, urllib.error.URLError) as exc:
        print(f"[treasury_soak_probes] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
