"""End-to-end tests for `gate()`. The public surface contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.safety import Decision, gate
from orchestrator.safety.ledger import iter_rows, verify_chain
from orchestrator.safety.llm_arbiter import Provider
from orchestrator.safety.types import EscalationReason, LlmJudgement


def test_gate_ok_writes_ok_row(ledger_path: Path):
    v = gate("The report is due Monday.", correlation_id="c-ok", ledger_path=ledger_path)
    assert v.decision is Decision.OK
    assert v.egress_allowed is True
    rows = list(iter_rows(ledger_path))
    assert len(rows) == 1
    assert rows[0]["verdict"] == "ok"
    assert rows[0]["correlation_id"] == "c-ok"
    assert rows[0]["principle_id"] is None


def test_gate_refuse_writes_refuse_row(ledger_path: Path):
    v = gate("Her SSN is 123-45-6789.", correlation_id="c-refuse", ledger_path=ledger_path)
    assert v.decision is Decision.REFUSE
    assert v.egress_allowed is False
    assert v.principle_id == "7"
    assert v.rule_id is not None
    rows = list(iter_rows(ledger_path))
    assert rows[0]["verdict"] == "refuse"
    assert rows[0]["principle_id"] == "7"


def test_gate_escalate_writes_escalate_row(ledger_path: Path):
    v = gate("Sometimes I just want to die.", correlation_id="c-escalate", ledger_path=ledger_path)
    assert v.decision is Decision.ESCALATE
    assert v.egress_allowed is False
    assert v.principle_id == "10"
    rows = list(iter_rows(ledger_path))
    assert rows[0]["verdict"] == "escalate"
    assert rows[0]["escalation_reason"] is not None


def test_gate_every_call_writes_exactly_one_row(ledger_path: Path):
    for i in range(10):
        gate(f"benign text {i}", correlation_id=f"c-{i}", ledger_path=ledger_path)
    rows = list(iter_rows(ledger_path))
    assert len(rows) == 10
    for i, row in enumerate(rows):
        assert row["correlation_id"] == f"c-{i}"
        assert row["seq"] == i
    count, tip = verify_chain(ledger_path)
    assert count == 10


def test_gate_rejects_empty_correlation_id(ledger_path: Path):
    with pytest.raises(ValueError):
        gate("hi", correlation_id="", ledger_path=ledger_path)


def test_gate_rejects_non_string_correlation_id(ledger_path: Path):
    with pytest.raises(ValueError):
        gate("hi", correlation_id=None, ledger_path=ledger_path)  # type: ignore[arg-type]


def test_gate_preserves_empty_candidate(ledger_path: Path):
    # An empty string is a valid candidate (model may emit empty output);
    # it should be OK-verdict and logged normally.
    v = gate("", correlation_id="c-empty", ledger_path=ledger_path)
    assert v.decision is Decision.OK
    assert v.candidate_sha256 == (
        # sha256 of empty bytes
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_gate_timestamp_override_is_written(ledger_path: Path):
    v = gate("hi", correlation_id="c-ts", ledger_path=ledger_path, now_utc_ns=1_700_000_000_000_000_000)
    rows = list(iter_rows(ledger_path))
    assert rows[0]["timestamp_utc_ns"] == 1_700_000_000_000_000_000
    assert v.timestamp_utc_ns == 1_700_000_000_000_000_000


def test_gate_rules_run_trace_populated_on_ok(ledger_path: Path):
    v = gate("benign", correlation_id="c-trace", ledger_path=ledger_path)
    assert len(v.rules_run) == 8
    # Trace is in-process only; not in the ledger row.
    rows = list(iter_rows(ledger_path))
    assert "rules_run" not in rows[0]


# ================================================================== v2 pipeline


class _FakeProvider(Provider):
    """In-test provider with scriptable decision. Used to exercise the
    v2 pipeline paths in `gate()` without any I/O."""

    provider_id = "fake-v2-for-tests"
    model_id = "fake-v2-for-tests"
    provider_version = 1

    def __init__(
        self,
        *,
        decision: Decision = Decision.OK,
        principle_id: str | None = None,
        summary: str = "fake",
        raise_on_enabled: bool = False,
        enabled_value: bool = True,
        raise_on_judge: Exception | None = None,
        return_garbage: bool = False,
    ) -> None:
        self._decision = decision
        self._principle_id = principle_id
        self._summary = summary
        self._raise_on_enabled = raise_on_enabled
        self._enabled_value = enabled_value
        self._raise_on_judge = raise_on_judge
        self._return_garbage = return_garbage

    def enabled(self) -> bool:
        if self._raise_on_enabled:
            raise RuntimeError("config corrupt")
        return self._enabled_value

    def judge(self, candidate: str):
        if self._raise_on_judge is not None:
            raise self._raise_on_judge
        if self._return_garbage:
            return "not an LlmJudgement"  # type: ignore[return-value]
        return LlmJudgement(
            provider_id=self.provider_id,
            model_id=self.model_id,
            provider_version=self.provider_version,
            latency_ms=1,
            decision=self._decision,
            summary=self._summary,
            raw_output=b"fake-raw",
            principle_id=self._principle_id,
        )


def test_v2_runs_on_v1_ok_records_llm_verdict(ledger_path: Path):
    v = gate(
        "benign text",
        correlation_id="c-v2-ok",
        ledger_path=ledger_path,
        llm_provider=_FakeProvider(decision=Decision.OK),
    )
    assert v.decision is Decision.OK
    assert v.llm_verdict is not None
    assert v.llm_verdict.decision is Decision.OK
    row = next(iter(iter_rows(ledger_path)))
    assert row["schema_version"] == 2
    assert row["llm_verdict"] is not None
    assert row["llm_verdict"]["decision"] == "ok"
    assert row["llm_verdict"]["provider_id"] == "fake-v2-for-tests"


def test_v2_skipped_on_v1_refuse_llm_verdict_null(ledger_path: Path):
    # PII rule refuses; v2 must not run.
    fake = _FakeProvider(decision=Decision.OK, raise_on_judge=AssertionError("MUST NOT RUN"))
    v = gate(
        "Her SSN is 123-45-6789.",
        correlation_id="c-v2-skip-on-refuse",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.REFUSE
    assert v.llm_verdict is None
    row = next(iter(iter_rows(ledger_path)))
    assert row["schema_version"] == 2
    assert row["llm_verdict"] is None
    assert row["rule_id"] is not None


def test_v2_skipped_on_v1_escalate_llm_verdict_null(ledger_path: Path):
    fake = _FakeProvider(decision=Decision.OK, raise_on_judge=AssertionError("MUST NOT RUN"))
    v = gate(
        "Sometimes I just want to die.",
        correlation_id="c-v2-skip-on-escalate",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.ESCALATE
    assert v.llm_verdict is None
    row = next(iter(iter_rows(ledger_path)))
    assert row["llm_verdict"] is None


def test_v2_escalates_v1_ok(ledger_path: Path):
    fake = _FakeProvider(
        decision=Decision.ESCALATE,
        principle_id="3",
        summary="semantically suspicious",
    )
    v = gate(
        "benign-looking text",
        correlation_id="c-v2-escalate",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.ESCALATE
    assert v.escalation_reason is EscalationReason.LLM_ARBITER_ESCALATED
    assert v.principle_id == "3"
    assert v.llm_verdict is not None
    assert v.llm_verdict.decision is Decision.ESCALATE
    row = next(iter(iter_rows(ledger_path)))
    assert row["verdict"] == "escalate"
    assert row["escalation_reason"] == "llm_arbiter_escalated"
    assert row["llm_verdict"]["decision"] == "escalate"


def test_v2_refuses_v1_ok_rule_id_is_null(ledger_path: Path):
    fake = _FakeProvider(
        decision=Decision.REFUSE,
        principle_id="2",
        summary="mass-harm adversarial",
    )
    v = gate(
        "benign-looking text",
        correlation_id="c-v2-refuse",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.REFUSE
    assert v.rule_id is None
    assert v.principle_id == "2"
    assert v.llm_verdict is not None
    assert v.llm_verdict.decision is Decision.REFUSE
    row = next(iter(iter_rows(ledger_path)))
    assert row["verdict"] == "refuse"
    assert row["rule_id"] is None
    assert row["llm_verdict"]["decision"] == "refuse"
    # The chain must verify even with a v2-produced refuse row.
    count, _ = verify_chain(ledger_path)
    assert count == 1


def test_v2_never_weakens_v1_ok_is_only_ok_when_both_ok(ledger_path: Path):
    """no-weakening property, stated positively: the final decision is
    strength_max(v1, v2). Since v1 is OK on the benign candidate, only
    a v2-OK produces a final-OK; v2-ESCALATE/REFUSE strengthen."""
    for d in (Decision.OK, Decision.ESCALATE, Decision.REFUSE):
        from pathlib import Path as _P  # local to keep outer fixture per-test
        ledger = _P(str(ledger_path) + f".{d.value}")
        fake = _FakeProvider(
            decision=d,
            principle_id="3" if d is not Decision.OK else None,
        )
        v = gate(
            "benign",
            correlation_id=f"c-noweak-{d.value}",
            ledger_path=ledger,
            llm_provider=fake,
        )
        if d is Decision.OK:
            assert v.decision is Decision.OK
        else:
            assert v.decision is d


def test_v2_exception_escalates_llm_verdict_null(ledger_path: Path):
    fake = _FakeProvider(raise_on_judge=RuntimeError("boom"))
    v = gate(
        "benign",
        correlation_id="c-v2-crash",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.ESCALATE
    assert v.escalation_reason is EscalationReason.LLM_ARBITER_UNCAUGHT_EXCEPTION
    assert v.llm_verdict is None
    row = next(iter(iter_rows(ledger_path)))
    assert row["verdict"] == "escalate"
    assert row["escalation_reason"] == "llm_arbiter_uncaught_exception"
    assert row["llm_verdict"] is None
    count, _ = verify_chain(ledger_path)
    assert count == 1


def test_v2_enabled_false_escalates_as_provider_unavailable(ledger_path: Path):
    fake = _FakeProvider(enabled_value=False)
    v = gate(
        "benign",
        correlation_id="c-v2-unavailable",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.ESCALATE
    assert v.escalation_reason is EscalationReason.LLM_ARBITER_PROVIDER_UNAVAILABLE
    assert v.llm_verdict is None


def test_v2_enabled_raises_treated_as_unavailable(ledger_path: Path):
    fake = _FakeProvider(raise_on_enabled=True)
    v = gate(
        "benign",
        correlation_id="c-v2-enabled-raise",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.ESCALATE
    assert v.escalation_reason is EscalationReason.LLM_ARBITER_PROVIDER_UNAVAILABLE
    assert v.llm_verdict is None


def test_v2_garbage_return_fails_closed(ledger_path: Path):
    fake = _FakeProvider(return_garbage=True)
    v = gate(
        "benign",
        correlation_id="c-v2-garbage",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.ESCALATE
    assert v.escalation_reason is EscalationReason.LLM_ARBITER_UNCAUGHT_EXCEPTION


def test_v2_disabled_via_flag_llm_verdict_null(ledger_path: Path):
    fake = _FakeProvider(raise_on_judge=AssertionError("MUST NOT RUN"))
    v = gate(
        "benign",
        correlation_id="c-v2-disabled",
        ledger_path=ledger_path,
        llm_provider=fake,
        enable_llm_arbiter=False,
    )
    assert v.decision is Decision.OK
    assert v.llm_verdict is None
    row = next(iter(iter_rows(ledger_path)))
    assert row["llm_verdict"] is None
    assert row["schema_version"] == 2


def test_v2_disabled_via_env_llm_verdict_null(ledger_path: Path, monkeypatch):
    monkeypatch.setenv("XION_LLM_ARBITER_DISABLED", "1")
    fake = _FakeProvider(raise_on_judge=AssertionError("MUST NOT RUN"))
    v = gate(
        "benign",
        correlation_id="c-v2-env-disabled",
        ledger_path=ledger_path,
        llm_provider=fake,
    )
    assert v.decision is Decision.OK
    assert v.llm_verdict is None


def test_v2_mixed_verdicts_chain_verifies(ledger_path: Path):
    """End-to-end: mix of v1-refuse, v1-ok+v2-ok, v1-ok+v2-escalate,
    v1-ok+v2-refuse, v2-crash. Final chain must verify under the
    Phase 4b verifier rules."""
    gate(
        "Her SSN is 123-45-6789.",
        correlation_id="c-mix-1",
        ledger_path=ledger_path,
        llm_provider=_FakeProvider(decision=Decision.OK),
    )
    gate(
        "benign a",
        correlation_id="c-mix-2",
        ledger_path=ledger_path,
        llm_provider=_FakeProvider(decision=Decision.OK),
    )
    gate(
        "benign b",
        correlation_id="c-mix-3",
        ledger_path=ledger_path,
        llm_provider=_FakeProvider(decision=Decision.ESCALATE, principle_id="3"),
    )
    gate(
        "benign c",
        correlation_id="c-mix-4",
        ledger_path=ledger_path,
        llm_provider=_FakeProvider(decision=Decision.REFUSE, principle_id="2"),
    )
    gate(
        "benign d",
        correlation_id="c-mix-5",
        ledger_path=ledger_path,
        llm_provider=_FakeProvider(raise_on_judge=RuntimeError("sim crash")),
    )
    count, _ = verify_chain(ledger_path)
    assert count == 5
