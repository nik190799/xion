"""Tests for `xion-verify refund-fidelity` — cross-ledger join."""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner
from orchestrator.relay import Relay
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision

from xion_verify.commands.refund_fidelity import refund_fidelity
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _invoke(repo: Path) -> tuple[int, str]:
    runner = CliRunner()
    with _chdir(repo):
        result = runner.invoke(refund_fidelity, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def _ok_gate(candidate: str, **kw):
    return safety_ledger.build_verdict(
        correlation_id=kw["correlation_id"],
        candidate=candidate,
        timestamp_utc_ns=1_700_000_000_000_000_000,
        decision=Decision.OK,
        summary="OK",
    )


def _refuse_gate(candidate: str, **kw):
    return safety_ledger.build_verdict(
        correlation_id=kw["correlation_id"],
        candidate=candidate,
        timestamp_utc_ns=1_700_000_000_000_000_000,
        decision=Decision.REFUSE,
        summary="refused",
        principle_id="7",
        rule_id="t.r_v1",
        rule_version=1,
    )


# ----- empty / half-sealed states -------------------------------------------


def test_no_ledgers_is_ok(synthetic_repo: Path):
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "no ledgers yet" in out


def test_only_safety_present_is_not_yet_sealed(synthetic_repo: Path):
    (synthetic_repo / "SAFETY_LEDGER.jsonl").write_text("", encoding="utf-8")
    code, out = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED
    assert "REQUEST_LEDGER.jsonl not present" in out


def test_only_request_present_is_not_yet_sealed(synthetic_repo: Path):
    (synthetic_repo / "REQUEST_LEDGER.jsonl").write_text("", encoding="utf-8")
    code, out = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED
    assert "SAFETY_LEDGER.jsonl not present" in out


# ----- happy paths ----------------------------------------------------------


def test_clean_paired_ledgers_pass(synthetic_repo: Path):
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    request_path = synthetic_repo / "REQUEST_LEDGER.jsonl"
    with Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_ok_gate,
    ) as relay:
        for _ in range(3):
            relay.evaluate("hello")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "3 cross-ledger pair(s) verified" in out
    assert "ok=3" in out


def test_mixed_outcomes_tally(synthetic_repo: Path):
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    request_path = synthetic_repo / "REQUEST_LEDGER.jsonl"
    with Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_ok_gate,
    ) as relay:
        relay.evaluate("a")
    with Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_refuse_gate,
    ) as relay:
        relay.evaluate("b")
        relay.evaluate("c")
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "ok=1" in out
    assert "refuse=2" in out


# ----- failure detection ----------------------------------------------------


def test_orphan_request_row_fails(synthetic_repo: Path):
    """REQUEST row with no matching SAFETY row = silent egress signature."""
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    request_path = synthetic_repo / "REQUEST_LEDGER.jsonl"
    with Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_ok_gate,
    ) as relay:
        relay.evaluate("a")
        relay.evaluate("b")
    # Truncate SAFETY_LEDGER to just the first row (a real attacker would
    # have to also rewrite the chain, but for testing the join we only need
    # to make a row disappear from one side).
    s_lines = safety_path.read_bytes().splitlines()
    safety_path.write_bytes(s_lines[0] + b"\n")
    code, err = _invoke(synthetic_repo)
    assert code == FAIL
    # Truncating SAFETY at seq=0 leaves its chain intact (single row
    # verifies cleanly); Property 1 of the join should then fire,
    # naming the REQUEST cid that has no matching SAFETY row. Asserting
    # the specific message — not just "FAIL" — distinguishes a true
    # silent-egress catch from a coincidental chain-break.
    assert "has NO matching SAFETY_LEDGER row" in err
    assert "silent egress" in err


def test_outcome_mismatch_fails(synthetic_repo: Path):
    """REQUEST.final_outcome disagreeing with SAFETY.verdict = integrity bug."""
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    request_path = synthetic_repo / "REQUEST_LEDGER.jsonl"
    with Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_ok_gate,
    ) as relay:
        relay.evaluate("a")
    # Tamper: rewrite the REQUEST row's final_outcome to "refuse".
    # The chain check will detect this if we don't recompute the hash;
    # do recompute it so we land on the cross-ledger mismatch.
    import hashlib
    line = request_path.read_bytes().splitlines()[0]
    parsed = json.loads(line)
    parsed["final_outcome"] = "refuse"
    body = {k: v for k, v in parsed.items() if k != "this_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    parsed["this_hash"] = hashlib.sha256(canonical).hexdigest()
    request_path.write_bytes(
        (json.dumps(parsed, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    )
    code, err = _invoke(synthetic_repo)
    assert code == FAIL
    assert "final_outcome" in err
