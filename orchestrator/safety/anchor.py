"""SAFETY_LEDGER_ANCHORS — periodic commitment to the ledger's chain tip.

`SAFETY_LEDGER.jsonl` alone defends against ALL tampering EXCEPT one:
tail-truncation by the party that controls the file. An attacker with
filesystem access can delete the last N rows and recompute nothing —
the remaining prefix is still a perfectly valid hash chain, because
every `prev_hash` still links. There is no way for an auditor holding
the file alone to tell "this is the full ledger" from "this is the
ledger minus the last 50 rows".

`SAFETY_LEDGER_ANCHORS` is the answer. It is a separate, shorter,
hash-chained JSONL file that records periodic commitments to the main
ledger's chain tip. Each anchor row names the main ledger's
`ledger_tip_hash` at some `ledger_row_count`. An anchor submitter then
publishes that commitment somewhere an attacker cannot silently revise
— on Arweave, or just locally with honest labelling.

The cadence policy, anchor row schema, submitter abstraction, and
wallet custody posture are specified in:

  - `docs/04-ARCHITECTURE.md` § "Safety Ledger Arweave anchoring"
  - `docs/schemas/ledger-safety-anchors.yaml`

## What this module provides (Phase 4b)

  - `AnchorSubmitter` ABC with `LocalOnlySubmitter` and an optional
    `ArweaveSubmitter` (lazily imports `arweave-python-client`).
  - `write_anchor(...)` — appends a single anchor row.
  - `should_anchor(...)` — evaluates cadence policy against current
    state, returns (True, trigger) or (False, None).
  - `verify_anchor_chain(path)` — structural verifier (same discipline
    as `ledger.verify_chain`).
  - `cross_check_anchors_against_ledger(anchors_path, ledger_path)` —
    semantic verifier that every anchor's `ledger_tip_hash` matches
    the ledger's row at `ledger_row_count - 1`.

## What this module does NOT provide

  - The long-running anchor loop (process supervisor, systemd-style
    lifecycle). That ships with the Relay in Phase 5. The CLI
    subcommand `python -m orchestrator.safety anchor` lets an
    operator run a single anchor one-shot today; a simple cron /
    Task-Scheduler wrapper turns that into a working loop until
    Phase 5 ships the supervisor.
  - The cross-gateway Arweave re-fetch check. That lives in
    `xion-verify arbiter-up --gateway <URL>` (next tranche).

## Failure posture (load-bearing)

Nothing in this module is on the Arbiter's hot path. `gate()` does
not depend on the anchor subsystem for ANYTHING — a broken anchor
pipeline (no wallet, no network, no disk space) does not cause
safety verdicts to stop being written. That separation is a
structural safety property: the Covenant's fail-closed guarantee
must not depend on network-available infrastructure.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.safety.ledger import ZERO_HASH, chain_tip

SCHEMA_VERSION = 1
"""Matches `docs/schemas/ledger-safety-anchors.yaml` schema_version."""

LEDGER_NAME = "SAFETY_LEDGER"
"""The ledger these anchors commit to. In v1 there is exactly one."""

# Cadence defaults, matching `docs/schemas/ledger-safety-anchors.yaml` cadence.
DEFAULT_ROW_COUNT_THRESHOLD = 64
DEFAULT_WALL_TIME_THRESHOLD_S = 21_600  # 6 hours

_VALID_CADENCE_TRIGGERS: frozenset[str] = frozenset({"row_count", "wall_time", "startup"})
_VALID_SUBMITTED_TO: frozenset[str] = frozenset({"local", "arweave"})


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
    """Canonicalization. MUST match the schema's `hash.canonicalization`
    block byte-for-byte."""
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------ submitter abstraction


@dataclass(frozen=True)
class AnchorReceipt:
    """What an `AnchorSubmitter` returns after publishing an anchor.

    `submitted_to` is the honest label — the place the anchor actually
    went. `ar_tx_id` and `wallet_address` are present iff
    `submitted_to == "arweave"`; `None` in the local-only case.

    This dataclass intentionally holds ONLY the fields the ledger row
    will record; it is not a general "arweave transaction receipt"
    type. Keeping it narrow keeps the submitter surface small and
    replaceable.
    """

    submitted_to: str
    ar_tx_id: str | None = None
    wallet_address: str | None = None

    def __post_init__(self) -> None:
        if self.submitted_to not in _VALID_SUBMITTED_TO:
            raise ValueError(
                f"AnchorReceipt.submitted_to must be one of {sorted(_VALID_SUBMITTED_TO)}; "
                f"got {self.submitted_to!r}"
            )
        if self.submitted_to == "arweave":
            if not self.ar_tx_id:
                raise ValueError("AnchorReceipt: submitted_to='arweave' requires non-empty ar_tx_id")
            if not self.wallet_address:
                raise ValueError("AnchorReceipt: submitted_to='arweave' requires non-empty wallet_address")
        else:
            # local-only: ar_tx_id and wallet_address MUST be None.
            if self.ar_tx_id is not None or self.wallet_address is not None:
                raise ValueError(
                    "AnchorReceipt: submitted_to='local' must have null ar_tx_id and wallet_address"
                )


class AnchorSubmitter(ABC):
    """Abstract base class for publishing an anchor commitment.

    Every concrete submitter sets `submitter_id` and `submitter_version`
    as class attributes. These are recorded on the anchor row so an
    auditor can see which submitter code made the publication — and
    that it was replaced on a specific date because its version bumped.

    `submit(body)` MAY perform I/O (HTTP, file writes to a sidecar
    registry, etc.). It MUST return an `AnchorReceipt`. It MAY raise
    on systemic failures; the anchor loop catches those and retries
    on a bounded backoff in Phase 5, or in Phase 4b surfaces them to
    the CLI operator as a nonzero exit code.

    Submitters MUST NOT mutate `body`. If they need to record
    additional metadata, they return it in the receipt.
    """

    submitter_id: str = ""
    submitter_version: int = 0

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.__dict__.get("__abstractmethods__"):
            if not getattr(cls, "submitter_id", ""):
                raise TypeError(f"{cls.__name__}: submitter_id must be set")
            if not isinstance(getattr(cls, "submitter_version", 0), int) or cls.submitter_version < 1:
                raise TypeError(f"{cls.__name__}: submitter_version must be a positive int")

    @abstractmethod
    def submit(self, body: dict[str, Any]) -> AnchorReceipt:
        """Publish `body` and return a receipt.

        `body` is the anchor record excluding submitter-side fields
        (ar_tx_id, wallet_address) and excluding the chain-internal
        fields (seq, prev_hash, this_hash). The caller fills those in.
        """


class LocalOnlySubmitter(AnchorSubmitter):
    """The default, pure-stdlib submitter.

    This submitter does not publish anywhere. It simply returns a
    receipt labelled `submitted_to: "local"`. The anchor row is still
    hash-chained and still tamper-evident against anyone who does NOT
    control this operator's local storage. Honest label; honest limits.

    When a builder ships Xion on a single host without an Arweave
    wallet, this is the right default: it costs nothing, it produces
    a correct hash chain, and the row makes no false claims of
    third-party durability.
    """

    submitter_id = "local_only_v1"
    submitter_version = 1

    def submit(self, body: dict[str, Any]) -> AnchorReceipt:
        # No I/O. The hash chain of anchor rows plus the cross-check
        # against the ledger is the value this submitter provides.
        return AnchorReceipt(submitted_to="local")


class ArweaveSubmitter(AnchorSubmitter):
    """Real Arweave submitter — publishes each anchor as a small AR tx.

    Wallet custody. See `docs/04-ARCHITECTURE.md` § "Wallet-custody
    posture (honest)" and `docs/schemas/ledger-safety-anchors.yaml`
    wallet_custody. TL;DR: this is a hot single-signer wallet whose
    only authority is "post an anchor record". Compromise publishes
    false anchors, which are detectable by honest submitters and by
    `cross_check_anchors_against_ledger`.

    Environment:
      - `XION_ANCHOR_WALLET_JWK_PATH` — path to the Arweave JWK file
        (never the JWK inline, never in shell history).
      - `XION_ANCHOR_ARWEAVE_GATEWAY` — optional; overrides the default
        `https://arweave.net` gateway.

    Dependencies:
      - `arweave-python-client>=1.0.19` (optional extra `[anchor]`).
        Imported lazily in `submit()`; `__init__` does not touch the
        network.

    Failure modes (all recorded honestly):
      - Missing JWK file -> raise (operator error; anchor loop surfaces
        and retries).
      - Arweave gateway unreachable -> raise (systemic; retryable).
      - Transaction rejected (malformed) -> raise (bug; not retryable
        without code change).

    This submitter does NOT wait for confirmation. It submits the tx
    and records `ar_tx_id` immediately. Confirmation happens at verify
    time, when `xion-verify arbiter-up --gateway` fetches the tx back
    from multiple gateways.
    """

    submitter_id = "arweave_v1"
    submitter_version = 1

    _DEFAULT_GATEWAY = "https://arweave.net"
    _JWK_PATH_ENV = "XION_ANCHOR_WALLET_JWK_PATH"
    _GATEWAY_ENV = "XION_ANCHOR_ARWEAVE_GATEWAY"

    def __init__(
        self,
        *,
        jwk_path: str | Path | None = None,
        gateway: str | None = None,
    ) -> None:
        # Both arguments are overrides for tests / explicit selection.
        # Production callers pass nothing and rely on env vars.
        if jwk_path is not None:
            self._jwk_path: str | None = str(jwk_path)
        else:
            self._jwk_path = os.environ.get(self._JWK_PATH_ENV)
        if gateway is not None:
            self._gateway = gateway
        else:
            self._gateway = os.environ.get(self._GATEWAY_ENV, self._DEFAULT_GATEWAY)

    def submit(self, body: dict[str, Any]) -> AnchorReceipt:
        try:
            import arweave  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "ArweaveSubmitter requires the `arweave-python-client` package. "
                "Install via `pip install xion-orchestrator[anchor]`."
            ) from exc

        if not self._jwk_path:
            raise RuntimeError(
                f"ArweaveSubmitter: no JWK path configured (set {self._JWK_PATH_ENV} "
                f"or pass jwk_path=)"
            )
        jwk_file = Path(self._jwk_path)
        if not jwk_file.is_file():
            raise RuntimeError(f"ArweaveSubmitter: JWK file not found: {jwk_file}")

        # Load wallet. `arweave.Wallet` signature accepts a path-to-JWK.
        wallet = arweave.Wallet(str(jwk_file))
        payload = json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        tx = arweave.Transaction(wallet, data=payload)
        # Tags are free metadata; using them lets a reader filter
        # Xion-anchor txs from all of Arweave without fetching payloads.
        tx.add_tag("App-Name", "xion-os")
        tx.add_tag("Xion-Artifact", "SAFETY_LEDGER_ANCHORS")
        tx.add_tag("Xion-Schema-Version", str(SCHEMA_VERSION))
        tx.add_tag("Xion-Ledger-Tip-Hash", str(body["ledger_tip_hash"]))
        tx.add_tag("Xion-Ledger-Row-Count", str(body["ledger_row_count"]))
        tx.sign()
        tx.send()

        return AnchorReceipt(
            submitted_to="arweave",
            ar_tx_id=str(tx.id),
            wallet_address=str(wallet.address),
        )


# ------------------------------------------------------------ cadence policy


@dataclass(frozen=True)
class CadenceDecision:
    should_anchor: bool
    trigger: str | None = None  # "row_count" | "wall_time" | "startup" | None
    reason: str = ""


@dataclass(frozen=True)
class CadencePolicy:
    """Tunable cadence policy. Defaults match the schema's Genesis Defaults.
    Tests pass tighter thresholds to exercise the triggers without
    waiting hours."""

    row_count_threshold: int = DEFAULT_ROW_COUNT_THRESHOLD
    wall_time_threshold_s: int = DEFAULT_WALL_TIME_THRESHOLD_S
    startup_anchor_required: bool = True


def should_anchor(
    *,
    anchors_path: Path,
    ledger_path: Path,
    now_utc_ns: int | None = None,
    policy: CadencePolicy | None = None,
) -> CadenceDecision:
    """Decide whether a new anchor should be written right now.

    Returns a `CadenceDecision` with:
      - `should_anchor=True` and a non-None `trigger` if cadence fires;
      - `should_anchor=False` otherwise, with a `reason` naming why.

    Decision rules (evaluated in this order):
      1. If the ledger is empty, return False ("no ledger rows to anchor").
         Writing a "here is the tip of an empty ledger" row is noise.
      2. If the anchors file is empty AND policy.startup_anchor_required
         is True, return True with trigger="startup".
      3. Compute delta_rows = ledger_row_count - last_anchor_row_count.
         If delta_rows >= policy.row_count_threshold, return True with
         trigger="row_count".
      4. Compute delta_s = (now - last_anchor_timestamp) / 1e9. If
         delta_s >= policy.wall_time_threshold_s, return True with
         trigger="wall_time".
      5. Otherwise return False.

    This function is read-only. It does not write anything, does not
    acquire locks on the anchors file, and is safe to call as often as
    the operator wants.
    """
    policy = policy or CadencePolicy()
    now = now_utc_ns if now_utc_ns is not None else time.time_ns()

    ledger_count, _ledger_tip = chain_tip(ledger_path)
    if ledger_count == 0:
        return CadenceDecision(False, None, "ledger is empty")

    last_anchor = _read_last_anchor(anchors_path)
    if last_anchor is None:
        if policy.startup_anchor_required:
            return CadenceDecision(True, "startup", "no anchor file yet")
        return CadenceDecision(False, None, "no anchor file and startup_anchor_required is False")

    last_count = int(last_anchor["ledger_row_count"])
    last_ts = int(last_anchor["timestamp_utc_ns"])
    delta_rows = ledger_count - last_count
    delta_s = (now - last_ts) / 1_000_000_000

    if delta_rows >= policy.row_count_threshold:
        return CadenceDecision(True, "row_count", f"delta_rows={delta_rows}")
    if delta_s >= policy.wall_time_threshold_s:
        return CadenceDecision(True, "wall_time", f"delta_s={delta_s:.1f}")
    return CadenceDecision(
        False,
        None,
        f"no trigger (delta_rows={delta_rows}/{policy.row_count_threshold}, "
        f"delta_s={delta_s:.1f}/{policy.wall_time_threshold_s})",
    )


# ------------------------------------------------------------------ writing


def iter_anchor_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Yield every anchor row in file order. Does not verify."""
    if not path.is_file():
        return
    with path.open("rb") as fh:
        for raw_line in fh:
            line = raw_line.rstrip(b"\n").rstrip(b"\r")
            if not line:
                continue
            yield json.loads(line.decode("utf-8"))


def _read_last_anchor(path: Path) -> dict[str, Any] | None:
    last: dict[str, Any] | None = None
    for row in iter_anchor_rows(path):
        last = row
    return last


def _read_anchor_tail(path: Path) -> tuple[int, str]:
    """Return (next_seq, prev_hash) for a fresh append."""
    last_seq = -1
    last_this = ZERO_HASH
    for row in iter_anchor_rows(path):
        last_seq = int(row["seq"])
        last_this = str(row["this_hash"])
    return last_seq + 1, last_this


def anchor_chain_tip(path: Path) -> tuple[int, str]:
    """Return (row_count, tip_hash). (0, ZERO_HASH) if file missing."""
    count = 0
    tip = ZERO_HASH
    for row in iter_anchor_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


def write_anchor(
    anchors_path: Path,
    *,
    ledger_path: Path,
    cadence_trigger: str,
    submitter: AnchorSubmitter | None = None,
    now_utc_ns: int | None = None,
) -> dict[str, Any]:
    """Compose + publish + persist a single anchor row.

    The flow:
      1. Read `chain_tip(ledger_path)` -> (ledger_row_count, ledger_tip_hash).
      2. Build the body-without-chain-fields (the submittable payload).
      3. Call `submitter.submit(body)` -> receipt.
      4. Compose the full row with seq / prev_hash / receipt fields /
         this_hash and append atomically to `anchors_path`.

    Returns the written row dict (including `this_hash`).

    Failure posture: if `submitter.submit()` raises, NOTHING is
    written to the anchors file. The operator's runbook treats this
    as "the anchor loop did not run this round; retry on the next
    cadence tick". This is the honest record: we do not pretend to
    have anchored when we did not.
    """
    if cadence_trigger not in _VALID_CADENCE_TRIGGERS:
        raise ValueError(
            f"write_anchor: cadence_trigger must be one of "
            f"{sorted(_VALID_CADENCE_TRIGGERS)}; got {cadence_trigger!r}"
        )
    submitter = submitter if submitter is not None else LocalOnlySubmitter()
    now = now_utc_ns if now_utc_ns is not None else time.time_ns()

    ledger_count, ledger_tip = chain_tip(ledger_path)
    # The submit payload is everything except chain-internal fields and
    # the receipt-sourced fields. The submitter sees this body as a
    # stable record that does not change between submit() and append().
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp_utc_ns": now,
        "ledger_name": LEDGER_NAME,
        "ledger_row_count": int(ledger_count),
        "ledger_tip_hash": str(ledger_tip),
        "cadence_trigger": cadence_trigger,
        "submitter_id": submitter.submitter_id,
        "submitter_version": int(submitter.submitter_version),
    }
    receipt = submitter.submit(body)

    lock = _lock_for(anchors_path)
    with lock:
        seq, prev_hash = _read_anchor_tail(anchors_path)
        row: dict[str, Any] = {
            **body,
            "seq": seq,
            "prev_hash": prev_hash,
            "submitted_to": receipt.submitted_to,
            "ar_tx_id": receipt.ar_tx_id,
            "wallet_address": receipt.wallet_address,
        }
        row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        line = json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        anchors_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(anchors_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
        return row


@dataclass(frozen=True)
class AnchorRunResult:
    """Human- and machine-readable outcome of a single anchor-run
    invocation. Useful for the CLI's JSON output and for tests."""

    anchored: bool
    trigger: str | None = None
    reason: str = ""
    row: dict[str, Any] | None = field(default=None)


def run_anchor_once(
    *,
    anchors_path: Path,
    ledger_path: Path,
    submitter: AnchorSubmitter | None = None,
    policy: CadencePolicy | None = None,
    force: bool = False,
    now_utc_ns: int | None = None,
) -> AnchorRunResult:
    """One-shot anchor: evaluate cadence, and if it fires (or `force`),
    publish and append exactly one anchor row.

    This is the function behind `python -m orchestrator.safety anchor`.
    Operators wrap it in cron / systemd / Task Scheduler today; the
    Relay supervisor takes over in Phase 5.

    `force=True` overrides the cadence check and anchors immediately.
    The row's `cadence_trigger` in that case is "startup" — the
    honest label for "a human deliberately invoked the submitter",
    and the only non-cadence trigger available in v1 of the schema.
    """
    if force:
        # Honesty: force-anchors label themselves as the startup trigger.
        # We could add a new "manual" trigger, but that's a schema change.
        ledger_count, _ = chain_tip(ledger_path)
        if ledger_count == 0:
            return AnchorRunResult(False, None, "ledger is empty (nothing to anchor)")
        trigger = "startup"
    else:
        decision = should_anchor(
            anchors_path=anchors_path,
            ledger_path=ledger_path,
            now_utc_ns=now_utc_ns,
            policy=policy,
        )
        if not decision.should_anchor:
            return AnchorRunResult(False, None, decision.reason)
        assert decision.trigger is not None
        trigger = decision.trigger
    row = write_anchor(
        anchors_path,
        ledger_path=ledger_path,
        cadence_trigger=trigger,
        submitter=submitter,
        now_utc_ns=now_utc_ns,
    )
    return AnchorRunResult(
        anchored=True,
        trigger=trigger,
        reason=f"trigger={trigger}",
        row=row,
    )


# -------------------------------------------------------------- verifying


class AnchorChainBroken(Exception):
    """Raised by `verify_anchor_chain` when the anchors file fails a
    structural check. Peer exception of `ledger.ChainBroken`."""


# Required top-level fields for every anchor row.
_ANCHOR_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "seq", "prev_hash", "this_hash",
    "timestamp_utc_ns", "ledger_name", "ledger_row_count",
    "ledger_tip_hash", "cadence_trigger", "submitted_to",
    "submitter_id", "submitter_version",
    # Conditional fields are ALWAYS keys on the row (value null-or-str),
    # mirroring the discipline used on SAFETY_LEDGER rows. Absence of
    # the key is a schema violation.
    "ar_tx_id", "wallet_address",
)


def verify_anchor_chain(path: Path) -> tuple[int, str]:
    """Walk the anchors file and verify structure:
      - every row has every required field,
      - schema_version matches this module's SCHEMA_VERSION,
      - seq is contiguous from 0,
      - prev_hash linkage holds,
      - this_hash recomputes,
      - submitted_to is valid; arweave rows have non-null
        ar_tx_id + wallet_address; local rows have both null,
      - cadence_trigger is valid.

    Returns (row_count, tip_hash). Raises AnchorChainBroken on failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this = ZERO_HASH

    for row in iter_anchor_rows(path):
        seq = row.get("seq", "?")
        for f in _ANCHOR_REQUIRED_FIELDS:
            if f not in row:
                raise AnchorChainBroken(f"seq={seq}: missing required field {f!r}")

        try:
            sv = int(row["schema_version"])
        except (TypeError, ValueError):
            raise AnchorChainBroken(
                f"seq={seq}: schema_version must be an int"
            ) from None
        if sv != SCHEMA_VERSION:
            raise AnchorChainBroken(
                f"seq={seq}: schema_version={sv} not supported by verifier (knows {SCHEMA_VERSION})"
            )

        if int(row["seq"]) != expected_seq:
            raise AnchorChainBroken(
                f"seq non-contiguous: expected {expected_seq}, got {row['seq']}"
            )

        if str(row["prev_hash"]) != expected_prev:
            raise AnchorChainBroken(
                f"seq={seq}: prev_hash={row['prev_hash']} != expected {expected_prev}"
            )

        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise AnchorChainBroken(
                f"seq={seq}: this_hash recomputation mismatch "
                f"(stored={row['this_hash']} recomputed={recomputed})"
            )

        if row["cadence_trigger"] not in _VALID_CADENCE_TRIGGERS:
            raise AnchorChainBroken(
                f"seq={seq}: invalid cadence_trigger {row['cadence_trigger']!r}"
            )
        if row["submitted_to"] not in _VALID_SUBMITTED_TO:
            raise AnchorChainBroken(
                f"seq={seq}: invalid submitted_to {row['submitted_to']!r}"
            )
        if row["submitted_to"] == "arweave":
            if not row.get("ar_tx_id"):
                raise AnchorChainBroken(f"seq={seq}: submitted_to=arweave requires non-null ar_tx_id")
            if not row.get("wallet_address"):
                raise AnchorChainBroken(f"seq={seq}: submitted_to=arweave requires non-null wallet_address")
        else:  # local
            if row.get("ar_tx_id") is not None:
                raise AnchorChainBroken(f"seq={seq}: submitted_to=local must have null ar_tx_id")
            if row.get("wallet_address") is not None:
                raise AnchorChainBroken(f"seq={seq}: submitted_to=local must have null wallet_address")

        if not isinstance(row.get("ledger_row_count"), int) or row["ledger_row_count"] < 0:
            raise AnchorChainBroken(f"seq={seq}: ledger_row_count must be a non-negative int")
        if row.get("ledger_name") != LEDGER_NAME:
            raise AnchorChainBroken(
                f"seq={seq}: ledger_name={row.get('ledger_name')!r} != {LEDGER_NAME!r}"
            )

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    return expected_seq, last_this


# ------------------------------------------------------ cross-check to ledger


class AnchorCrossCheckFailed(Exception):
    """Raised by `cross_check_anchors_against_ledger` when an anchor's
    named tip does not match the ledger's row at the named count."""


def cross_check_anchors_against_ledger(
    anchors_path: Path,
    ledger_path: Path,
) -> tuple[int, int]:
    """For every anchor row, assert that its `ledger_tip_hash` equals
    the ledger's `this_hash` at seq == ledger_row_count - 1.

    This is the property an auditor needs to detect silent ledger
    rewriting: if an operator truncates the ledger after anchoring,
    the next verify invocation reads the anchor, looks up the row at
    `ledger_row_count - 1`, and either (a) finds no such row (ledger
    shorter than claimed) or (b) finds a row whose this_hash does not
    match the anchor's claim.

    Returns (anchor_count, ledger_rows_covered). The second value is
    the `ledger_row_count` of the LAST anchor — i.e., how many ledger
    rows are covered by at least one anchor. Ledger rows beyond that
    point are unanchored and are the lone truncation window.

    Raises AnchorCrossCheckFailed on mismatch.
    """
    # Build an index of ledger seq -> this_hash. We read the whole
    # ledger once; acceptable for Phase 4b (ledgers are tiny at this
    # stage). Phase 5 can replace with a seek-based lookup when ledgers
    # grow into the millions.
    from orchestrator.safety.ledger import iter_rows as _iter_ledger_rows

    ledger_this_by_seq: dict[int, str] = {}
    for lrow in _iter_ledger_rows(ledger_path):
        ledger_this_by_seq[int(lrow["seq"])] = str(lrow["this_hash"])

    anchor_count = 0
    last_covered = 0
    for arow in iter_anchor_rows(anchors_path):
        anchor_count += 1
        claimed_count = int(arow["ledger_row_count"])
        claimed_tip = str(arow["ledger_tip_hash"])
        if claimed_count == 0:
            # Anchor of an empty ledger (shouldn't happen; policy skips
            # this case). If present, tip must be ZERO_HASH.
            if claimed_tip != ZERO_HASH:
                raise AnchorCrossCheckFailed(
                    f"anchor seq={arow['seq']}: ledger_row_count=0 requires ledger_tip_hash=ZERO_HASH"
                )
            last_covered = max(last_covered, 0)
            continue
        target_seq = claimed_count - 1
        actual = ledger_this_by_seq.get(target_seq)
        if actual is None:
            raise AnchorCrossCheckFailed(
                f"anchor seq={arow['seq']}: ledger_row_count={claimed_count} "
                f"but ledger has no row at seq={target_seq} (ledger truncated?)"
            )
        if actual != claimed_tip:
            raise AnchorCrossCheckFailed(
                f"anchor seq={arow['seq']}: ledger_tip_hash={claimed_tip} "
                f"does not match ledger row seq={target_seq} this_hash={actual} "
                f"(ledger silently rewritten?)"
            )
        last_covered = max(last_covered, claimed_count)
    return anchor_count, last_covered


__all__ = [
    "DEFAULT_ROW_COUNT_THRESHOLD",
    "DEFAULT_WALL_TIME_THRESHOLD_S",
    "LEDGER_NAME",
    "SCHEMA_VERSION",
    "AnchorChainBroken",
    "AnchorCrossCheckFailed",
    "AnchorReceipt",
    "AnchorRunResult",
    "AnchorSubmitter",
    "ArweaveSubmitter",
    "CadenceDecision",
    "CadencePolicy",
    "LocalOnlySubmitter",
    "anchor_chain_tip",
    "cross_check_anchors_against_ledger",
    "iter_anchor_rows",
    "run_anchor_once",
    "should_anchor",
    "verify_anchor_chain",
    "write_anchor",
]
