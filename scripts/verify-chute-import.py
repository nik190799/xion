"""Smoke-import the repo-root Chutes module before pushing.

This catches import-time errors (typos, missing deps, bad cord declarations)
before we burn a Chutes build slot.
"""

from __future__ import annotations

import sys

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
    if xion_relay_chute.IMAGE_TAG != "pre-genesis-d3-8":
        print(
            "FAIL image_tag pinned to pre-genesis-d3-8, got:",
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
    print("live_surface_ok:", xion_relay_chute.SERVICE_NAME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
