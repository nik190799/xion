#!/usr/bin/env python3
"""Relay babysitter: health + escrow watchdog (stdlib only, CI-friendly).

Probes every endpoint in ledgers/RELAY_REGISTRY.json and every ACTIVE Akash
deployment's escrow runway via public REST. Exits 0 when all green, 1 when
anything needs operator attention, printing a plain-text report either way.

Born 2026-07-22 after three same-week silent failures: an Akash lease died of
escrow depletion mid-deploy, the live relay came within 30h of the same, and
an Aleph instance burned its full credit balance in ~2 days against a
misread pricing table. Lesson: liveness and runway must be watched from
OUTSIDE the operator laptop.
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request
from pathlib import Path

OWNER = "akash1sgt75mdxy7tuufam364n59089hre7gyew227ml"
# Public REST endpoints rotate/lapse; first responsive one wins.
AKASH_REST_CANDIDATES = [
    "https://rest.akashnet.net",
    "https://api.akashnet.net",
    "https://akash-api.polkachu.com",
    "https://rest-akash.ecostake.com",
    "https://akash-rest.publicnode.com",
]
# Observed CPU-relay burn 2026-07: ~95k uact/day single-service, ~250k/day hybrid.
UACT_PER_DAY_ESTIMATE = 250_000
MIN_RUNWAY_DAYS = 14

_INSECURE = ssl.create_default_context()
_INSECURE.check_hostname = False
_INSECURE.verify_mode = ssl.CERT_NONE


def _get(url: str, *, insecure: bool = False, timeout: int = 25) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "xion-babysitter/1"})
    ctx = _INSECURE if insecure else None
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.status, resp.read()


def check_registry_health(repo_root: Path) -> list[str]:
    problems: list[str] = []
    registry = json.loads((repo_root / "ledgers" / "RELAY_REGISTRY.json").read_text(encoding="utf-8"))
    for row in registry.get("relays", []):
        rid, endpoint = row.get("relay_id", "?"), str(row.get("endpoint", ""))
        if row.get("substrate") == "chutes":
            # Known-dead pending platform unblock (KW-RELAY-CHUTES-D3-001); skip noise.
            print(f"  [skip] {rid}: chutes leg platform-blocked, not probed")
            continue
        try:
            status, body = _get(endpoint.rstrip("/") + "/health", insecure=True)
            healthy = status == 200 and b'"relay_healthy":true' in body.replace(b" ", b"")
            print(f"  [{'ok' if healthy else 'BAD'}] {rid}: HTTP {status} {body[:80]!r}")
            if not healthy:
                problems.append(f"{rid}: /health HTTP {status} at {endpoint}")
        except Exception as exc:
            print(f"  [BAD] {rid}: {exc}")
            problems.append(f"{rid}: unreachable ({exc}) at {endpoint}")
    return problems


def check_akash_escrow() -> list[str]:
    problems: list[str] = []
    path = (
        "/akash/deployment/v1beta4/deployments/list"
        f"?filters.owner={OWNER}&filters.state=active&pagination.limit=50"
    )
    status, body = 0, b""
    for base in AKASH_REST_CANDIDATES:
        try:
            status, body = _get(base + path)
            if status == 200:
                print(f"  (rest endpoint: {base})")
                break
        except Exception:
            continue
    if status != 200:
        return ["akash REST unreachable on all candidate endpoints"]
    for item in json.loads(body).get("deployments", []):
        dseq = item.get("deployment", {}).get("id", {}).get("dseq", "?")
        funds = {f["denom"]: float(f["amount"]) for f in item.get("escrow_account", {}).get("state", {}).get("funds", [])}
        uact = funds.get("uact", 0.0)
        days = uact / UACT_PER_DAY_ESTIMATE
        print(f"  [{'ok' if days >= MIN_RUNWAY_DAYS else 'LOW'}] dseq {dseq}: {uact:,.0f} uact escrow (~{days:.0f} days)")
        if days < MIN_RUNWAY_DAYS:
            problems.append(
                f"dseq {dseq}: escrow ~{days:.0f} days left ({uact:,.0f} uact). "
                f"Top up: python -m xion_ops akash deposit {dseq} 10000000"
            )
    return problems


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    print("babysitter: relay health")
    problems = check_registry_health(repo_root)
    print("babysitter: akash escrow runway")
    try:
        problems += check_akash_escrow()
    except Exception as exc:
        problems.append(f"escrow check failed: {exc}")
    if problems:
        print("\nBABYSITTER ALERTS:")
        for p in problems:
            print(f"- {p}")
        return 1
    print("\nbabysitter: all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
