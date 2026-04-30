"""Verify bridge attestor scaffold."""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(name="bridge-attest")
@click.option("--backend", type=click.Choice(["all", "multisig", "lightclient"]), default="all", show_default=True)
def bridge_attest(backend: str) -> None:
    try:
        from orchestrator.bridge import (
            BridgeAttestor,
            LightClientBridgeAttestor,
            MultisigBridgeAttestor,
            canonical_payload_hash,
        )

        if backend in {"all", "multisig"}:
            attestor = MultisigBridgeAttestor()
            payload = {"kind": "attest", "event_weight": 1}
            attestation = attestor.attest(source_chain="ao", target_chain="base", event_id="evt-1", payload=payload)
            if not isinstance(attestor, BridgeAttestor):
                raise RuntimeError("multisig attestor does not satisfy BridgeAttestor Protocol")
            if not attestor.verify(attestation, payload=payload):
                raise RuntimeError("multisig attestation did not verify")
            if "multisig" not in attestation.signature:
                raise RuntimeError("attestation is not explicitly multisig-scoped")
        if backend in {"all", "lightclient"}:
            lightclient = LightClientBridgeAttestor()
            payload = {
                "kind": "treasury-spend",
                "amount": 1,
                "ao_checkpoint": {
                    "process_id": "ao-core-localnet",
                    "height": 1,
                    "prev_state_root": "0" * 64,
                    "state_root": "1" * 64,
                    "event_id": "evt-1",
                    "payload_hash": "placeholder",
                },
            }
            body_hash = canonical_payload_hash(
                {key: value for key, value in payload.items() if key not in {"ao_checkpoint", "payload_hash"}}
            )
            payload["ao_checkpoint"]["payload_hash"] = body_hash
            attestation = lightclient.attest(source_chain="ao", target_chain="base", event_id="evt-1", payload=payload)
            if not isinstance(lightclient, BridgeAttestor):
                raise RuntimeError("lightclient attestor does not satisfy BridgeAttestor Protocol")
            if not lightclient.verify(attestation, payload=payload):
                raise RuntimeError("lightclient attestation did not verify")
            if "ao-checkpoint" not in attestation.signature:
                raise RuntimeError("lightclient attestation is not AO-checkpoint scoped")
    except Exception as exc:
        click.echo(f"bridge-attest: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo(f"bridge-attest: OK ({backend} bridge attestor verified)")
    sys.exit(OK)


__all__ = ["bridge_attest"]
