"""PAYMENT_LEDGER — append-only, hash-chained JSONL (Phase 5g-iii).

Schema canonicalized in ``docs/schemas/ledger-payment.yaml`` (status:
canonical as of Phase 5g-iii). Row field semantics in
``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface (Phase 5g-iii)"
and ``docs/29-BILLING-X402.md`` § "PAYMENT_LEDGER schema".

Design posture. This module is the near-mirror of
``orchestrator/safety/ledger.py``. The canonicalization rule, file-lock
pattern, hash-chain semantics, ``ChainBroken`` error, and the
read/write/verify triple are byte-exact clones so a Phase-6 unified
treasury verifier can walk both ledgers with one library.

Differences from SAFETY_LEDGER:

  - One row per turn (settled or refunded); SAFETY writes one row per
    Arbiter call (two per turn). The join is on ``correlation_id``.
  - The row carries three money fields (committed / settled / refund)
    plus an ``outcome`` enum and a nullable ``refusal_stage``. These
    mirror the RESEARCH_SPEND_LEDGER sketch in
    ``docs/27-RESEARCH-SPEND.md`` so Phase 6 treasury audit code is
    one library, not two.
  - The writer refuses to emit the ``B3`` posture (Phase 6+ only) or
    the ``refunded_partial`` / ``stranded`` outcomes (Phase 7+ only)
    — an attempt is treated as a doctrine-violating bug and raises.

Stdlib-only by deliberate posture (Invariant 14 one level up). Hashing
is SHA-256 at ``SCHEMA_VERSION=1``; a migration to a non-SHA-256 family
bumps ``SCHEMA_VERSION`` and rotates the canonicalization rule inside
the same module.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1
"""Current PAYMENT_LEDGER schema version. Matches
``docs/schemas/ledger-payment.yaml``.

History:
  1  Phase 5g-iii (2026-04-21) — first landing.
"""

ZERO_HASH = "0" * 64
"""prev_hash sentinel for seq=0 of a fresh ledger. Byte-identical to
SAFETY_LEDGER's ZERO_HASH so a unified treasury verifier can share
the constant."""

_KNOWN_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})

# Enum vocabularies. These are the WRITER-side set at 5g-iii + 5g-ii;
# the ledger schema file reserves additional values (B3,
# refunded_partial, stranded, billing_rejected) for forward-
# compatibility — a 5g-iii writer that emits them is a bug. Phase
# 5g-ii Commit 3 adds ``cancelled`` to _WRITER_OUTCOMES for the
# client-disconnect path on the streaming Chat Surface.

_WRITER_POSTURES: frozenset[str] = frozenset({"B1", "B2", "disabled"})
_READER_POSTURES: frozenset[str] = frozenset({"B1", "B2", "B3", "disabled"})

_WRITER_OUTCOMES: frozenset[str] = frozenset({"settled", "refunded", "cancelled"})
_READER_OUTCOMES: frozenset[str] = frozenset(
    {"settled", "refunded", "cancelled", "refunded_partial", "stranded"}
)

_WRITER_REFUSAL_STAGES: frozenset[str] = frozenset({
    "ingress",
    "egress",
    "empty_candidate",
    "no_floor",
    "provider_error",
    "provider_timeout",
})
_READER_REFUSAL_STAGES: frozenset[str] = frozenset(
    _WRITER_REFUSAL_STAGES | {"billing_rejected"}
)

_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "seq",
    "prev_hash",
    "this_hash",
    "timestamp_utc_ns",
    "correlation_id",
    "posture",
    "outcome",
    "refusal_stage",
    "committed_XION",
    "settled_XION",
    "refund_XION",
    "posted_price_XION",
    "provider_id",
    "model_id",
    "authorization_reference",
    "source_sha256",
)

_FILE_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _REGISTRY_LOCK:
        lock = _FILE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _FILE_LOCKS[key] = lock
        return lock


def _canonical_bytes_excluding_this_hash(row: dict[str, Any]) -> bytes:
    """Byte-exact mirror of ``orchestrator.safety.ledger``'s rule."""
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------- READING


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Yield every row in file order. Does not verify the chain."""
    if not path.is_file():
        return
    with path.open("rb") as fh:
        for raw_line in fh:
            line = raw_line.rstrip(b"\n").rstrip(b"\r")
            if not line:
                continue
            yield json.loads(line.decode("utf-8"))


def _read_tail(path: Path) -> tuple[int, str]:
    last_seq = -1
    last_this_hash = ZERO_HASH
    for row in iter_rows(path):
        last_seq = int(row["seq"])
        last_this_hash = str(row["this_hash"])
    return last_seq + 1, last_this_hash


def chain_tip(path: Path) -> tuple[int, str]:
    count = 0
    tip = ZERO_HASH
    for row in iter_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


# --------------------------------------------------------------- WRITING


PostureLit = Literal["B1", "B2", "disabled"]
OutcomeLit = Literal["settled", "refunded", "cancelled"]
RefusalStageLit = Literal[
    "ingress",
    "egress",
    "empty_candidate",
    "no_floor",
    "provider_error",
    "provider_timeout",
]


def build_payment_row(
    *,
    correlation_id: str,
    timestamp_utc_ns: int,
    posture: PostureLit,
    outcome: OutcomeLit,
    refusal_stage: RefusalStageLit | None,
    committed_XION: int,
    settled_XION: int,
    refund_XION: int,
    posted_price_XION: int,
    provider_id: str | None,
    model_id: str | None,
    authorization_reference: str,
    source_sha256: str,
    seq: int,
    prev_hash: str,
    stream_id: str | None = None,
    user_proof_commit: str | None = None,
    user_proof_algorithm: str | None = None,
) -> dict[str, Any]:
    """Assemble a PAYMENT_LEDGER row and compute its ``this_hash``.

    Enforces the structural invariants pinned in
    ``docs/schemas/ledger-payment.yaml`` § ``structural_invariants``:

      - ``committed_XION == settled_XION + refund_XION``
      - ``outcome=settled  → refund_XION == 0   and refusal_stage IS NULL``
      - ``outcome=refunded → settled_XION == 0  and refund_XION == committed_XION``
      - ``posture=disabled → committed_XION == settled_XION == refund_XION == 0``
      - reserved enum values (``B3``, ``refunded_partial``, ``stranded``) are NEVER emitted

    Raises ``ValueError`` on any invariant violation. Callers catch +
    log + return 503 — a writer that tries to emit a malformed row is
    a bug, not a user-visible state; failing loudly surfaces it.
    """
    if posture not in _WRITER_POSTURES:
        raise ValueError(
            f"5g-iii writer refuses posture={posture!r}; "
            f"allowed: {sorted(_WRITER_POSTURES)}"
        )
    if outcome not in _WRITER_OUTCOMES:
        raise ValueError(
            f"5g-iii writer refuses outcome={outcome!r}; "
            f"allowed: {sorted(_WRITER_OUTCOMES)}"
        )
    if refusal_stage is not None and refusal_stage not in _WRITER_REFUSAL_STAGES:
        raise ValueError(
            f"5g-iii writer refuses refusal_stage={refusal_stage!r}; "
            f"allowed: {sorted(_WRITER_REFUSAL_STAGES)}"
        )

    if committed_XION < 0 or settled_XION < 0 or refund_XION < 0:
        raise ValueError("money fields must be non-negative")
    if committed_XION != settled_XION + refund_XION:
        raise ValueError(
            "committed_XION must equal settled_XION + refund_XION "
            f"(got {committed_XION} vs {settled_XION}+{refund_XION})"
        )

    if outcome == "settled":
        if refund_XION != 0:
            raise ValueError("outcome=settled requires refund_XION=0")
        if refusal_stage is not None:
            raise ValueError("outcome=settled requires refusal_stage=None")
        if settled_XION != committed_XION:
            raise ValueError(
                "outcome=settled requires settled_XION == committed_XION"
            )
    elif outcome == "cancelled":
        # Phase 5g-ii Commit 3: client-disconnect cancellation. Money
        # shape mirrors refunded (no value delivered, full refund), but
        # refusal_stage MUST be None because a cancel is an operational
        # outcome, not a Covenant refusal — the Arbiter never ran on
        # the candidate (the candidate may not even exist). Callers
        # that write a cancelled row MUST NOT pair it with a SAFETY
        # egress refuse row; xion-verify chat-streaming-fidelity
        # (Phase 5g-ii Commit 5) enforces the no-paired-egress shape.
        if settled_XION != 0:
            raise ValueError("outcome=cancelled requires settled_XION=0")
        if refund_XION != committed_XION:
            raise ValueError(
                "outcome=cancelled requires refund_XION == committed_XION"
            )
        if refusal_stage is not None:
            raise ValueError(
                "outcome=cancelled requires refusal_stage=None (cancel "
                "is operational, not a Covenant refusal)"
            )
    else:  # refunded
        if settled_XION != 0:
            raise ValueError("outcome=refunded requires settled_XION=0")
        if refusal_stage is None:
            raise ValueError("outcome=refunded requires refusal_stage!=None")
        if refund_XION != committed_XION:
            raise ValueError(
                "outcome=refunded (5g-iii full-refund) requires "
                "refund_XION == committed_XION"
            )

    if posture == "disabled":
        if committed_XION != 0 or settled_XION != 0 or refund_XION != 0:
            raise ValueError(
                "posture=disabled requires committed/settled/refund all 0"
            )
        if authorization_reference != "":
            raise ValueError(
                "posture=disabled requires authorization_reference=''"
            )

    if posted_price_XION < 0:
        raise ValueError("posted_price_XION must be non-negative")
    if len(source_sha256) != 64:
        raise ValueError("source_sha256 must be 64 hex chars")
    if seq < 0:
        raise ValueError("seq must be non-negative")

    # Phase 5g-ii Commit 5: ``stream_id`` is an OPTIONAL additive
    # field. A PAYMENT row that originated from the streaming Chat
    # Surface (``POST /chat/stream``) carries a lowercase hex
    # identifier (32 chars, 128 bits of entropy); a row from the
    # non-streaming ``POST /chat`` handler omits the field entirely.
    # Schema is additive: the canonicalization rule (json.dumps
    # sort_keys) hashes absent keys as absent, so existing
    # pre-commit-5 rows on disk stay byte-exact.
    if stream_id is not None:
        if not isinstance(stream_id, str):
            raise ValueError("stream_id must be a string when present")
        if len(stream_id) != 32:
            raise ValueError(
                f"stream_id must be exactly 32 hex chars (got {len(stream_id)})"
            )
        if not all(c in "0123456789abcdef" for c in stream_id):
            raise ValueError(
                "stream_id must be lowercase hex (0-9a-f)"
            )
        if outcome == "cancelled" and stream_id is None:
            # Defensive: cancellation without a stream_id is structurally
            # impossible (cancel only fires on streams) but re-asserted
            # here so a future refactor cannot silently drop the field.
            raise ValueError(
                "outcome=cancelled requires stream_id (streams only)"
            )

    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": prev_hash,
        "timestamp_utc_ns": timestamp_utc_ns,
        "correlation_id": correlation_id,
        "posture": posture,
        "outcome": outcome,
        "refusal_stage": refusal_stage,
        "committed_XION": committed_XION,
        "settled_XION": settled_XION,
        "refund_XION": refund_XION,
        "posted_price_XION": posted_price_XION,
        "provider_id": provider_id,
        "model_id": model_id,
        "authorization_reference": authorization_reference,
        "source_sha256": source_sha256,
    }
    if stream_id is not None:
        row["stream_id"] = stream_id
    if user_proof_commit is not None:
        row["user_proof_commit"] = user_proof_commit
        row["user_proof_algorithm"] = user_proof_algorithm
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    return row


def append_payment_row(
    path: Path,
    *,
    correlation_id: str,
    timestamp_utc_ns: int,
    posture: PostureLit,
    outcome: OutcomeLit,
    refusal_stage: RefusalStageLit | None,
    committed_XION: int,
    settled_XION: int,
    refund_XION: int,
    posted_price_XION: int,
    provider_id: str | None,
    model_id: str | None,
    authorization_reference: str,
    source_sha256: str,
    stream_id: str | None = None,
    user_proof_commit: str | None = None,
    user_proof_algorithm: str | None = None,
) -> dict[str, Any]:
    """Append a new row to the ledger. Returns the written row.

    Thread-safe within a process (per-path lock). Not multiprocess-safe.
    Mirrors ``orchestrator.safety.ledger.append`` byte-for-byte so a
    Phase-6 unified treasury verifier can walk both files with one
    canonicalization library.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        next_seq, prev_hash = _read_tail(path)
        row = build_payment_row(
            correlation_id=correlation_id,
            timestamp_utc_ns=timestamp_utc_ns,
            posture=posture,
            outcome=outcome,
            refusal_stage=refusal_stage,
            committed_XION=committed_XION,
            settled_XION=settled_XION,
            refund_XION=refund_XION,
            posted_price_XION=posted_price_XION,
            provider_id=provider_id,
            model_id=model_id,
            authorization_reference=authorization_reference,
            source_sha256=source_sha256,
            seq=next_seq,
            prev_hash=prev_hash,
            stream_id=stream_id,
            user_proof_commit=user_proof_commit,
            user_proof_algorithm=user_proof_algorithm,
        )
        line = json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
        return row


# --------------------------------------------------------------- VERIFY


class ChainBroken(Exception):
    """Raised by ``verify_chain`` when the ledger fails a structural
    check. The message names the offending ``seq`` and the specific
    property that failed. Callers: catch and print; do not unwind
    silently.
    """


def verify_chain(path: Path) -> tuple[int, str]:
    """Walk the ledger and verify, for every row:

      (a) well-formed JSON with every required field,
      (b) schema_version is a version this verifier knows,
      (c) seq contiguous starting at 0,
      (d) this_hash matches recomputed canonical-bytes hash,
      (e) prev_hash matches the prior row's this_hash,
      (f) structural invariants (money arithmetic, posture-outcome
          consistency, forbidden-enum-values) hold per row.

    Cross-ledger join with SAFETY_LEDGER on ``correlation_id`` is
    performed by ``xion-verify refusal-is-free`` (commit 4 of 5g-iii),
    not here. This function is per-ledger chain integrity only.

    Returns (row_count, tip_hash). Raises ChainBroken on any failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None

    for row in iter_rows(path):
        seq = row.get("seq", "?")

        for f in _REQUIRED_FIELDS:
            if f not in row:
                raise ChainBroken(f"seq={seq}: missing required field {f!r}")

        try:
            sv = int(row["schema_version"])
        except (TypeError, ValueError):
            raise ChainBroken(
                f"seq={seq}: schema_version must be an int, got "
                f"{row['schema_version']!r}"
            ) from None
        if sv not in _KNOWN_SCHEMA_VERSIONS:
            raise ChainBroken(
                f"seq={seq}: schema_version={sv} not supported by verifier "
                f"(knows {sorted(_KNOWN_SCHEMA_VERSIONS)})"
            )

        if int(row["seq"]) != expected_seq:
            raise ChainBroken(
                f"seq non-contiguous: expected {expected_seq}, got {row['seq']}"
            )
        if str(row["prev_hash"]) != expected_prev:
            raise ChainBroken(
                f"seq={seq}: prev_hash={row['prev_hash']} != expected {expected_prev}"
            )
        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(
                f"seq={seq}: this_hash recomputation mismatch "
                f"(stored={row['this_hash']} recomputed={recomputed})"
            )

        posture = row["posture"]
        outcome = row["outcome"]
        if posture not in _READER_POSTURES:
            raise ChainBroken(
                f"seq={seq}: invalid posture {posture!r}"
            )
        if outcome not in _READER_OUTCOMES:
            raise ChainBroken(
                f"seq={seq}: invalid outcome {outcome!r}"
            )
        rs = row["refusal_stage"]
        if rs is not None and rs not in _READER_REFUSAL_STAGES:
            raise ChainBroken(
                f"seq={seq}: invalid refusal_stage {rs!r}"
            )

        cXION = row["committed_XION"]
        sXION = row["settled_XION"]
        rXION = row["refund_XION"]
        for f in ("committed_XION", "settled_XION", "refund_XION", "posted_price_XION"):
            v = row[f]
            if not isinstance(v, int) or v < 0:
                raise ChainBroken(f"seq={seq}: {f} must be a non-negative int")

        if cXION != sXION + rXION:
            raise ChainBroken(
                f"seq={seq}: committed_XION ({cXION}) != "
                f"settled_XION + refund_XION ({sXION}+{rXION})"
            )

        if outcome == "settled":
            if rXION != 0 or rs is not None:
                raise ChainBroken(
                    f"seq={seq}: outcome=settled requires refund_XION=0 "
                    f"and refusal_stage=null"
                )
            if sXION != cXION:
                raise ChainBroken(
                    f"seq={seq}: outcome=settled requires "
                    f"settled_XION == committed_XION"
                )
        elif outcome == "cancelled":
            # Phase 5g-ii Commit 3: cancelled rows have the refunded
            # money shape (no value delivered, full refund) but
            # refusal_stage is NULL (cancel is operational, not a
            # Covenant refusal). Mirrors the writer's branch.
            if sXION != 0:
                raise ChainBroken(
                    f"seq={seq}: outcome=cancelled requires settled_XION=0"
                )
            if rXION != cXION:
                raise ChainBroken(
                    f"seq={seq}: outcome=cancelled requires "
                    f"refund_XION == committed_XION"
                )
            if rs is not None:
                raise ChainBroken(
                    f"seq={seq}: outcome=cancelled requires refusal_stage=null"
                )
        elif outcome == "refunded":
            if sXION != 0 or rs is None:
                raise ChainBroken(
                    f"seq={seq}: outcome=refunded requires settled_XION=0 "
                    f"and refusal_stage not null"
                )
            if rXION != cXION:
                raise ChainBroken(
                    f"seq={seq}: outcome=refunded (5g-iii) requires "
                    f"refund_XION == committed_XION"
                )
        # refunded_partial / stranded are reader-allowed values
        # (forward-compatibility) but NOT 5g-ii / 5g-iii writer-
        # emittable. xion-verify refusal-is-free flags them as
        # unexpected at 5g-iii phase; this chain-integrity verifier
        # does not.

        if posture == "disabled":
            if cXION != 0 or sXION != 0 or rXION != 0:
                raise ChainBroken(
                    f"seq={seq}: posture=disabled requires "
                    f"committed/settled/refund all 0"
                )
            if row["authorization_reference"] != "":
                raise ChainBroken(
                    f"seq={seq}: posture=disabled requires "
                    f"authorization_reference=''"
                )

        # Phase 5g-ii Commit 5: optional ``stream_id`` field. If
        # present, it MUST be a lowercase 32-hex string. Cancel rows
        # MUST carry it (cancellation is stream-only). Non-stream rows
        # MUST omit it; a legacy row on disk without the field is
        # tolerated.
        stream_id_val = row.get("stream_id")
        if stream_id_val is not None:
            if not isinstance(stream_id_val, str):
                raise ChainBroken(
                    f"seq={seq}: stream_id must be a string when present"
                )
            if len(stream_id_val) != 32 or not all(
                c in "0123456789abcdef" for c in stream_id_val
            ):
                raise ChainBroken(
                    f"seq={seq}: stream_id must be 32 lowercase hex chars"
                )
        elif outcome == "cancelled":
            raise ChainBroken(
                f"seq={seq}: outcome=cancelled requires stream_id "
                f"(cancellation is stream-only)"
            )

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "append_payment_row",
    "build_payment_row",
    "chain_tip",
    "iter_rows",
    "verify_chain",
]
