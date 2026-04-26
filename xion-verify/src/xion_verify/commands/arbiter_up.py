"""`xion-verify arbiter-up` — Arbiter posture check (Phase 4b live).

Properties promised:

  1. The Arbiter library (`orchestrator.safety`) is importable.
  2. Its principle registry is internally self-consistent.
  3. If `SAFETY_LEDGER.jsonl` is present, its hash chain verifies
     byte-exactly under both v1 and v2 row rules (Phase 4b).
  4. If `SAFETY_LEDGER_ANCHORS.jsonl` is present, its own hash chain
     verifies AND every anchor's claimed `ledger_tip_hash` matches
     the ledger's row at `ledger_row_count - 1` (truncation-defense
     property).

Exit codes:
  0 OK              every required property holds. A missing anchors
                    file is NOT a failure in Phase 4b — anchoring is
                    an honest layer-2 and absence is labelled.
  1 FAIL            library unimportable, registry mismatch, ledger
                    chain broken, anchors chain broken, or cross-check
                    mismatch. The failure message names the specific
                    failure.
  2 NOT_YET_SEALED  never returned from here once Phase 4 has landed.

Why no TCP ping. `orchestrator.safety.server` is optional; the library
is the source of truth. `arbiter-up` checking a TCP endpoint would
require deciding where that endpoint lives. The operator's supervisor
monitors the daemon; this verifier's job is "is the Arbiter artifact
sound", not "is my daemon running".

Not yet implemented (tracked in KNOWN_WEAKNESSES):
  - Refund-fidelity ledger-to-ledger join (Phase 5).
  - Sensorium / CRS pairing (Phase 5).
"""

from __future__ import annotations

from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER_NAMES: tuple[str, ...] = ("SAFETY_LEDGER.jsonl",)
_ANCHORS_NAME = "SAFETY_LEDGER_ANCHORS.jsonl"


def _fail(message: str) -> None:
    click.echo(f"arbiter-up: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


@click.command(name="arbiter-up")
@click.option(
    "--gateway",
    "gateways",
    multiple=True,
    help="Arweave gateway URL. Provide at least two to re-fetch arweave anchor payloads by quorum.",
)
def arbiter_up(gateways: tuple[str, ...]) -> None:
    """Verify the Arbiter library, its local ledger, and its anchors."""

    # 1. Library importable.
    try:
        from orchestrator.safety.anchor import (
            AnchorChainBroken,
            AnchorCrossCheckFailed,
            cross_check_anchors_against_ledger,
            verify_anchor_chain,
        )
        from orchestrator.safety.ledger import ChainBroken, verify_chain
        from orchestrator.safety.principles import ALL, ALLOWED_PRINCIPLE_IDS, by_id
    except Exception as exc:  # ImportError, SyntaxError, etc.
        _fail(
            f"cannot import orchestrator.safety: {type(exc).__name__}: {exc}. "
            "The Arbiter library is not importable; this is a Phase 4 regression."
        )

    # 2. Principle registry self-consistent.
    ids_in_tuple = [p.id for p in ALL]
    if len(ids_in_tuple) != len(set(ids_in_tuple)):
        _fail(
            f"principle registry has duplicate ids: {sorted(ids_in_tuple)}. "
            "See orchestrator/safety/principles.py."
        )
    if frozenset(ids_in_tuple) != ALLOWED_PRINCIPLE_IDS:
        _fail(
            "principle registry: ALLOWED_PRINCIPLE_IDS does not match ALL. "
            "This would silently break SAFETY_LEDGER principle_id validation."
        )
    for p in ALL:
        if by_id(p.id) is not p:
            _fail(f"principle registry: by_id({p.id!r}) does not round-trip.")

    # 3. Locate the repo root for file-based checks.
    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        _fail(f"{exc}")

    # 4. Ledger chain, if present.
    ledger_paths_checked: list[str] = []
    ledger_path: Path | None = None
    for name in _LEDGER_NAMES:
        p = repo_root / name
        if not p.is_file():
            continue
        try:
            rows, tip = verify_chain(p)
        except ChainBroken as exc:
            _fail(
                f"ledger {name}: chain broken at {exc}. "
                "See docs/04-ARCHITECTURE.md § Safety Ledger row schema."
            )
        ledger_path = p
        ledger_paths_checked.append(f"{name}(rows={rows}, tip={tip[:16]}...)")

    # 5. Anchors file, if present. Absence is an HONEST state in Phase 4b:
    #    the operator has not yet run the anchor loop (or has chosen to
    #    defer it). We label it and move on. Presence triggers both the
    #    structural chain check AND the cross-check to the ledger.
    anchors_path = repo_root / _ANCHORS_NAME
    anchors_summary: str
    if anchors_path.is_file():
        try:
            a_count, a_tip = verify_anchor_chain(anchors_path)
        except AnchorChainBroken as exc:
            _fail(
                f"anchors {_ANCHORS_NAME}: chain broken at {exc}. "
                "See docs/schemas/ledger-safety-anchors.yaml."
            )
        if ledger_path is not None:
            try:
                _, rows_covered = cross_check_anchors_against_ledger(
                    anchors_path, ledger_path,
                )
            except AnchorCrossCheckFailed as exc:
                _fail(
                    f"anchors {_ANCHORS_NAME}: cross-check failed: {exc}. "
                    "The ledger or the anchors file has been silently modified."
                )
            anchors_summary = (
                f"anchors(rows={a_count}, tip={a_tip[:16]}..., "
                f"covers={rows_covered}/{_ledger_rows_from_summary(ledger_paths_checked)})"
            )
            if gateways:
                gateway_summary = _verify_arweave_gateway_quorum(
                    anchors_path,
                    gateways,
                )
                anchors_summary += f"; {gateway_summary}"
        else:
            # Anchors file exists but no ledger. That is a schema violation
            # in itself — anchors commit to a ledger that is not present.
            _fail(
                f"anchors {_ANCHORS_NAME} present but ledger {_LEDGER_NAMES[0]} is missing. "
                "An anchors file without a ledger is a truncation-to-zero attack signature."
            )
    else:
        anchors_summary = "no anchors file present (anchor loop not yet run)"

    principles_tally = (
        f"{len(ALL)} principles "
        f"({len([p for p in ALL if p.enforcement_mode.value == 'rules'])} rules-mode, "
        f"{len([p for p in ALL if p.enforcement_mode.value == 'escalate'])} escalate-mode)"
    )
    ledger_summary = (
        "no ledger file present (no verdicts yet)"
        if not ledger_paths_checked
        else "; ".join(ledger_paths_checked)
    )

    click.echo(
        f"arbiter-up: OK  library importable; registry consistent ({principles_tally}); "
        f"ledger: {ledger_summary}; {anchors_summary}"
    )
    raise SystemExit(OK)


def _verify_arweave_gateway_quorum(anchors_path: Path, gateways: tuple[str, ...]) -> str:
    if len(gateways) < 2:
        _fail("--gateway requires at least two gateways for quorum verification")
    try:
        from orchestrator.data.multi_gateway_arweave import MultiGatewayArweaveReader
        from orchestrator.safety.anchor import iter_anchor_rows
    except Exception as exc:
        _fail(f"cannot import Arweave quorum reader: {type(exc).__name__}: {exc}")

    reader = MultiGatewayArweaveReader(tuple(gateways))
    checked = 0
    for row in iter_anchor_rows(anchors_path):
        if row.get("submitted_to") != "arweave":
            continue
        tx_id = str(row.get("ar_tx_id") or "")
        if not tx_id:
            _fail("arweave anchor row missing ar_tx_id")
        expected = _anchor_submit_payload(row)
        try:
            result = reader.tx_data(tx_id)
        except Exception as exc:
            _fail(f"gateway quorum failed for ar_tx_id={tx_id}: {exc}")
        if result.value != expected:
            _fail(
                f"gateway quorum payload mismatch for ar_tx_id={tx_id}; "
                "Arweave payload does not match anchor row body"
            )
        checked += 1
    return f"gateway-quorum={checked} arweave anchor(s) checked across {len(gateways)} gateways"


def _anchor_submit_payload(row: dict) -> bytes:
    import json

    excluded = {
        "seq",
        "prev_hash",
        "this_hash",
        "submitted_to",
        "ar_tx_id",
        "wallet_address",
    }
    body = {k: v for k, v in row.items() if k not in excluded}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _ledger_rows_from_summary(entries: list[str]) -> int:
    """Parse the last 'rows=<N>' from the summary entries. Purely for
    the human-readable output. Returns 0 if nothing parseable."""
    for entry in reversed(entries):
        i = entry.find("rows=")
        if i == -1:
            continue
        j = entry.find(",", i)
        if j == -1:
            continue
        try:
            return int(entry[i + 5:j])
        except ValueError:
            return 0
    return 0
