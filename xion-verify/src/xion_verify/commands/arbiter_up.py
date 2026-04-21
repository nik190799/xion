"""`xion-verify arbiter-up` — Arbiter posture check (Phase 4a live).

Property promised. The Arbiter library is importable, its principle registry
is self-consistent, and — if `SAFETY_LEDGER.jsonl` is present — the ledger's
hash chain verifies byte-exactly.

Exit codes:
  0 OK              library importable AND registry self-consistent AND
                    (ledger absent OR ledger chain passes `verify_chain`).
  1 FAIL            library unimportable, registry mismatch, or a present
                    ledger failed a structural check. The failure message
                    names the specific failure.
  2 NOT_YET_SEALED  never returned from here once Phase 4 has landed; the
                    Arbiter exists now. (A future version may introduce
                    this if `orchestrator.safety` is relocated and not yet
                    wired.)

Why no TCP ping in v1. `orchestrator.safety.server` is optional; the
library is the source of truth. `arbiter-up` checking a TCP endpoint would
require deciding where that endpoint lives. The operator's supervisor
monitors the daemon directly; this verifier's job is "is the Arbiter
artifact sound", not "is my daemon running".

What this subcommand DOES NOT verify (yet):
  - Arweave anchoring of the chain tip (Phase 4b).
  - Refund-fidelity ledger-to-ledger join (Phase 5).
  - Sensorium / CRS pairing (Phase 5).
Each of these has its own honest `NOT_YET_SEALED` stub.
"""

from __future__ import annotations

from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_LEDGER_NAMES: tuple[str, ...] = ("SAFETY_LEDGER.jsonl",)


def _fail(message: str) -> None:
    click.echo(f"arbiter-up: FAIL: {message}", err=True)
    raise SystemExit(FAIL)


@click.command(name="arbiter-up")
def arbiter_up() -> None:
    """Verify the Arbiter library and its local ledger posture."""

    # 1. Library importable.
    try:
        from orchestrator.safety.ledger import ChainBroken, chain_tip, verify_chain
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
    if ALLOWED_PRINCIPLE_IDS != frozenset(ids_in_tuple):
        _fail(
            "principle registry: ALLOWED_PRINCIPLE_IDS does not match ALL. "
            "This would silently break SAFETY_LEDGER principle_id validation."
        )
    for p in ALL:
        if by_id(p.id) is not p:
            _fail(f"principle registry: by_id({p.id!r}) does not round-trip.")

    # 3. Ledger chain, if present.
    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        _fail(f"{exc}")

    rows_total = 0
    tip_total = "0" * 64
    ledger_paths_checked: list[str] = []

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
        rows_total += rows
        tip_total = tip  # last non-empty tip wins; there is only one ledger in v1
        ledger_paths_checked.append(f"{name}(rows={rows}, tip={tip[:16]}...)")

    principles_tally = f"{len(ALL)} principles ({len([p for p in ALL if p.enforcement_mode.value == 'rules'])} rules-mode, {len([p for p in ALL if p.enforcement_mode.value == 'escalate'])} escalate-mode)"
    ledger_summary = "no ledger file present (no verdicts yet)" if not ledger_paths_checked else "; ".join(ledger_paths_checked)

    click.echo(
        f"arbiter-up: OK  library importable; registry consistent ({principles_tally}); "
        f"ledger: {ledger_summary}"
    )
    raise SystemExit(OK)
