"""Verify bridge attestor scaffold."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="bridge-attest")
def bridge_attest() -> None:
    try:
        from orchestrator.bridge import BridgeAttestor, LightClientBridgeAttestor, MultisigBridgeAttestor

        attestor = MultisigBridgeAttestor()
        payload = {"kind": "attest", "event_weight": 1}
        attestation = attestor.attest(source_chain="ao", target_chain="base", event_id="evt-1", payload=payload)
        if not isinstance(attestor, BridgeAttestor):
            raise RuntimeError("multisig attestor does not satisfy BridgeAttestor Protocol")
        if not attestor.verify(attestation, payload=payload):
            raise RuntimeError("multisig attestation did not verify")
        if "multisig" not in attestation.signature:
            raise RuntimeError("attestation is not explicitly multisig-scoped")
        if "NOT_YET_SEALED" not in LightClientBridgeAttestor().not_yet_sealed_reason:
            raise RuntimeError("lightclient stub does not declare NOT_YET_SEALED")
    except Exception as exc:
        click.echo(f"bridge-attest: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("bridge-attest: OK (multisig bridge attestor + lightclient stub)")
    sys.exit(OK)


__all__ = ["bridge_attest"]
