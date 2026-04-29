"""Smoke-import the repo-root Chutes module before pushing.

This catches import-time errors (typos, missing deps, bad cord declarations)
and the Relay subprocess env contract before we burn a Chutes build slot.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import xion_relay_chute


def main() -> int:
    chute = xion_relay_chute.chute
    print("chute_name :", chute.name)
    print("image_tag  :", xion_relay_chute.IMAGE_TAG)
    print("service    :", xion_relay_chute.SERVICE_NAME)

    public_paths: list[str] = []
    print("cords      :")
    for cord in chute.cords:
        method = getattr(cord, "_public_api_method", getattr(cord, "public_api_method", "?"))
        path = getattr(cord, "_public_api_path", getattr(cord, "public_api_path", "?"))
        print("  -", method, path)
        public_paths.append(path)

    expected_paths = {"/health", "/quote", "/self"}
    missing_paths = expected_paths - set(public_paths)
    if missing_paths:
        print("FAIL missing public cord paths:", sorted(missing_paths), file=sys.stderr)
        return 1
    if xion_relay_chute.IMAGE_TAG != "pre-genesis-d3-10":
        print(
            "FAIL image_tag pinned to pre-genesis-d3-10, got:",
            xion_relay_chute.IMAGE_TAG,
            file=sys.stderr,
        )
        return 1

    if xion_relay_chute.SERVICE_NAME != "xion-relay-chutes":
        print(
            "FAIL service name should advertise the live Relay surface, got:",
            xion_relay_chute.SERVICE_NAME,
            file=sys.stderr,
        )
        return 1

    app_root = xion_relay_chute.APP_ROOT
    if not (app_root / "orchestrator").is_dir():
        print("FAIL APP_ROOT does not contain orchestrator/:", app_root, file=sys.stderr)
        return 1

    relay_env = xion_relay_chute._relay_env()
    expected_env = {
        "XION_API_HOST": "127.0.0.1",
        "XION_API_PORT": str(xion_relay_chute.RELAY_PORT),
        "XION_API_WORKERS": "1",
        "XION_REPO_ROOT": str(app_root),
        "XION_CAST_POOL_ON_BOOT": "false",
    }
    for key, expected in expected_env.items():
        actual = relay_env.get(key)
        if actual != expected:
            print(f"FAIL relay env {key}={actual!r}, expected {expected!r}", file=sys.stderr)
            return 1

    pythonpath = relay_env.get("PYTHONPATH", "").split(os.pathsep)
    if str(app_root) not in pythonpath:
        print("FAIL relay env PYTHONPATH does not include APP_ROOT:", app_root, file=sys.stderr)
        return 1

    print("live_surface_ok:", xion_relay_chute.SERVICE_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
