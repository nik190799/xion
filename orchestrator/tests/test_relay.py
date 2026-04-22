"""Tests for `orchestrator/relay/relay.py` — the Relay class.

Property under test (per docs/04-ARCHITECTURE.md § "Relay ↔ Arbiter
integration contract"):
  - exactly one SAFETY_LEDGER row per `Relay.evaluate()`,
  - exactly one REQUEST_LEDGER row per `Relay.evaluate()`,
  - the two rows pair on `correlation_id`,
  - the SAFETY row's `verdict` equals the REQUEST row's `final_outcome`,
  - the wall-clock watchdog enforces the hard cap fail-closed,
  - gate() that raises is handled fail-closed (no row ever lost),
  - no double-write race exists when the watchdog fires.

Tests inject `gate_fn` so we never depend on a real gate() runtime.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import pytest

from orchestrator.relay import Relay, RelayResult, derive_correlation_id
from orchestrator.relay.ledger import iter_rows as iter_request_rows
from orchestrator.relay.ledger import verify_chain as verify_request_chain
from orchestrator.relay.relay import CONTRACT_VERSION, state_height_str
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision, EscalationReason, Verdict

# ----- helpers --------------------------------------------------------------


def _build_ok_verdict_factory() -> Any:
    def _gate(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK: no rule fired (test stub)",
        )
    return _gate


def _build_refuse_verdict_factory() -> Any:
    def _gate(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.REFUSE,
            summary="refused (test stub)",
            principle_id="7",
            rule_id="test.rule_v1",
            rule_version=1,
        )
    return _gate


def _build_escalate_verdict_factory() -> Any:
    def _gate(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.ESCALATE,
            summary="escalated (test stub)",
            principle_id="14",
            escalation_reason=EscalationReason.SUBJECTIVE_PRINCIPLE,
        )
    return _gate


def _hanging_gate(_sleep_seconds: float) -> Any:
    """A fake gate() that blocks for `_sleep_seconds` before returning OK."""
    def _gate(candidate: str, **kw: Any) -> Verdict:
        time.sleep(_sleep_seconds)
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK (after long sleep)",
        )
    return _gate


def _raising_gate(exc_type: type[Exception], message: str = "boom") -> Any:
    def _gate(_candidate: str, **_kw: Any) -> Verdict:
        raise exc_type(message)
    return _gate


def _wrong_type_gate() -> Any:
    def _gate(_candidate: str, **_kw: Any) -> Any:
        return "not a Verdict"
    return _gate


@pytest.fixture
def relay_paths(tmp_path: Path) -> tuple[Path, Path]:
    return tmp_path / "SAFETY_LEDGER.jsonl", tmp_path / "REQUEST_LEDGER.jsonl"


def _make_relay(
    relay_paths: tuple[Path, Path],
    *,
    gate_fn: Any,
    hard_cap_ms: int = 250,
    relay_id: str = "relay-test",
    max_workers: int = 4,
) -> Relay:
    safety_path, request_path = relay_paths
    return Relay(
        relay_id=relay_id,
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        hard_cap_ms=hard_cap_ms,
        max_workers=max_workers,
        gate_fn=gate_fn,
    )


# ----- contract version + helpers -------------------------------------------


def test_contract_version_is_one():
    assert CONTRACT_VERSION == 1


def test_state_height_str_zero_pads_to_16():
    assert state_height_str(1) == "0000000000000001"
    assert len(state_height_str(1_700_000_000_000_000_000)) >= 16


def test_state_height_str_rejects_negative():
    with pytest.raises(ValueError):
        state_height_str(-1)


def test_derive_correlation_id_shape():
    cid = derive_correlation_id(1)
    assert re.fullmatch(r"0000000000000001:[0-9a-f]{32}", cid) is not None


def test_derive_correlation_id_unique_across_calls():
    cids = {derive_correlation_id(1) for _ in range(50)}
    assert len(cids) == 50


def test_derive_correlation_id_rejects_negative_state_height():
    with pytest.raises(ValueError):
        derive_correlation_id(-1)


def test_derive_correlation_id_rejects_zero_nonce_bytes():
    with pytest.raises(ValueError):
        derive_correlation_id(1, nonce_bytes=0)


# ----- happy paths -----------------------------------------------------------


def test_evaluate_ok_writes_both_ledgers(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        result = relay.evaluate("hello")
    assert isinstance(result, RelayResult)
    assert result.egress_allowed is True
    assert result.verdict.decision is Decision.OK
    # Exactly one row in each ledger.
    assert len(list(safety_ledger.iter_rows(safety_path))) == 1
    assert len(list(iter_request_rows(request_path))) == 1
    # Correlation ids agree.
    s_row = next(safety_ledger.iter_rows(safety_path))
    r_row = next(iter_request_rows(request_path))
    assert s_row["correlation_id"] == r_row["correlation_id"] == result.correlation_id
    # final_outcome equals SAFETY verdict.
    assert r_row["final_outcome"] == s_row["verdict"] == "ok"
    # gate_call_count is 1 in Phase 5a.
    assert r_row["gate_call_count"] == 1
    # relay_id is what we passed.
    assert r_row["relay_id"] == "relay-test"


def test_evaluate_refuse_writes_both_ledgers_with_refuse_outcome(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_refuse_verdict_factory()) as relay:
        result = relay.evaluate("bad input")
    assert result.egress_allowed is False
    assert result.verdict.decision is Decision.REFUSE
    s_row = next(safety_ledger.iter_rows(safety_path))
    r_row = next(iter_request_rows(request_path))
    assert s_row["verdict"] == "refuse"
    assert r_row["final_outcome"] == "refuse"


def test_evaluate_escalate_writes_both_ledgers_with_escalate_outcome(
    relay_paths: tuple[Path, Path],
):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_escalate_verdict_factory()) as relay:
        result = relay.evaluate("hmm")
    assert result.egress_allowed is False
    assert result.verdict.decision is Decision.ESCALATE
    r_row = next(iter_request_rows(relay_paths[1]))
    assert r_row["final_outcome"] == "escalate"


def test_evaluate_emits_state_height_matching_correlation_id(
    relay_paths: tuple[Path, Path],
):
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        result = relay.evaluate("x")
    sh, _, _ = result.correlation_id.partition(":")
    r_row = next(iter_request_rows(relay_paths[1]))
    assert r_row["state_height"] == sh


def test_two_evaluations_produce_two_paired_rows_per_ledger(
    relay_paths: tuple[Path, Path],
):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        relay.evaluate("a")
        relay.evaluate("b")
    s_rows = list(safety_ledger.iter_rows(safety_path))
    r_rows = list(iter_request_rows(request_path))
    assert len(s_rows) == 2
    assert len(r_rows) == 2
    assert {row["correlation_id"] for row in s_rows} == {row["correlation_id"] for row in r_rows}


def test_chains_verify_after_multiple_evaluations(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        for _ in range(5):
            relay.evaluate("payload")
    s_count, _ = safety_ledger.verify_chain(safety_path)
    r_count, _ = verify_request_chain(request_path)
    assert s_count == r_count == 5


# ----- fail-closed: watchdog timeout ----------------------------------------


def test_watchdog_timeout_writes_arbiter_timeout_row(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    # gate() sleeps 1s; hard cap is 50ms.
    with _make_relay(
        relay_paths,
        gate_fn=_hanging_gate(1.0),
        hard_cap_ms=50,
    ) as relay:
        result = relay.evaluate("slow")
    assert result.egress_allowed is False
    assert result.verdict.decision is Decision.ESCALATE
    assert result.verdict.escalation_reason is EscalationReason.ARBITER_TIMEOUT
    # principle_id is "6" (Refusal Right) per the contract.
    assert result.verdict.principle_id == "6"
    # llm_verdict is null on timeout rows.
    s_row = next(safety_ledger.iter_rows(safety_path))
    assert s_row["llm_verdict"] is None
    assert s_row["escalation_reason"] == "arbiter_timeout"
    # REQUEST row records final_outcome=escalate.
    r_row = next(iter_request_rows(request_path))
    assert r_row["final_outcome"] == "escalate"


def test_watchdog_timeout_writes_exactly_one_safety_row(relay_paths: tuple[Path, Path]):
    """No double-write race: even though the in-flight gate() worker
    keeps running after the watchdog fires (Python cannot pre-empt),
    the SAFETY_LEDGER receives exactly one row because gate() was
    called with append_to_ledger=False."""
    safety_path, request_path = relay_paths
    with _make_relay(
        relay_paths,
        gate_fn=_hanging_gate(0.5),
        hard_cap_ms=50,
    ) as relay:
        relay.evaluate("racy")
        # Give the in-flight worker time to finish so any rogue write
        # would have happened.
        time.sleep(0.7)
    s_rows = list(safety_ledger.iter_rows(safety_path))
    r_rows = list(iter_request_rows(request_path))
    assert len(s_rows) == 1
    assert len(r_rows) == 1
    assert s_rows[0]["escalation_reason"] == "arbiter_timeout"


# ----- fail-closed: uncaught exception --------------------------------------


def test_gate_raises_writes_ruleset_uncaught_exception_row(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    with _make_relay(
        relay_paths,
        gate_fn=_raising_gate(RuntimeError, "synthetic"),
    ) as relay:
        result = relay.evaluate("crashing")
    assert result.verdict.decision is Decision.ESCALATE
    assert result.verdict.escalation_reason is EscalationReason.RULESET_UNCAUGHT_EXCEPTION
    assert result.verdict.principle_id == "6"
    s_row = next(safety_ledger.iter_rows(safety_path))
    assert s_row["escalation_reason"] == "ruleset_uncaught_exception"
    assert s_row["llm_verdict"] is None
    r_row = next(iter_request_rows(request_path))
    assert r_row["final_outcome"] == "escalate"


def test_gate_returns_wrong_type_is_uncaught(relay_paths: tuple[Path, Path]):
    with _make_relay(relay_paths, gate_fn=_wrong_type_gate()) as relay:
        result = relay.evaluate("weird")
    assert result.verdict.decision is Decision.ESCALATE
    assert result.verdict.escalation_reason is EscalationReason.RULESET_UNCAUGHT_EXCEPTION


def test_evaluate_after_close_is_uncaught(relay_paths: tuple[Path, Path]):
    relay = _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory())
    relay.close()
    result = relay.evaluate("post-close")
    assert result.verdict.decision is Decision.ESCALATE
    assert result.verdict.escalation_reason is EscalationReason.RULESET_UNCAUGHT_EXCEPTION


# ----- fail-closed: arbiter_unreachable helper ------------------------------


def test_unreachable_helper_builds_correct_verdict(relay_paths: tuple[Path, Path]):
    """Phase 6+ fail-closed path. Verify the helper exists and produces
    a well-formed verdict — the actual TCP wiring is Phase 6's job."""
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        v = relay.build_unreachable_verdict(
            candidate="x",
            correlation_id=derive_correlation_id(1),
            request_arrived_utc_ns=1_700_000_000_000_000_000,
            detail="connection refused",
        )
    assert v.decision is Decision.ESCALATE
    assert v.escalation_reason is EscalationReason.ARBITER_UNREACHABLE
    assert v.principle_id == "6"


# ----- input validation -----------------------------------------------------


def test_evaluate_non_str_candidate_raises(relay_paths: tuple[Path, Path]):
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay, pytest.raises(TypeError):
        relay.evaluate(b"bytes not str")  # type: ignore[arg-type]


def test_relay_rejects_zero_hard_cap(relay_paths: tuple[Path, Path]):
    with pytest.raises(ValueError):
        _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory(), hard_cap_ms=0)


# ----- state_height monotonicity guard --------------------------------------


def test_state_height_monotonic_under_flat_clock(relay_paths: tuple[Path, Path]):
    """A wall clock that returns the same value twice in a row must not
    produce duplicate state_heights — the per-process guard bumps."""
    safety_path, request_path = relay_paths

    fixed_ns = 1_700_000_000_000_000_000

    relay = Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_build_ok_verdict_factory(),
        clock_ns=lambda: fixed_ns,
        relay_id="relay-test",
        max_workers=2,
    )
    try:
        a = relay.evaluate("a")
        b = relay.evaluate("b")
    finally:
        relay.close()
    assert a.correlation_id != b.correlation_id
    sh_a = a.correlation_id.split(":", 1)[0]
    sh_b = b.correlation_id.split(":", 1)[0]
    assert int(sh_b, 16) > int(sh_a, 16)


def test_state_height_source_injection_works(relay_paths: tuple[Path, Path]):
    """If the operator wires state_height_source to the AO Core's head
    (Phase 6+), the Relay uses that value verbatim."""
    safety_path, request_path = relay_paths
    counter = {"n": 100}

    def _source() -> int:
        counter["n"] += 7
        return counter["n"]

    relay = Relay(
        safety_ledger_path=safety_path,
        request_ledger_path=request_path,
        gate_fn=_build_ok_verdict_factory(),
        state_height_source=_source,
        relay_id="relay-test",
        max_workers=2,
    )
    try:
        r1 = relay.evaluate("a")
        r2 = relay.evaluate("b")
    finally:
        relay.close()
    assert r1.correlation_id.startswith(state_height_str(107) + ":")
    assert r2.correlation_id.startswith(state_height_str(114) + ":")


def test_state_height_source_negative_raises(relay_paths: tuple[Path, Path]):
    relay = Relay(
        safety_ledger_path=relay_paths[0],
        request_ledger_path=relay_paths[1],
        gate_fn=_build_ok_verdict_factory(),
        state_height_source=lambda: -1,
        max_workers=2,
    )
    try:
        with pytest.raises(RuntimeError):
            relay.evaluate("x")
    finally:
        relay.close()


# ----- gate_latency_ms recording --------------------------------------------


def test_gate_latency_ms_is_recorded_in_request_row(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        result = relay.evaluate("fast")
    r_row = next(iter_request_rows(request_path))
    assert r_row["gate_latency_ms_total"] == result.gate_latency_ms
    # Sanity: a stub call should be very fast but always >= 1 (we round up).
    assert result.gate_latency_ms >= 1


# ----- contract: append_to_ledger=False from gate() actually used -----------


def test_relay_passes_append_to_ledger_false_to_gate(relay_paths: tuple[Path, Path]):
    """The Relay MUST call gate() with append_to_ledger=False to avoid
    the double-write race. Capture what we got passed."""
    captured: dict[str, Any] = {}

    def _spy(candidate: str, **kw: Any) -> Verdict:
        captured.update(kw)
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK (spy)",
        )

    with _make_relay(relay_paths, gate_fn=_spy) as relay:
        relay.evaluate("payload")
    assert captured.get("append_to_ledger") is False


# ----- close idempotency ----------------------------------------------------


def test_close_is_idempotent(relay_paths: tuple[Path, Path]):
    relay = _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory())
    relay.close()
    relay.close()  # MUST NOT raise


# ----- exhaustive cross-ledger pairing under many evaluations ---------------


def test_50_evaluations_produce_50_paired_rows(relay_paths: tuple[Path, Path]):
    safety_path, request_path = relay_paths
    with _make_relay(relay_paths, gate_fn=_build_ok_verdict_factory()) as relay:
        results = [relay.evaluate(f"msg-{i}") for i in range(50)]
    s_rows = list(safety_ledger.iter_rows(safety_path))
    r_rows = list(iter_request_rows(request_path))
    assert len(s_rows) == len(r_rows) == 50
    s_cids = {row["correlation_id"] for row in s_rows}
    r_cids = {row["correlation_id"] for row in r_rows}
    expected = {res.correlation_id for res in results}
    assert s_cids == r_cids == expected
    # Both chains verify.
    safety_ledger.verify_chain(safety_path)
    verify_request_chain(request_path)
