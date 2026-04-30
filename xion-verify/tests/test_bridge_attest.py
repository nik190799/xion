from __future__ import annotations

from click.testing import CliRunner
from orchestrator.bridge import (
    LightClientBridgeAttestor,
    attest_treasury_spend,
    build_treasury_spend_payload,
    canonical_payload_hash,
    verify_treasury_spend,
)

from xion_verify.cli import root
from xion_verify.exit_codes import OK


def _payload() -> dict[str, object]:
    body = {"kind": "treasury-spend", "amount": 7}
    return {
        **body,
        "ao_checkpoint": {
            "process_id": "ao-core-localnet",
            "height": 1,
            "prev_state_root": "0" * 64,
            "state_root": "1" * 64,
            "event_id": "evt-7",
            "payload_hash": canonical_payload_hash(body),
        },
    }


def test_bridge_attest_lightclient_cli() -> None:
    result = CliRunner().invoke(root, ["bridge-attest", "--backend=lightclient"])

    assert result.exit_code == OK, result.output
    assert "lightclient bridge attestor verified" in result.output


def test_lightclient_rejects_tampered_payload_body() -> None:
    attestor = LightClientBridgeAttestor()
    payload = _payload()
    attestation = attestor.attest(source_chain="ao", target_chain="base", event_id="evt-7", payload=payload)

    tampered = dict(payload)
    tampered["amount"] = 8

    assert not attestor.verify(attestation, payload=tampered)


def test_treasury_spend_payload_verifies_with_lightclient() -> None:
    attestor = LightClientBridgeAttestor()
    payload = build_treasury_spend_payload(
        process_id="ao-core-localnet",
        height=2,
        prev_state_root="0" * 64,
        state_root="a" * 64,
        spend_id="spend-1",
        amount=100,
        asset="USDC",
        recipient="0x000000000000000000000000000000000000b0b0",
        purpose_sha256="b" * 64,
        chain_id=8453,
    )
    attestation = attest_treasury_spend(attestor, payload=payload)

    assert verify_treasury_spend(attestor, attestation, payload=payload)
