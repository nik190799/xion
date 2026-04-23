"""Tests for the Arbiter v2 primitives (Provider ABC + DeterministicStub
+ registry). These tests do NOT run `gate()`; pipeline-level tests live
in `test_api.py`. Keeping the two layers separate makes it easy to
add real providers later without blurring which layer a failure lives in.
"""

from __future__ import annotations

import hashlib

import pytest

from orchestrator.safety.llm_arbiter import (
    DeterministicStub,
    Provider,
    get_active_provider,
    is_v2_enabled,
    register_provider,
    strength_max,
)
from orchestrator.safety.types import Decision, LlmJudgement

# --------------------------------------------------------------- strength_max


def test_strength_max_ordering_refuse_wins():
    assert strength_max(Decision.OK, Decision.REFUSE) is Decision.REFUSE
    assert strength_max(Decision.REFUSE, Decision.OK) is Decision.REFUSE
    assert strength_max(Decision.ESCALATE, Decision.REFUSE) is Decision.REFUSE
    assert strength_max(Decision.REFUSE, Decision.ESCALATE) is Decision.REFUSE


def test_strength_max_ordering_escalate_beats_ok():
    assert strength_max(Decision.OK, Decision.ESCALATE) is Decision.ESCALATE
    assert strength_max(Decision.ESCALATE, Decision.OK) is Decision.ESCALATE


def test_strength_max_ok_only_when_both_ok():
    assert strength_max(Decision.OK, Decision.OK) is Decision.OK


# -------------------------------------------------------------- Provider ABC


def test_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        Provider()  # type: ignore[abstract]


def test_concrete_provider_missing_identity_rejected_at_subclass_time():
    with pytest.raises(TypeError, match="provider_id"):

        class _NoId(Provider):
            model_id = "m"
            provider_version = 1

            def enabled(self) -> bool:
                return True

            def judge(self, candidate: str) -> LlmJudgement:
                raise AssertionError("unused")


def test_concrete_provider_zero_version_rejected():
    with pytest.raises(TypeError, match="provider_version"):

        class _BadVersion(Provider):
            provider_id = "bad"
            model_id = "bad"
            provider_version = 0

            def enabled(self) -> bool:
                return True

            def judge(self, candidate: str) -> LlmJudgement:
                raise AssertionError("unused")


# ------------------------------------------------------- DeterministicStub


def test_stub_always_returns_ok():
    p = DeterministicStub()
    assert p.enabled() is True
    j = p.judge("anything")
    assert j.decision is Decision.OK
    assert j.principle_id is None
    assert j.confidence == 0.0
    assert j.provider_id == "deterministic-stub"
    assert j.model_id == "deterministic-stub"
    assert j.provider_version == 1


def test_stub_raw_output_is_candidate_independent():
    """Auditor property: the stub's raw_output is a pure function of its
    provider_version. Given only the provider_id and provider_version,
    an auditor can reproduce raw_output_sha256 without seeing the
    candidate."""
    p = DeterministicStub()
    j_a = p.judge("candidate A")
    j_b = p.judge("candidate B" * 100)
    assert j_a.raw_output == j_b.raw_output
    expected = f"{p.provider_id}:v{p.provider_version}:OK".encode()
    assert j_a.raw_output == expected
    # The sha256 of raw_output is what ends up on the ledger.
    assert hashlib.sha256(expected).hexdigest() == hashlib.sha256(j_a.raw_output).hexdigest()


def test_stub_latency_ms_non_negative():
    p = DeterministicStub()
    j = p.judge("x")
    assert isinstance(j.latency_ms, int)
    assert j.latency_ms >= 0


# ---------------------------------------------------------- v2 enable/disable


def test_is_v2_enabled_default(monkeypatch):
    monkeypatch.delenv("XION_LLM_ARBITER_DISABLED", raising=False)
    assert is_v2_enabled() is True


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "Yes"])
def test_is_v2_enabled_false_when_env_set(monkeypatch, val):
    monkeypatch.setenv("XION_LLM_ARBITER_DISABLED", val)
    assert is_v2_enabled() is False


@pytest.mark.parametrize("val", ["0", "false", "no", "", "stub"])
def test_is_v2_enabled_true_on_other_values(monkeypatch, val):
    monkeypatch.setenv("XION_LLM_ARBITER_DISABLED", val)
    assert is_v2_enabled() is True


# --------------------------------------------------------------- registry


def test_get_active_provider_default_is_stub(monkeypatch):
    monkeypatch.delenv("XION_LLM_ARBITER_PROVIDER", raising=False)
    p = get_active_provider()
    assert isinstance(p, DeterministicStub)


def test_get_active_provider_unknown_env_falls_back_to_stub(monkeypatch):
    monkeypatch.setenv("XION_LLM_ARBITER_PROVIDER", "does-not-exist")
    p = get_active_provider()
    assert isinstance(p, DeterministicStub)


def test_register_provider_roundtrip(monkeypatch):
    class _Fake(Provider):
        provider_id = "fake-test-only"
        model_id = "fake-test-only"
        provider_version = 7

        def enabled(self) -> bool:
            return True

        def judge(self, candidate: str) -> LlmJudgement:
            return LlmJudgement(
                provider_id=self.provider_id,
                model_id=self.model_id,
                provider_version=self.provider_version,
                latency_ms=0,
                decision=Decision.OK,
                summary="fake",
                raw_output=b"fake",
            )

    register_provider(_Fake)
    monkeypatch.setenv("XION_LLM_ARBITER_PROVIDER", "fake-test-only")
    p = get_active_provider()
    assert isinstance(p, _Fake)
    assert p.provider_version == 7


def test_register_provider_rejects_non_subclass():
    with pytest.raises(TypeError):
        register_provider(object)  # type: ignore[arg-type]


def test_register_provider_rejects_abstract_base():
    with pytest.raises(TypeError):
        register_provider(Provider)


# -------------------------------------------------------------- LlmJudgement


def test_llm_judgement_ok_with_principle_id_rejected():
    with pytest.raises(ValueError, match="principle_id must be None when decision is OK"):
        LlmJudgement(
            provider_id="p",
            model_id="m",
            provider_version=1,
            latency_ms=0,
            decision=Decision.OK,
            summary="",
            raw_output=b"",
            principle_id="3",
        )


def test_llm_judgement_non_ok_requires_principle_id():
    with pytest.raises(ValueError, match="principle_id required"):
        LlmJudgement(
            provider_id="p",
            model_id="m",
            provider_version=1,
            latency_ms=0,
            decision=Decision.REFUSE,
            summary="",
            raw_output=b"",
            principle_id=None,
        )


def test_llm_judgement_confidence_range():
    # In range.
    LlmJudgement(
        provider_id="p",
        model_id="m",
        provider_version=1,
        latency_ms=0,
        decision=Decision.OK,
        summary="",
        raw_output=b"",
        confidence=0.5,
    )
    with pytest.raises(ValueError, match="confidence"):
        LlmJudgement(
            provider_id="p",
            model_id="m",
            provider_version=1,
            latency_ms=0,
            decision=Decision.OK,
            summary="",
            raw_output=b"",
            confidence=1.5,
        )


def test_llm_judgement_negative_latency_rejected():
    with pytest.raises(ValueError, match="latency_ms"):
        LlmJudgement(
            provider_id="p",
            model_id="m",
            provider_version=1,
            latency_ms=-1,
            decision=Decision.OK,
            summary="",
            raw_output=b"",
        )
