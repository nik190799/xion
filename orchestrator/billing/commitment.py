"""``X-Payment-Commitment`` header parser + posture verifiers.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)" → "Billing postures (B1 / B2 / B3)" and
``docs/29-BILLING-X402.md`` → "Posture".

Three postures live in the vocabulary; two are live writers at 5g-iii.
Posture is selected per-request by the header prefix; the operator does
not toggle it globally, since a single Relay legitimately serves both
localhost operator turns (B1) and external integrators (B2).

B1 — operator-attestation (D1 default)
    Header:    ``operator-attest:v1:<hex_signature>:<hex_payload_hash>``
    Signature: HMAC-SHA256 over the raw payload bytes, keyed by the
               operator's shared secret. 64 hex chars (256 bits).
    Payload:   implementation-defined binding of
               ``{posted_price_micro_XION, request_body_sha256,
                  timestamp_utc_ns}``; the client-side format is the
               UTF-8 string
               ``"{posted_price_micro_XION}:{body_sha256}:{timestamp_utc_ns}"``.
               Only the payload HASH appears in the header; the payload
               itself is presented in follow-up fields on the header
               (semicolon-separated inline vs out-of-band envelope).

    For 5g-iii the B1 client puts the payload fields directly in the
    header after the signature+hash, so the receiver can independently
    re-hash the payload and compare:

        operator-attest:v1:<hmac_hex>:<payload_hash_hex>:<posted_price_micro_XION>:<body_sha256_hex>:<timestamp_utc_ns>

    The receiver:
      1. Splits on ':'.
      2. Recomputes the payload hash from the three trailing fields.
      3. Verifies the payload hash matches the 3rd field (prevents a
         mismatch between signed payload and declared payload).
      4. Verifies HMAC-SHA256 of the payload bytes under the shared
         secret matches the 2nd field.
      5. Verifies timestamp is within the freshness window.
      6. Verifies body_sha256 matches the incoming request body.
      7. Verifies posted_price_micro_XION matches the
         ``pricing_config.per_message_price_micro_XION`` at commitment
         time (operator attesting to a price lower than posted is
         invalid).

B2 — x402-commitment (D2, opt-in)
    Header:    ``x402:v1:<eip712_sig_hex>:<commitment_hash_hex>``
    5g-iii validates the header SHAPE only (hex, length, non-empty)
    and records ``commitment_hash_hex`` in ``authorization_reference``.
    ``KW-BILLING-001`` tracks the deferred cryptographic signature
    verification; it closes in Phase 6 when AO Core chain-verification
    becomes available.

B3 — x402-settled (Phase 6+; not emittable at 5g-iii)
    The writer NEVER emits B3 rows. The PAYMENT_LEDGER schema reserves
    the enum value for forward-compatibility under Invariant 14.

Stdlib-only by deliberate posture — core orchestrator deps remain 0.
HMAC-SHA256 is ``hmac.compare_digest`` (constant-time) over
``hmac.new(key, payload, sha256).hexdigest()``. Ed25519 is a Phase-6+
migration under the Crypto-Agility Mandate; the parser / verifier
module rotates wholesale in that phase with no change to
``PAYMENT_LEDGER`` row shape.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class CommitmentRejectReason(str, Enum):
    """Structured reasons a commitment header is rejected.

    These values feed directly into ``PaymentChallenge.reason_code``.
    Wrapped in an enum so the reject call site cannot typo one.
    """

    MISSING = "missing_commitment"
    MALFORMED = "malformed_commitment"
    POSTURE_NOT_ACCEPTED = "posture_not_accepted"
    SIGNATURE_INVALID = "attestation_signature_invalid"
    TIMESTAMP_EXPIRED = "attestation_timestamp_expired"
    NONCE_REPLAYED = "attestation_nonce_replayed"


_PostureLit = Literal["B1", "B2"]
"""5g-iii-emittable postures. B3 is reserved for Phase 6+ and is NEVER
produced by this module. Future-phase additions widen this literal
under a schema_version bump on PAYMENT_LEDGER."""


@dataclass(frozen=True)
class Commitment:
    """The successfully-parsed, structurally-validated commitment.

    Successful parse + verification of this object gates the start of a
    billable turn. The ``authorization_reference`` field is what lands
    in the PAYMENT_LEDGER row; its semantic depends on posture:

      - B1: sha256 hex of the operator-attestation payload
      - B2: the client-supplied commitment hash (x402's 32-byte digest
            of the EIP-712 message, hex-encoded)

    Fields:
      posture: Which posture was declared. The Relay serves both.
      authorization_reference: Row-field value (64-hex-char string).
      posted_price_micro_XION_claim: Price the client claims in the
          attestation. For B1 only; the verifier checks this against
          ``pricing_config.per_message_price_micro_XION`` before the
          commitment is accepted. For B2, 0 (the price is implicit in
          the on-chain commitment; 5g-iii does not cross-check).
      body_sha256_claim: Request-body hash the client claims (B1 only;
          empty string for B2). The verifier checks against the actual
          incoming body hash.
      timestamp_utc_ns_claim: The signed timestamp (B1 only; 0 for
          B2). The verifier checks freshness.
    """

    posture: _PostureLit
    authorization_reference: str
    posted_price_micro_XION_claim: int = 0
    body_sha256_claim: str = ""
    timestamp_utc_ns_claim: int = 0


def parse_commitment_header(
    raw: str | None,
) -> Commitment | CommitmentRejectReason:
    """Split and shape-validate a raw ``X-Payment-Commitment`` header.

    Returns the parsed ``Commitment`` on success; a
    ``CommitmentRejectReason`` on failure. Does NOT verify signatures
    here — verification is a separate step so the parser can be reused
    in contexts where signature verification is not appropriate (e.g.,
    a debug operator inspecting a commitment without the secret).

    The parser is deliberately strict: missing / empty / non-ASCII /
    over-long headers are rejected without special handling. A future
    posture that needs a different separator must rotate under a
    new ``:vN`` suffix; this parser's ``v1`` is pinned.
    """
    if raw is None:
        return CommitmentRejectReason.MISSING
    s = raw.strip()
    if not s:
        return CommitmentRejectReason.MISSING
    if len(s) > 1024:
        return CommitmentRejectReason.MALFORMED
    try:
        s.encode("ascii")
    except UnicodeEncodeError:
        return CommitmentRejectReason.MALFORMED

    if s.startswith("operator-attest:v1:"):
        return _parse_b1(s)
    if s.startswith("x402:v1:"):
        return _parse_b2(s)
    return CommitmentRejectReason.POSTURE_NOT_ACCEPTED


def _parse_b1(s: str) -> Commitment | CommitmentRejectReason:
    """B1 header shape:

        operator-attest:v1:<hmac_hex>:<payload_hash_hex>:<price>:<body_sha>:<ts_ns>

    Seven colon-separated fields (the first two are the prefix + v1
    marker; the remaining five are the payload).
    """
    parts = s.split(":")
    if len(parts) != 7:
        return CommitmentRejectReason.MALFORMED
    _prefix, _version, sig_hex, payload_hash_hex, price_s, body_sha, ts_s = parts

    if not _HEX64_RE.match(sig_hex):
        return CommitmentRejectReason.MALFORMED
    if not _HEX64_RE.match(payload_hash_hex):
        return CommitmentRejectReason.MALFORMED
    if not _HEX64_RE.match(body_sha):
        return CommitmentRejectReason.MALFORMED
    try:
        price = int(price_s)
        ts = int(ts_s)
    except ValueError:
        return CommitmentRejectReason.MALFORMED
    if price < 0 or ts < 0:
        return CommitmentRejectReason.MALFORMED

    # Parser validates the self-consistency of the payload hash: if the
    # client's declared payload-hash does not match the payload bytes
    # as re-canonicalized by the receiver, the commitment is malformed
    # before any signature work runs. This catches a class of client
    # bugs cheaply; it does not replace the signature check below.
    payload = _b1_payload_bytes(price, body_sha, ts)
    recomputed = hashlib.sha256(payload).hexdigest()
    if not hmac.compare_digest(recomputed, payload_hash_hex):
        return CommitmentRejectReason.MALFORMED

    return Commitment(
        posture="B1",
        authorization_reference=payload_hash_hex,
        posted_price_micro_XION_claim=price,
        body_sha256_claim=body_sha,
        timestamp_utc_ns_claim=ts,
    )


def _parse_b2(s: str) -> Commitment | CommitmentRejectReason:
    """B2 header shape:

        x402:v1:<eip712_sig_hex>:<commitment_hash_hex>

    At 5g-iii the signature is NOT verified (KW-BILLING-001); the
    parser only enforces shape. Both hex fields must be 64 chars (the
    EIP-712 signature is typically 65 bytes / 130 hex; for 5g-iii we
    allow the hex length to be 64 or 130 so a future phase can tighten
    or a client can hash-truncate). At this phase the only use of the
    signature field is shape-check; the commitment hash is what lands
    in the ledger row.
    """
    parts = s.split(":")
    if len(parts) != 4:
        return CommitmentRejectReason.MALFORMED
    _prefix, _version, sig_hex, commitment_hash_hex = parts

    # Permissive signature-length check: 64 or 130 hex chars. Tighten
    # at Phase 6 when chain verification lands.
    if len(sig_hex) not in (64, 130):
        return CommitmentRejectReason.MALFORMED
    try:
        bytes.fromhex(sig_hex)
    except ValueError:
        return CommitmentRejectReason.MALFORMED
    if not _HEX64_RE.match(commitment_hash_hex):
        return CommitmentRejectReason.MALFORMED

    return Commitment(
        posture="B2",
        authorization_reference=commitment_hash_hex,
    )


def _b1_payload_bytes(
    price: int,
    body_sha256_hex: str,
    timestamp_utc_ns: int,
) -> bytes:
    """Canonical payload the operator signs.

    Format is pinned as a stable UTF-8 string so a client in any
    language can reproduce it byte-for-byte. Any change to this
    serialization is a v2 bump (``operator-attest:v2:...``); a v1
    parser must not accept a v2 payload.
    """
    return f"{price}:{body_sha256_hex}:{timestamp_utc_ns}".encode()


def verify_b1_attestation(
    commitment: Commitment,
    *,
    secret: bytes,
    raw_header: str,
    expected_price_micro_XION: int,
    actual_body_sha256: str,
    now_utc_ns: int,
    freshness_window_ns: int = 300_000_000_000,
) -> CommitmentRejectReason | None:
    """Cryptographically verify a parsed B1 commitment.

    Returns ``None`` on success; a ``CommitmentRejectReason`` on
    failure. Called AFTER ``parse_commitment_header`` has shape-
    validated the header.

    Constitutional property checked here:
      - The operator's HMAC-SHA256 over the payload matches the
        signature the client declared.
      - The price the client claims matches the posted price (the
        operator cannot under-pay themselves by signing a lower price
        than governance has posted).
      - The body hash the client signed matches the actual request
        body (the signature is bound to this specific message).
      - The timestamp is within ``freshness_window_ns`` of now
        (Genesis Default: 5 minutes). A signed commitment more than
        5 minutes old is treated as replayed / stale.

    A future nonce-registry (Phase 6+) closes the last replay window:
    a commitment whose timestamp is fresh but whose payload-hash has
    already been used is rejected as replayed. 5g-iii does not ship
    the registry; the 5-minute freshness window is the partial defense.
    """
    if commitment.posture != "B1":
        return CommitmentRejectReason.POSTURE_NOT_ACCEPTED

    # Extract the signature field from the raw header (authoritative
    # vs reconstructing from the parsed commitment — the parser drops
    # it from the dataclass intentionally so a caller cannot forget to
    # cross-check).
    parts = raw_header.strip().split(":")
    if len(parts) != 7:
        return CommitmentRejectReason.MALFORMED
    sig_hex = parts[2]

    payload = _b1_payload_bytes(
        commitment.posted_price_micro_XION_claim,
        commitment.body_sha256_claim,
        commitment.timestamp_utc_ns_claim,
    )
    expected_sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, sig_hex):
        return CommitmentRejectReason.SIGNATURE_INVALID

    if commitment.posted_price_micro_XION_claim != expected_price_micro_XION:
        return CommitmentRejectReason.SIGNATURE_INVALID

    if not hmac.compare_digest(
        commitment.body_sha256_claim, actual_body_sha256
    ):
        return CommitmentRejectReason.SIGNATURE_INVALID

    delta = abs(now_utc_ns - commitment.timestamp_utc_ns_claim)
    if delta > freshness_window_ns:
        return CommitmentRejectReason.TIMESTAMP_EXPIRED

    return None


def verify_b2_x402_shape(
    commitment: Commitment,
) -> CommitmentRejectReason | None:
    """Verify a parsed B2 commitment's shape.

    At 5g-iii this is a no-op beyond what the parser already did
    (hex-shape check on commitment hash). The function exists as a
    seam so Phase 6 can replace the body with chain-side EIP-712
    signature verification + nonce-registry lookup under unchanged
    call sites. ``KW-BILLING-001`` tracks that migration.
    """
    if commitment.posture != "B2":
        return CommitmentRejectReason.POSTURE_NOT_ACCEPTED
    if not _HEX64_RE.match(commitment.authorization_reference):
        return CommitmentRejectReason.MALFORMED
    return None


__all__ = [
    "Commitment",
    "CommitmentRejectReason",
    "parse_commitment_header",
    "verify_b1_attestation",
    "verify_b2_x402_shape",
]
