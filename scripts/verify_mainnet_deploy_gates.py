#!/usr/bin/env python3
"""Cross-platform deploy gate bundle (mirrors ``verify-mainnet-deploy-gates.sh``).

Use when WSL/bash ``python3`` lacks ``xion_verify`` but Windows ``python`` has it.

Loads repo-root ``.env`` when present (same as the shell script).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _bash_script_path(path: Path) -> str:
    """Path for Git Bash / MSYS when spawning ``bash`` from Windows Python."""
    resolved = path.resolve()
    if sys.platform == "win32":
        s = str(resolved)
        if len(s) > 2 and s[1] == ":":
            drive = s[0].lower()
            rest = s[2:].replace("\\", "/")
            return f"/{drive}{rest}"
    return str(resolved).replace("\\", "/")


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


def _run(args: list[str], root: Path) -> None:
    print(f"[verify_mainnet_deploy_gates] {' '.join(args)}")
    subprocess.run(
        [sys.executable, "-m", "xion_verify", *args],
        cwd=root,
        check=True,
    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    _load_dotenv(root)
    os.environ.setdefault("XION_API_REQUIRE_BEARER", "false")

    print(f"[verify_mainnet_deploy_gates] cwd={root}")
    try:
        _run(["--self-test"], root)
        _run(["treasury"], root)
        _run(["discovery", "--no-cloudflare"], root)
        _run(["substrate-portability"], root)
        try:
            _run(["akash-deploy-discipline"], root)
        except subprocess.CalledProcessError:
            print(
                "[verify_mainnet_deploy_gates] WARN: akash-deploy-discipline — "
                "see docs/STATE_OF_XION_TESTNET.md"
            )
        try:
            _run(["treasury-flow"], root)
        except subprocess.CalledProcessError as exc:
            print(
                f"[verify_mainnet_deploy_gates] WARN: treasury-flow exited {exc.returncode} "
                "(expected until Sepolia rehearsal + manifests match)"
            )
        if os.environ.get("TREASURY_SOAK_PROBES") == "1":
            soak_sh = root / "scripts" / "treasury-soak-probes.sh"
            soak_py = root / "scripts" / "treasury_soak_probes.py"
            if sys.platform == "win32":
                rc = subprocess.call([sys.executable, str(soak_py)], cwd=str(root))
            else:
                rc = subprocess.call(["bash", _bash_script_path(soak_sh)], cwd=str(root))
            if rc != 0:
                print(f"[verify_mainnet_deploy_gates] WARN: treasury soak probes exited {rc}")
        else:
            print(
                "[verify_mainnet_deploy_gates] hint: set TREASURY_SOAK_PROBES=1 to run treasury soak probes. "
                "Windows uses scripts/treasury_soak_probes.py (cast if on PATH, else JSON-RPC). "
                "Unix uses scripts/treasury-soak-probes.sh under bash."
            )
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    print("[verify_mainnet_deploy_gates] core bundle complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
