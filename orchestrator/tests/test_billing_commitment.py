"""Unit tests for the Phase 5g-iii commitment parser and verifiers.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)" → "Billing postures (B1 / B2 / B3)".

These tests exercise ``orchestrator.billing.commitment`` directly;
they do not spin up FastAPI. The integration tests in
``test_chat_billing.py`` drive the full /chat path.
"""

from __future__ import annotations

import hashlib
import hmac

from orchestrator.billing.commitment import (
    Commitment,
    CommitmentRejectReason,
    _b1_payload_bytes,
    parse_commitment_header,
    verify_b1_attestation,
    verify_b2_x402_shape,
)

# ---------------------------------------------------------- parser: common


def test_parser_rejects_none_as_missing() -> None:
    assert parse_commitment_header(None) == CommitmentRejectReason.MISSING


def test_parser_rejects_empty_as_missing() -> None:
    assert parse_commitment_header("") == CommitmentRejectReason.MISSING
    assert parse_commitment_header("   ") == CommitmentRejectReason.MISSING


def test_parser_rejects_non_ascii() -> None:
    result = parse_commitment_header("operator-attest:v1:\u00ff\u00ff")
    assert result == CommitmentRejectReason.MALFORMED


def test_parser_rejects_excessively_long_header() -> None:
    header = "operator-attest:v1:" + ("a" * 2000)
    assert parse_commitment_header(header) == CommitmentRejectReason.MALFORMED


def test_parser_rejects_unknown_posture() -> None:
    assert (
        parse_commitment_header("unknown-scheme:v1:abc")
        == CommitmentRejectReason.POSTURE_NOT_ACCEPTED
    )


# --------------------------------------------------------------- parser: B1


def _build_b1_header(
    *,
    secret: bytes,
    price: int,
    body_sha256: str,
    ts: int,
) -> str:
    payload = _b1_payload_bytes(price, body_sha256, ts)
    payload_hash = hashlib.sha256(payload).hexdigest()
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return f"operator-attest:v1:{sig}:{payload_hash}:{price}:{body_sha256}:{ts}"


def test_parser_accepts_valid_b1_header() -> None:
    secret = b"x" * 32
    body_sha = "a" * 64
    header = _build_b1_header(secret=secret, price=1000, body_sha256=body_sha, ts=42)
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)
    assert parsed.posture == "B1"
    assert parsed.posted_price_micro_XION_claim == 1000
    assert parsed.body_sha256_claim == body_sha
    assert parsed.timestamp_utc_ns_claim == 42
    assert len(parsed.authorization_reference) == 64


def test_parser_rejects_b1_with_wrong_payload_hash() -> None:
    """Self-consistency check: a client that says hash=X but payload
    bytes hash to Y is malformed, even before signature verification."""
    secret = b"x" * 32
    body_sha = "a" * 64
    payload = _b1_payload_bytes(1000, body_sha, 42)
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    wrong_hash = "b" * 64
    header = f"operator-attest:v1:{sig}:{wrong_hash}:1000:{body_sha}:42"
    assert parse_commitment_header(header) == CommitmentRejectReason.MALFORMED


def test_parser_rejects_b1_wrong_field_count() -> None:
    header = "operator-attest:v1:" + ":".join(["a" * 64] * 3)  # only 5 parts
    assert parse_commitment_header(header) == CommitmentRejectReason.MALFORMED


def test_parser_rejects_b1_non_hex_signature() -> None:
    body_sha = "a" * 64
    payload_hash = "b" * 64
    header = f"operator-attest:v1:notahex:{payload_hash}:1000:{body_sha}:42"
    assert parse_commitment_header(header) == CommitmentRejectReason.MALFORMED


def test_parser_rejects_b1_negative_price() -> None:
    body_sha = "a" * 64
    sig = "c" * 64
    payload_hash = "b" * 64
    header = f"operator-attest:v1:{sig}:{payload_hash}:-1:{body_sha}:42"
    assert parse_commitment_header(header) == CommitmentRejectReason.MALFORMED


# --------------------------------------------------------------- parser: B2


def test_parser_accepts_b2_with_short_sig() -> None:
    sig = "a" * 64
    commitment_hash = "b" * 64
    parsed = parse_commitment_header(f"x402:v1:{sig}:{commitment_hash}")
    assert isinstance(parsed, Commitment)
    assert parsed.posture == "B2"
    assert parsed.authorization_reference == commitment_hash


def test_parser_accepts_b2_with_long_sig() -> None:
    """130-hex-char EIP-712-style signature."""
    sig = "c" * 130
    commitment_hash = "d" * 64
    parsed = parse_commitment_header(f"x402:v1:{sig}:{commitment_hash}")
    assert isinstance(parsed, Commitment)
    assert parsed.posture == "B2"


def test_parser_rejects_b2_wrong_sig_length() -> None:
    sig = "c" * 100
    commitment_hash = "d" * 64
    assert (
        parse_commitment_header(f"x402:v1:{sig}:{commitment_hash}")
        == CommitmentRejectReason.MALFORMED
    )


def test_parser_rejects_b2_wrong_commitment_hash() -> None:
    sig = "c" * 64
    bad_hash = "d" * 63
    assert (
        parse_commitment_header(f"x402:v1:{sig}:{bad_hash}")
        == CommitmentRejectReason.MALFORMED
    )


# ------------------------------------------------------- verifier: B1 HMAC


def test_b1_verifier_accepts_valid_attestation() -> None:
    secret = b"\x01" * 32
    body_sha = "a" * 64
    ts = 1_700_000_000_000_000_000
    header = _build_b1_header(secret=secret, price=1000, body_sha256=body_sha, ts=ts)
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)

    err = verify_b1_attestation(
        parsed,
        secret=secret,
        raw_header=header,
        expected_price_micro_XION=1000,
        actual_body_sha256=body_sha,
        now_utc_ns=ts + 1_000_000,  # 1ms later
    )
    assert err is None


def test_b1_verifier_rejects_signature_under_wrong_secret() -> None:
    signing_secret = b"\x01" * 32
    body_sha = "a" * 64
    ts = 1_700_000_000_000_000_000
    header = _build_b1_header(
        secret=signing_secret, price=1000, body_sha256=body_sha, ts=ts
    )
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)

    wrong_secret = b"\x02" * 32
    err = verify_b1_attestation(
        parsed,
        secret=wrong_secret,
        raw_header=header,
        expected_price_micro_XION=1000,
        actual_body_sha256=body_sha,
        now_utc_ns=ts,
    )
    assert err == CommitmentRejectReason.SIGNATURE_INVALID


def test_b1_verifier_rejects_price_mismatch() -> None:
    """Operator signs for 500; posted governance price is 1000. Reject."""
    secret = b"\x01" * 32
    body_sha = "a" * 64
    ts = 1_700_000_000_000_000_000
    header = _build_b1_header(
        secret=secret, price=500, body_sha256=body_sha, ts=ts
    )
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)

    err = verify_b1_attestation(
        parsed,
        secret=secret,
        raw_header=header,
        expected_price_micro_XION=1000,
        actual_body_sha256=body_sha,
        now_utc_ns=ts,
    )
    assert err == CommitmentRejectReason.SIGNATURE_INVALID


def test_b1_verifier_rejects_body_mismatch() -> None:
    """Signed body sha does not match the actual incoming body."""
    secret = b"\x01" * 32
    signed_body = "a" * 64
    actual_body = "b" * 64
    ts = 1_700_000_000_000_000_000
    header = _build_b1_header(
        secret=secret, price=1000, body_sha256=signed_body, ts=ts
    )
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)

    err = verify_b1_attestation(
        parsed,
        secret=secret,
        raw_header=header,
        expected_price_micro_XION=1000,
        actual_body_sha256=actual_body,
        now_utc_ns=ts,
    )
    assert err == CommitmentRejectReason.SIGNATURE_INVALID


def test_b1_verifier_rejects_expired_timestamp() -> None:
    secret = b"\x01" * 32
    body_sha = "a" * 64
    ts = 1_700_000_000_000_000_000
    header = _build_b1_header(
        secret=secret, price=1000, body_sha256=body_sha, ts=ts
    )
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)

    # 10 minutes after the signed timestamp (default window: 5 minutes).
    err = verify_b1_attestation(
        parsed,
        secret=secret,
        raw_header=header,
        expected_price_micro_XION=1000,
        actual_body_sha256=body_sha,
        now_utc_ns=ts + 600_000_000_000,
    )
    assert err == CommitmentRejectReason.TIMESTAMP_EXPIRED


def test_b1_verifier_refuses_non_b1_posture() -> None:
    """Calling the B1 verifier on a B2 commitment is a caller bug; it
    must fail-closed rather than pass."""
    sig = "c" * 64
    commitment_hash = "d" * 64
    parsed = parse_commitment_header(f"x402:v1:{sig}:{commitment_hash}")
    assert isinstance(parsed, Commitment)
    err = verify_b1_attestation(
        parsed,
        secret=b"\x01" * 32,
        raw_header="",
        expected_price_micro_XION=0,
        actual_body_sha256="",
        now_utc_ns=0,
    )
    assert err == CommitmentRejectReason.POSTURE_NOT_ACCEPTED


# -------------------------------------------------------- verifier: B2 shape


def test_b2_verifier_passes_shape_valid_commitment() -> None:
    sig = "c" * 64
    commitment_hash = "d" * 64
    parsed = parse_commitment_header(f"x402:v1:{sig}:{commitment_hash}")
    assert isinstance(parsed, Commitment)
    assert verify_b2_x402_shape(parsed) is None


def test_b2_verifier_refuses_non_b2_posture() -> None:
    secret = b"\x01" * 32
    body_sha = "a" * 64
    header = _build_b1_header(
        secret=secret, price=1000, body_sha256=body_sha, ts=42
    )
    parsed = parse_commitment_header(header)
    assert isinstance(parsed, Commitment)
    assert (
        verify_b2_x402_shape(parsed)
        == CommitmentRejectReason.POSTURE_NOT_ACCEPTED
    )
