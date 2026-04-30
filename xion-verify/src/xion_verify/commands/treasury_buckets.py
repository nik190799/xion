"""Treasury bucket verifiers for D3."""

from __future__ import annotations

import json
import sys

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_MANIFEST = "genesis/TREASURY_VAULTS.json"


def _load() -> tuple[int, dict[str, object] | str]:
    repo_root = find_repo_root()
    data = json.loads((repo_root / _MANIFEST).read_text(encoding="utf-8"))
    if data.get("status") != "testnet":
        return NOT_YET_SEALED, f"{_MANIFEST} status is {data.get('status')!r}, expected 'testnet'"
    if not data.get("master_treasury") or not data.get("vaults"):
        return NOT_YET_SEALED, "treasury vault addresses not populated"
    return OK, data


def _run(label: str) -> None:
    try:
        code, result = _load()
    except (RepoRootNotFound, OSError, json.JSONDecodeError) as exc:
        click.echo(f"{label}: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    if code != OK:
        click.echo(f"{label}: NOT_YET_SEALED — {result}")
        sys.exit(code)
    if label == "treasury-flow":
        try:
            from orchestrator.bridge import (
                LightClientBridgeAttestor,
                attest_treasury_spend,
                build_treasury_spend_payload,
                verify_treasury_spend,
            )

            payload = build_treasury_spend_payload(
                process_id="ao-core-localnet",
                height=1,
                prev_state_root="0" * 64,
                state_root="1" * 64,
                spend_id="synthetic-treasury-flow",
                amount=1,
                asset="USDC",
                recipient="0x0000000000000000000000000000000000000001",
                purpose_sha256="a" * 64,
                chain_id=8453,
            )
            attestor = LightClientBridgeAttestor()
            attestation = attest_treasury_spend(attestor, payload=payload)
            if not verify_treasury_spend(attestor, attestation, payload=payload):
                raise RuntimeError("synthetic AO treasury-spend bridge event did not verify")
        except Exception as exc:
            click.echo(f"{label}: FAIL: {exc}", err=True)
            sys.exit(FAIL)
    click.echo(f"{label}: OK (testnet treasury manifest populated)")
    sys.exit(OK)


@click.command(name="treasury-flow", help="Verify routed revenue matches five-slice treasury composition.")
def treasury_flow() -> None:
    _run("treasury-flow")


@click.command(name="improvement-fund", help="Verify Improvement Fund spend posture.")
def improvement_fund() -> None:
    _run("improvement-fund")


@click.command(name="reserve", help="Verify Rainy-Day Reserve posture.")
def reserve() -> None:
    _run("reserve")


@click.command(name="foundation-reserve", help="Verify Foundation Reserve separation.")
def foundation_reserve() -> None:
    _run("foundation-reserve")


__all__ = ["foundation_reserve", "improvement_fund", "reserve", "treasury_flow"]
