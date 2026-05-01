"""Tests for `xion-verify refund-fidelity` — cross-ledger join."""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner
from orchestrator.relay import Relay
from orchestrator.relay.ledger import (
    ProviderAttemptRecord,
    append_provider_attempt,
)
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


# ----- v2 multi-attempt provider rows (Phase 5g-vii) ------------------------
#
# These tests verify that `refund-fidelity` correctly handles the v2
# REQUEST_LEDGER rows that `orchestrator/api/chat.py` writes per
# provider-attempt. Each test seeds a clean v1 gate-call row first (so
# the v2 rows have a matching correlation_id to join against under
# Property 7), then appends v2 rows to exercise a specific invariant.


def _seed_v1_turn(synthetic_repo: Path) -> tuple[Path, Path, str]:
    """Write a single clean v1 row and return its correlation_id."""
    safety_path = synthetic_repo / "SAFETY_LEDGER.jsonl"
    request_path = synthetic_repo / "REQUEST_LEDGER.jsonl"
    with Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_ok_gate,
    ) as relay:
        result = relay.evaluate("hello")
    cid = result.correlation_id
    return safety_path, request_path, cid


def _v2_row(
    cid: str,
    *,
    chat_turn_id: str = "a" * 32,
    attempt_index: int = 0,
    provider_id: str = "fake-hosted",
    outcome: str = "success",
    failure_reason_class: str | None = None,
) -> ProviderAttemptRecord:
    state_height, _nonce = cid.split(":", 1)
    return ProviderAttemptRecord(
        correlation_id=cid,
        state_height=state_height,
        relay_id="relay-test",
        request_arrived_utc_ns=1_700_000_000_000_000_000,
        responded_utc_ns=1_700_000_000_000_000_100,
        chat_turn_id=chat_turn_id,
        attempt_index=attempt_index,
        provider_id=provider_id,
        outcome=outcome,
        failure_reason_class=failure_reason_class,
    )


def test_v2_clean_single_success_turn_passes(synthetic_repo: Path):
    _safety, request_path, cid = _seed_v1_turn(synthetic_repo)
    append_provider_attempt(request_path, _v2_row(cid))
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "v2 attempt rows: turns=1" in out
    assert "success=1" in out


def test_v2_clean_fallback_turn_passes(synthetic_repo: Path):
    """Hosted fails on credits -> floor succeeds: two v2 rows, terminal
    success, distinct providers."""
    _safety, request_path, cid = _seed_v1_turn(synthetic_repo)
    append_provider_attempt(
        request_path,
        _v2_row(
            cid,
            attempt_index=0,
            provider_id="hosted",
            outcome="failure",
            failure_reason_class="insufficient_credits",
        ),
    )
    append_provider_attempt(
        request_path,
        _v2_row(cid, attempt_index=1, provider_id="sentinel-llm-v0"),
    )
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "success=1" in out
    assert "insufficient_credits=1" in out


def test_v2_orphan_correlation_id_fails_property_7(synthetic_repo: Path):
    """v2 row with a correlation_id that has no v1 peer = Property 7
    violation."""
    _safety_path, request_path, _real_cid = _seed_v1_turn(synthetic_repo)
    fake_cid = "deadbeefdeadbeef:" + "0" * 32
    append_provider_attempt(request_path, _v2_row(fake_cid))
    code, err = _invoke(synthetic_repo)
    assert code == FAIL
    assert "v2" in err
    assert "NO matching v1 gate-call row" in err


def test_v2_attempt_index_gap_fails_property_8(synthetic_repo: Path):
    """attempt_index = [0, 2] is not {0, 1, ..., N-1} — Property 8
    violation. Writing that requires bypassing `append_provider_attempt`'s
    own contiguity check is NOT what we want — we want to catch it at
    verify-chain time. But `verify_chain` already rejects it at
    chain-level before the refund-fidelity command runs its own check.
    So this test simply confirms the chain-break path surfaces with a
    message that an operator can trace."""
    _safety, request_path, cid = _seed_v1_turn(synthetic_repo)
    append_provider_attempt(request_path, _v2_row(cid, attempt_index=0))
    # Insert a second row at attempt_index=2, skipping 1. `verify_chain`
    # on the REQUEST_LEDGER will catch the gap; refund-fidelity's
    # _fail('REQUEST_LEDGER chain broken') surfaces.
    append_provider_attempt(
        request_path,
        _v2_row(
            cid,
            attempt_index=2,
            provider_id="floor",
            outcome="failure",
            failure_reason_class="timeout",
        ),
    )
    code, err = _invoke(synthetic_repo)
    assert code == FAIL
    # Either the chain-break or the Property-8 shape error is acceptable;
    # both are true and both name the offending row:
    assert (
        "attempt_index sequence" in err
        or "REQUEST_LEDGER chain broken" in err
    )


def test_v2_two_success_rows_fails_property_8(synthetic_repo: Path):
    """Two rows with outcome=success in one chat_turn_id = the fallback
    loop didn't short-circuit — Property 8 'at most one success'."""
    _safety, request_path, cid = _seed_v1_turn(synthetic_repo)
    append_provider_attempt(
        request_path,
        _v2_row(cid, attempt_index=0, outcome="success"),
    )
    append_provider_attempt(
        request_path,
        _v2_row(cid, attempt_index=1, outcome="success"),
    )
    code, err = _invoke(synthetic_repo)
    assert code == FAIL
    assert "outcome='success'" in err
    assert "at most once" in err


def test_v2_non_terminal_success_fails_property_8(synthetic_repo: Path):
    """Success at attempt 0 with a failure row at attempt 1 = the
    handler kept trying after success — Property 8 terminality."""
    _safety, request_path, cid = _seed_v1_turn(synthetic_repo)
    append_provider_attempt(
        request_path,
        _v2_row(cid, attempt_index=0, outcome="success"),
    )
    append_provider_attempt(
        request_path,
        _v2_row(
            cid,
            attempt_index=1,
            outcome="failure",
            failure_reason_class="timeout",
        ),
    )
    code, err = _invoke(synthetic_repo)
    assert code == FAIL
    assert "not the terminal attempt" in err


def test_v2_all_fail_turn_passes(synthetic_repo: Path):
    """A turn where every provider failed is a LEGAL shape (a 503 to
    the user). verify passes; summary reflects all-fail."""
    _safety, request_path, cid = _seed_v1_turn(synthetic_repo)
    append_provider_attempt(
        request_path,
        _v2_row(
            cid,
            attempt_index=0,
            provider_id="hosted",
            outcome="failure",
            failure_reason_class="insufficient_credits",
        ),
    )
    append_provider_attempt(
        request_path,
        _v2_row(
            cid,
            attempt_index=1,
            provider_id="floor",
            outcome="failure",
            failure_reason_class="provider_unreachable",
        ),
    )
    code, out = _invoke(synthetic_repo)
    assert code == OK
    assert "all_fail=1" in out
    assert "insufficient_credits=1" in out
    assert "provider_unreachable=1" in out
