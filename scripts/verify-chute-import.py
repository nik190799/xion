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

    expected_paths = {"/health", "/xpricing", "/self"}
    missing_paths = expected_paths - set(public_paths)
    if missing_paths:
        print("FAIL missing public cord paths:", sorted(missing_paths), file=sys.stderr)
        return 1
    if xion_relay_chute.IMAGE_TAG != "pre-genesis-d3-7":
        print(
            "FAIL image_tag pinned to pre-genesis-d3-7, got:",
            xion_relay_chute.IMAGE_TAG,
            file=sys.stderr,
        )
        return 1

    sample = xion_relay_chute._smoke_envelope("/health")
    expected_keys = {"status", "service", "image_tag", "endpoint", "timestamp", "note"}
    missing = expected_keys - set(sample)
    if missing:
        print("FAIL missing envelope keys:", missing, file=sys.stderr)
        return 1
    if sample["status"] != "ok":
        print("FAIL envelope status not 'ok':", sample, file=sys.stderr)
        return 1
    if sample["endpoint"] != "/health":
        print("FAIL envelope endpoint not '/health':", sample, file=sys.stderr)
        return 1
    print("envelope_ok:", sample)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
