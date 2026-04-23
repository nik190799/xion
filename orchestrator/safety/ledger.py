"""SAFETY_LEDGER — append-only, hash-chained JSONL.

Schema canonicalized in `docs/schemas/ledger-safety.yaml` (status: canonical
as of Phase 4a). Row field semantics live in `docs/04-ARCHITECTURE.md`
§ "Safety Ledger row schema". This module is the single implementation
that writes and verifies the ledger. No other file in `orchestrator/safety/`
touches the file directly.

Properties guaranteed.

  - Append-only: `append(verdict)` opens the file in `"ab"` mode; there is
    no call path in this module that seeks or truncates.
  - Hash-chained: every row's `prev_hash` == previous row's `this_hash`.
    Any in-place edit, delete, or insertion breaks the chain.
  - Canonical bytes: `json.dumps(..., sort_keys=True,
    separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Byte-exact
    across platforms.
  - Candidate-content-free: the candidate text is NEVER written; only its
    sha256 (as `candidate_sha256`) is recorded. This makes the ledger
    publishable without leaking caller content.

Non-properties (honestly stated).

  - Tail truncation is not detected by the chain alone. Truncation defense
    acquires the chain head pinned to Arweave in Phase 4b. Until then,
    `chain_tip(path)` returns the current tip hash so operators can pin it
    out-of-band.
  - Concurrent writers are NOT supported. One `append()` at a time; a
    process-level `threading.Lock` is held around the read+write. Multi-
    process coordination is Phase 5's job (the Relay runs one Arbiter).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from orchestrator.safety.types import Decision, EscalationReason, LlmJudgement, Verdict

SCHEMA_VERSION = 2
"""Current ledger schema version. Matches `docs/schemas/ledger-safety.yaml`.

History.
  1  Phase 4a (2026-04-20) — Arbiter v1 rule engine; eight flat fields.
  2  Phase 4b (2026-04-21) — adds nested `llm_verdict` field for v2 LLM
                             second-pass; readers dispatch per-row.

Readers MUST accept any schema_version in `_KNOWN_SCHEMA_VERSIONS`. Writers
always write at `SCHEMA_VERSION` (the current version). A single ledger
file may therefore contain rows of multiple versions — pre-upgrade rows
stay at their original version forever; post-upgrade rows are written at
the then-current version. `prev_hash` linkage is enforced across version
boundaries; only the canonicalization differs, and it differs only in
which fields are present.
"""

_V1_SCHEMA_VERSION = 1
_V2_SCHEMA_VERSION = 2
_KNOWN_SCHEMA_VERSIONS: frozenset[int] = frozenset({_V1_SCHEMA_VERSION, _V2_SCHEMA_VERSION})

ZERO_HASH = "0" * 64
"""prev_hash sentinel for seq=0 of a fresh ledger."""

# Required fields shared by every schema_version.
_COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "seq", "prev_hash", "this_hash",
    "timestamp_utc_ns", "correlation_id", "candidate_sha256",
    "verdict", "summary",
)
# Fields v2 adds on top of the common set. Value may be null (v2 did not run)
# but the key MUST be present on v2 rows — absence is a schema violation.
_V2_REQUIRED_FIELDS: tuple[str, ...] = ("llm_verdict",)

# Required nested fields inside a non-null llm_verdict object.
_LLM_VERDICT_REQUIRED_FIELDS: tuple[str, ...] = (
    "provider_id", "model_id", "provider_version",
    "latency_ms", "decision", "summary", "raw_output_sha256",
)
_LLM_VERDICT_OPTIONAL_FIELDS: tuple[str, ...] = ("principle_id", "confidence")
_LLM_VERDICT_ALLOWED_FIELDS: frozenset[str] = frozenset(
    _LLM_VERDICT_REQUIRED_FIELDS + _LLM_VERDICT_OPTIONAL_FIELDS
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
    """Canonicalization rule. MUST match `docs/schemas/ledger-safety.yaml`
    `hash.canonicalization` exactly."""
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_hex(text.encode("utf-8"))


def _llm_verdict_to_row(judgement: LlmJudgement | None) -> dict[str, Any] | None:
    """Serialise a `LlmJudgement` into the nested object the ledger writes
    under the `llm_verdict` field. `None` -> `None` (v2 did not run)."""
    if judgement is None:
        return None
    obj: dict[str, Any] = {
        "provider_id": judgement.provider_id,
        "model_id": judgement.model_id,
        "provider_version": int(judgement.provider_version),
        "latency_ms": int(judgement.latency_ms),
        "decision": judgement.decision.value,
        "summary": judgement.summary,
        "raw_output_sha256": _sha256_hex(bytes(judgement.raw_output)),
        # principle_id is null iff decision is OK (enforced in LlmJudgement).
        "principle_id": judgement.principle_id,
    }
    if judgement.confidence is not None:
        obj["confidence"] = float(judgement.confidence)
    else:
        obj["confidence"] = None
    return obj


def _row_from_verdict(
    verdict: Verdict,
    *,
    seq: int,
    prev_hash: str,
) -> dict[str, Any]:
    """Build a new-row dict at `SCHEMA_VERSION`. Writers always produce the
    current version; readers dispatch per-row to handle older versions."""
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": prev_hash,
        "timestamp_utc_ns": verdict.timestamp_utc_ns,
        "correlation_id": verdict.correlation_id,
        "candidate_sha256": verdict.candidate_sha256,
        "verdict": verdict.decision.value,
        "summary": verdict.summary,
        "principle_id": verdict.principle_id,
        "rule_id": verdict.rule_id,
        "rule_version": verdict.rule_version,
        "escalation_reason": (
            verdict.escalation_reason.value
            if verdict.escalation_reason is not None
            else None
        ),
    }
    # v2 addition: nested llm_verdict. Always present on v2 rows; value is
    # None if v2 did not run (e.g., v1 was not OK), an object otherwise.
    if SCHEMA_VERSION >= _V2_SCHEMA_VERSION:
        row["llm_verdict"] = _llm_verdict_to_row(verdict.llm_verdict)

    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    return row


# -------------------------------------------------------------------- READING


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
    """Return (next_seq, prev_hash) to use for a fresh append.

    For an empty / missing file: (0, ZERO_HASH).
    For an existing file: (last_seq + 1, last_this_hash).
    """
    last_seq = -1
    last_this_hash = ZERO_HASH
    for row in iter_rows(path):
        last_seq = int(row["seq"])
        last_this_hash = str(row["this_hash"])
    return last_seq + 1, last_this_hash


def chain_tip(path: Path) -> tuple[int, str]:
    """Return (seq_count, tip_hash). `seq_count` == number of rows; `tip_hash`
    == last row's `this_hash`, or ZERO_HASH if the file is empty/missing.

    Operators can pin `tip_hash` out-of-band (e.g., a weekly Arweave post
    in Phase 4a) to gain tail-truncation defense manually, ahead of Phase 4b
    automating it.
    """
    count = 0
    tip = ZERO_HASH
    for row in iter_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


# -------------------------------------------------------------------- WRITING


def append(path: Path, verdict: Verdict) -> dict[str, Any]:
    """Append a verdict to the ledger. Returns the written row.

    Thread-safe within a process (per-path lock). Not multiprocess-safe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        next_seq, prev_hash = _read_tail(path)
        row = _row_from_verdict(verdict, seq=next_seq, prev_hash=prev_hash)
        line = json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        # Open with O_APPEND so even a racing writer from the same process
        # (that bypasses the lock) cannot overwrite an existing row. We
        # still hold the lock for atomicity across the read_tail+write pair.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
        return row


# -------------------------------------------------------------------- VERIFY


class ChainBroken(Exception):
    """Raised by `verify_chain` when the ledger fails a structural check.
    The message names the offending `seq` and the specific property that
    failed. Callers: catch and print; do not unwind silently."""


_V2_ERA_ESCALATION_REASONS: frozenset[str] = frozenset({
    # Phase 4b (LLM second-pass pipeline, originates inside the Arbiter).
    "llm_arbiter_escalated",
    "llm_arbiter_uncaught_exception",
    "llm_arbiter_provider_unavailable",
    # Phase 4c (Relay ↔ Arbiter integration contract, originates on the
    # caller of gate()). See docs/04-ARCHITECTURE.md § "Relay ↔ Arbiter
    # integration contract". llm_verdict MAY be null on these rows — v2
    # did not run because the integration itself was the thing that failed.
    "arbiter_timeout",
    "arbiter_unreachable",
})


def _verify_llm_verdict_nested(obj: Any, seq: int) -> None:
    """Structural check on a non-null `llm_verdict` nested object.
    Raises ChainBroken on any violation. See
    `docs/04-ARCHITECTURE.md` § "Nested `llm_verdict` object"."""
    if not isinstance(obj, dict):
        raise ChainBroken(f"seq={seq}: llm_verdict must be an object or null, got {type(obj).__name__}")
    missing = [f for f in _LLM_VERDICT_REQUIRED_FIELDS if f not in obj]
    if missing:
        raise ChainBroken(f"seq={seq}: llm_verdict missing required fields: {missing}")
    unknown = set(obj.keys()) - _LLM_VERDICT_ALLOWED_FIELDS
    if unknown:
        raise ChainBroken(f"seq={seq}: llm_verdict has unknown fields: {sorted(unknown)}")
    if obj["decision"] not in ("ok", "refuse", "escalate"):
        raise ChainBroken(f"seq={seq}: llm_verdict.decision invalid: {obj['decision']!r}")
    if obj["decision"] == "ok":
        if obj.get("principle_id") is not None:
            raise ChainBroken(f"seq={seq}: llm_verdict.decision=ok requires principle_id=null")
    else:
        if not obj.get("principle_id"):
            raise ChainBroken(f"seq={seq}: llm_verdict.decision={obj['decision']} requires non-empty principle_id")
    if not isinstance(obj["provider_version"], int) or obj["provider_version"] < 1:
        raise ChainBroken(f"seq={seq}: llm_verdict.provider_version must be a positive int")
    if not isinstance(obj["latency_ms"], int) or obj["latency_ms"] < 0:
        raise ChainBroken(f"seq={seq}: llm_verdict.latency_ms must be a non-negative int")
    if not isinstance(obj["raw_output_sha256"], str) or len(obj["raw_output_sha256"]) != 64:
        raise ChainBroken(f"seq={seq}: llm_verdict.raw_output_sha256 must be a 64-char hex string")
    conf = obj.get("confidence")
    if conf is not None and (not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0)):
        raise ChainBroken(f"seq={seq}: llm_verdict.confidence must be in [0.0, 1.0] or null")


def verify_chain(path: Path) -> tuple[int, str]:
    """Walk the ledger and verify, for every row:
      (a) well-formed JSON with every required field for its schema_version,
      (b) seq contiguous starting at 0,
      (c) this_hash matches recomputed canonical-bytes hash,
      (d) prev_hash matches the prior row's this_hash (across version
          boundaries too).

    Per-row schema_version dispatch rules (Phase 4b):
      - v1 rows MUST NOT contain the llm_verdict field.
      - v2 rows MUST contain the llm_verdict field (value may be null).
      - On refuse verdicts: v1 rows require rule_id + rule_version; v2
        rows satisfy this EITHER that way (v1-produced refusal) OR via
        a non-null llm_verdict whose decision is "refuse" (v2-produced).
      - On escalate with a v2-era escalation_reason: the row MUST be v2.
        llm_verdict MAY be null only for the crash/unavailable cases
        (llm_arbiter_uncaught_exception, llm_arbiter_provider_unavailable);
        llm_arbiter_escalated requires a non-null llm_verdict whose
        decision is "escalate".

    Returns (row_count, tip_hash). Raises ChainBroken on any failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None

    for row in iter_rows(path):
        seq = row.get("seq", "?")

        # required-field presence (common to every schema_version)
        for f in _COMMON_REQUIRED_FIELDS:
            if f not in row:
                raise ChainBroken(f"seq={seq}: missing required field {f!r}")

        # schema_version must be one we know how to verify
        try:
            sv = int(row["schema_version"])
        except (TypeError, ValueError):
            raise ChainBroken(f"seq={seq}: schema_version must be an int, got {row['schema_version']!r}") from None
        if sv not in _KNOWN_SCHEMA_VERSIONS:
            raise ChainBroken(
                f"seq={seq}: schema_version={sv} not supported by verifier "
                f"(knows {sorted(_KNOWN_SCHEMA_VERSIONS)})"
            )

        # Per-version required-field rules.
        if sv >= _V2_SCHEMA_VERSION:
            for f in _V2_REQUIRED_FIELDS:
                if f not in row:
                    raise ChainBroken(
                        f"seq={seq}: schema_version>={_V2_SCHEMA_VERSION} "
                        f"requires field {f!r} (may be null)"
                    )
        else:
            # v1 rows MUST NOT contain v2-only fields (else their this_hash
            # would have been computed including those fields, and a row
            # without the field could not match).
            for f in _V2_REQUIRED_FIELDS:
                if f in row:
                    raise ChainBroken(
                        f"seq={seq}: schema_version={sv} rows must not contain "
                        f"v2-only field {f!r}"
                    )

        # seq contiguity
        if int(row["seq"]) != expected_seq:
            raise ChainBroken(
                f"seq non-contiguous: expected {expected_seq}, got {row['seq']}"
            )

        # prev_hash linkage (across version boundaries: unaffected)
        if str(row["prev_hash"]) != expected_prev:
            raise ChainBroken(
                f"seq={seq}: prev_hash={row['prev_hash']} != expected {expected_prev}"
            )

        # this_hash recompute — canonicalization uses whatever fields are
        # present. v1 rows hash over v1 fields; v2 rows hash over v2 fields.
        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(
                f"seq={seq}: this_hash recomputation mismatch "
                f"(stored={row['this_hash']} recomputed={recomputed})"
            )

        # verdict enum
        if row["verdict"] not in ("ok", "refuse", "escalate"):
            raise ChainBroken(f"seq={seq}: invalid verdict {row['verdict']!r}")

        # principle_id rules (identical across versions)
        if row["verdict"] == "ok":
            if row.get("principle_id") is not None:
                raise ChainBroken(f"seq={seq}: verdict=ok but principle_id is not null")
        else:
            if row.get("principle_id") is None:
                raise ChainBroken(f"seq={seq}: verdict={row['verdict']} requires principle_id")

        # Nested llm_verdict structural check (v2 rows only; value may be null).
        llm_v: Any = None
        if sv >= _V2_SCHEMA_VERSION:
            llm_v = row.get("llm_verdict")
            if llm_v is not None:
                _verify_llm_verdict_nested(llm_v, seq)

        # refuse rules — version-aware:
        #   v1: requires rule_id + rule_version (v1 rule fired).
        #   v2: either the v1-rule-fired path, OR a v2-produced refusal
        #       (rule_id null and llm_verdict.decision == "refuse").
        if row["verdict"] == "refuse":
            has_v1_rule = row.get("rule_id") is not None and row.get("rule_version") is not None
            v2_produced = (
                sv >= _V2_SCHEMA_VERSION
                and llm_v is not None
                and llm_v.get("decision") == "refuse"
                and row.get("rule_id") is None
            )
            if not (has_v1_rule or v2_produced):
                raise ChainBroken(
                    f"seq={seq}: verdict=refuse requires EITHER rule_id+rule_version "
                    f"(v1-produced) OR llm_verdict.decision=='refuse' with rule_id=null "
                    f"(v2-produced)"
                )

        # escalate rules — version-aware on reason.
        if row["verdict"] == "escalate":
            reason = row.get("escalation_reason")
            if reason is None:
                raise ChainBroken(f"seq={seq}: verdict=escalate requires escalation_reason")
            if reason in _V2_ERA_ESCALATION_REASONS:
                if sv < _V2_SCHEMA_VERSION:
                    raise ChainBroken(
                        f"seq={seq}: escalation_reason={reason!r} is v2-only but "
                        f"schema_version={sv}"
                    )
                if reason == "llm_arbiter_escalated":
                    if llm_v is None or llm_v.get("decision") != "escalate":
                        raise ChainBroken(
                            f"seq={seq}: escalation_reason='llm_arbiter_escalated' "
                            f"requires non-null llm_verdict with decision='escalate'"
                        )
                # For crash/unavailable reasons (both Phase 4b LLM-side and
                # Phase 4c Relay-side) llm_verdict may be null; that is the
                # honest record that v2 either attempted but did not complete
                # (llm_arbiter_uncaught_exception, llm_arbiter_provider_unavailable)
                # or never ran because the integration itself failed
                # (arbiter_timeout, arbiter_unreachable).

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip


# ------------------------------------------------------- convenience factory


def build_verdict(
    *,
    correlation_id: str,
    candidate: str,
    timestamp_utc_ns: int,
    decision: Decision,
    summary: str,
    principle_id: str | None = None,
    rule_id: str | None = None,
    rule_version: int | None = None,
    escalation_reason: EscalationReason | None = None,
    llm_verdict: LlmJudgement | None = None,
    rules_run: tuple[str, ...] = (),
) -> Verdict:
    """Build a Verdict with `candidate_sha256` computed from `candidate`.

    The Verdict object is the shape `api.gate()` returns; this helper is
    used by `api.gate()` and by the test suite to avoid re-implementing
    the candidate hash in two places. `llm_verdict` records what v2 alone
    said (None iff v2 did not run).
    """
    return Verdict(
        decision=decision,
        correlation_id=correlation_id,
        candidate_sha256=_sha256_text(candidate),
        timestamp_utc_ns=timestamp_utc_ns,
        summary=summary,
        principle_id=principle_id,
        rule_id=rule_id,
        rule_version=rule_version,
        escalation_reason=escalation_reason,
        llm_verdict=llm_verdict,
        rules_run=rules_run,
    )


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "append",
    "build_verdict",
    "chain_tip",
    "iter_rows",
    "verify_chain",
]
