#!/usr/bin/env python3
"""POST /chat smoke test (plan: live Xion replies — model path without x402).

Default mode runs one hermetic pytest that proves ``POST /chat`` returns 200
with a stub generative provider (billing off; matches operator D2 rehearsal).

**Local relay with billing on (Chutes parity):** start ``python -m orchestrator.api``
with production env, satisfy ``XION-Commitment`` per ``docs/29-BILLING-X402.md``,
then:

  python scripts/chat_smoke_local.py --http --url https://your-relay.chutes.ai

``--http`` targets a base where FastAPI exposes ``POST /chat`` (loopback, Akash
forwarded URL, etc.). The public **Chutes** hostname only wires ``/health``,
``/quote``, and ``/self`` cords — a bare ``POST /chat`` there returns platform
404; use ``python -m xion_ops chutes verify-cords`` for that substrate.

For Akash CPU-only relays, ``POST /chat`` may return **503**
``open_weights_floor_unsatisfied``; that still proves TLS + routing + billing
gates. Use ``--accept-floor-503`` or env ``XION_CHAT_SMOKE_ACCEPT_FLOOR=1`` to
exit 0 when that envelope is returned.

For Akash nip.io TLS, use ``--insecure`` (same posture as ``curl -k`` in
``docs/runbooks/AKASH_RELAY_DEPLOY.md``).

``--http`` fails fast on 402 (missing x402), 404 cord, or connection errors.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


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


def _chutes_headers() -> dict[str, str]:
    token = (os.environ.get("CHUTES_API_KEY") or os.environ.get("XION_CHUTES_API_KEY") or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _run_pytest() -> int:
    import pytest

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    return pytest.main(
        [
            "-q",
            "--tb=short",
            "orchestrator/tests/test_chat_api.py::test_post_chat_happy_path_returns_moderated_text",
        ]
    )


def _run_http(base: str, *, verify_tls: bool, accept_floor: bool) -> int:
    try:
        import httpx
    except ImportError:
        print("chat_smoke_local: install httpx for --http mode", file=sys.stderr)
        return 2

    base = base.rstrip("/")
    headers = _chutes_headers()
    try:
        with httpx.Client(timeout=120.0, headers=headers, verify=verify_tls) as client:
            hr = client.get(f"{base}/health")
            if hr.status_code != 200:
                print(f"chat_smoke_local: GET /health -> {hr.status_code}", file=sys.stderr)
                return 1
            pr = client.post(
                f"{base}/chat",
                json={"message": "Say one short friendly greeting."},
            )
    except httpx.RequestError as exc:
        print(f"chat_smoke_local: request failed: {exc}", file=sys.stderr)
        return 1

    if pr.status_code == 402:
        print(
            "chat_smoke_local: got 402 payment_required — provide XION-Commitment per "
            "docs/29-BILLING-X402.md or run without --http (pytest stub mode).",
            file=sys.stderr,
        )
        return 1
    if pr.status_code == 503:
        body = pr.text or ""
        if "open_weights_floor_unsatisfied" in body or "open_weights_floor" in body:
            if accept_floor:
                print(
                    "chat_smoke_local: relay reachable; open-weights floor unsatisfied "
                    "(honest CPU-only / D3 rehearsal posture; see KW-FLOOR-DEPLOY-001)."
                )
                return 0
    if pr.status_code != 200:
        print(f"chat_smoke_local: POST /chat -> {pr.status_code} {pr.text[:500]}", file=sys.stderr)
        return 1
    print("chat_smoke_local: POST /chat OK", pr.json().get("message", pr.text)[:200])
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="POST /chat smoke (pytest or HTTP).")
    p.add_argument(
        "--http",
        action="store_true",
        help="POST to relay URL instead of pytest (default URL below).",
    )
    p.add_argument(
        "--url",
        default=None,
        help="Relay base URL for --http (default: XION_CHAT_SMOKE_URL or http://127.0.0.1:8010).",
    )
    p.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS verification (Akash nip.io / dev forwards per runbooks).",
    )
    p.add_argument(
        "--accept-floor-503",
        action="store_true",
        help="Treat 503 open_weights_floor_unsatisfied as success (Akash CPU-only rehearsal).",
    )
    args = p.parse_args()
    if args.http:
        _load_dotenv(Path(__file__).resolve().parent.parent)
        url = (args.url or os.environ.get("XION_CHAT_SMOKE_URL") or "http://127.0.0.1:8010").strip()
        accept = args.accept_floor_503 or os.environ.get("XION_CHAT_SMOKE_ACCEPT_FLOOR") == "1"
        return _run_http(url, verify_tls=not args.insecure, accept_floor=accept)
    return _run_pytest()


if __name__ == "__main__":
    raise SystemExit(main())
