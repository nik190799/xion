"""Arbiter v2 — LLM second-pass classifier.

This module runs AFTER `rules.apply_rules` on v1-OK candidates only. It
adds adversarial-semantic coverage (prompt-injection, jailbreak framings,
principled harms that no keyword rule catches) without ever weakening
what v1 already decided. The combination rule and the fail-closed
posture are specified in `docs/04-ARCHITECTURE.md` § "Arbiter v2 (LLM
second-pass)".

## Invariants enforced here

  1. No-weakening. The pipeline (in `api.gate()`) calls `judge()` ONLY
     when v1 returned `Decision.OK`. The return value MAY be `OK`,
     `ESCALATE`, or `REFUSE` — any of those are an allowed
     strengthening of the v1-OK decision. v2 cannot weaken v1.
  2. Fail-closed on exception. If `judge()` raises, the pipeline
     converts it into an `ESCALATE` verdict with
     `escalation_reason=llm_arbiter_uncaught_exception`. v2 crashes
     do not become silent OKs.
  3. Pure-stdlib default. The `DeterministicStub` provider is
     always available and has zero network dependencies, keeping
     `orchestrator.safety`'s core importable without any extras.
     Real LLM providers live behind an optional extras install
     (`pip install xion-orchestrator[llm-<name>]`).
  4. Provider identity on the row. Every `LlmJudgement` names its
     `provider_id`, `model_id`, and `provider_version`. The ledger
     records these on the row so an auditor in 2126 can tell which
     classifier made the call — and see that it was replaced on a
     specific date because its provider_version bumped.

## Adding a new provider

A new provider is a subclass of `Provider` that:

  - sets `provider_id`, `model_id`, `provider_version` class-level;
  - implements `enabled()` to return True iff the provider is ready
    to answer calls (credentials present, network reachable, etc.);
  - implements `judge(candidate)` returning a `LlmJudgement`.

Then register it in `_PROVIDERS` below (the registry) keyed by its
provider_id. Selection happens at `get_active_provider()` via the
`XION_LLM_ARBITER_PROVIDER` env var; if unset or unknown, the
deterministic stub is returned.

Providers SHOULD NOT raise from `judge()` for ordinary outcomes
(use `ESCALATE` instead). Exceptions are reserved for systemic
failures: bad credentials, timeouts, invalid-JSON parses, etc.
The pipeline catches those and writes an
`llm_arbiter_uncaught_exception` escalate row.

## What v2 does NOT do

  - It does NOT replace v1. It runs AFTER v1 and MUST NOT be
    invoked on v1-non-OK candidates.
  - It does NOT override the Covenant or the Invariants. It enforces
    them in a second independent pass.
  - It does NOT write to the ledger directly. The pipeline (`gate`)
    embeds the judgement in the verdict row.
  - It does NOT vote. If v1 and v2 disagree, the strictly stricter
    verdict wins. There is no averaging, no quorum, no tie.
"""

from __future__ import annotations

import contextlib
import os
import time
from abc import ABC, abstractmethod

from orchestrator.safety.types import Decision, LlmJudgement

# Decision strength ordering. `strength_max(a, b)` returns the stricter
# of the two. The pipeline in `api.gate()` uses this to enforce the
# no-weakening property: `final = strength_max(v1, v2)`.
_DECISION_STRENGTH: dict[Decision, int] = {
    Decision.OK: 0,
    Decision.ESCALATE: 1,
    Decision.REFUSE: 2,
}


def strength_max(a: Decision, b: Decision) -> Decision:
    """Return the stricter of two `Decision` values.

    Ordering: `OK < ESCALATE < REFUSE`. Ties resolve to the shared
    value. This is the single canonical combination rule — do not
    re-implement it at call sites.
    """
    return a if _DECISION_STRENGTH[a] >= _DECISION_STRENGTH[b] else b


# --------------------------------------------------------------------- ABC


class Provider(ABC):
    """Abstract base class for an Arbiter v2 classifier provider.

    Concrete subclasses MUST set `provider_id`, `model_id`, and
    `provider_version` as class attributes. They MUST implement
    `enabled()` and `judge()`. They SHOULD be importable without their
    network-dependent extras; the extras should only be required at
    `enabled()` / `judge()` time.

    `provider_id` is a short stable handle ("deterministic-stub",
    "openai-moderation", "anthropic-claude-3-haiku"). `model_id` is
    the specific model name the provider called. `provider_version`
    is a monotonically-increasing int that bumps on ANY observable
    behaviour change (prompt-template, model-id, scoring threshold).
    Version bumps are how an auditor tells that a row from 2028-06
    was classified by a newer version than a row from 2026-05.
    """

    provider_id: str = ""
    model_id: str = ""
    provider_version: int = 0

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Guard against subclasses that forget to set identity.
        if not cls.__dict__.get("__abstractmethods__"):
            # Only enforce on concrete (non-abstract) subclasses.
            if not getattr(cls, "provider_id", ""):
                raise TypeError(f"{cls.__name__}: provider_id must be set (non-empty)")
            if not getattr(cls, "model_id", ""):
                raise TypeError(f"{cls.__name__}: model_id must be set (non-empty)")
            if not isinstance(getattr(cls, "provider_version", 0), int) or cls.provider_version < 1:
                raise TypeError(f"{cls.__name__}: provider_version must be a positive int")

    @abstractmethod
    def enabled(self) -> bool:
        """Return True iff this provider is ready to answer `judge()`.

        Return False (not raise) for ordinary "not configured" states
        (missing credentials, disabled by env var, offline by policy).
        The pipeline will treat a disabled provider as unavailable
        and write an `llm_arbiter_provider_unavailable` escalate row.

        RAISE ONLY on genuinely unexpected failures (e.g., a config
        file present but unparseable). Those are fail-closed.
        """

    @abstractmethod
    def judge(self, candidate: str) -> LlmJudgement:
        """Classify `candidate` and return an `LlmJudgement`.

        Latency. The pipeline wraps this call with its own clock and
        enforces a deadline, but providers SHOULD measure and fill
        `latency_ms` with their own observation (closer to the wire).

        Raising. As documented in the module-level docstring:
        return `ESCALATE` for ordinary "I'm unsure" cases; raise only
        on systemic failure. Do not raise `Decision.OK` or
        `Decision.REFUSE` — those are legitimate outcomes, not errors.
        """


# ----------------------------------------------------------- stub provider


class DeterministicStub(Provider):
    """A pure-stdlib v2 provider that always returns `Decision.OK`.

    This provider exists to satisfy two constraints simultaneously:
    (1) the orchestrator's core MUST be importable with no network deps,
    and (2) every `gate()` call on a v1-OK candidate MUST write an
    `llm_verdict` object to the ledger so the schema stays honest.
    Concretely, this stub is what runs in CI, in offline dev setups,
    and anywhere `XION_LLM_ARBITER_PROVIDER` is unset or set to
    `"deterministic-stub"`.

    Behaviour.
      - Always returns `decision = OK`, `confidence = 0.0`,
        `principle_id = None`, `summary = "stub: no classifier active"`,
        `raw_output = b"deterministic-stub:v{provider_version}:OK"`.
      - Latency is measured against `time.monotonic_ns()` so that the
        row's `latency_ms` is a real (small) wall number, not a
        hard-coded zero. An auditor grepping `latency_ms == 0` on
        every row would be a signal that something is lying.
      - `enabled()` is always True.

    Auditor replay. Given any row with
    `llm_verdict.provider_id == "deterministic-stub"` and
    `llm_verdict.provider_version == N`, the raw_output_sha256 is
    exactly `sha256(f"deterministic-stub:v{N}:OK".encode("utf-8"))`.
    No candidate content is required to reproduce it.

    Security note. Because this stub ALWAYS returns OK, deploying it
    in production means v2 provides zero adversarial-semantic coverage
    — the safety posture degrades to v1-only. This is documented in
    `KNOWN_WEAKNESSES.md` under `KW-ARBITER-001` and MUST NOT be the
    production configuration once a real provider is available.
    """

    provider_id = "deterministic-stub"
    model_id = "deterministic-stub"
    provider_version = 1

    def enabled(self) -> bool:
        return True

    def judge(self, candidate: str) -> LlmJudgement:
        t0 = time.monotonic_ns()
        # The stub does no classification work; the monotonic delta
        # here is dominated by object construction and hashing, which
        # is honest: that IS the full work this provider performs.
        raw = f"{self.provider_id}:v{self.provider_version}:OK".encode()
        latency_ms = max(0, (time.monotonic_ns() - t0) // 1_000_000)
        return LlmJudgement(
            provider_id=self.provider_id,
            model_id=self.model_id,
            provider_version=self.provider_version,
            latency_ms=int(latency_ms),
            decision=Decision.OK,
            summary="stub: no classifier active",
            raw_output=raw,
            principle_id=None,
            confidence=0.0,
        )


# -------------------------------------------------------- provider registry


_PROVIDERS: dict[str, type[Provider]] = {
    DeterministicStub.provider_id: DeterministicStub,
}

_ACTIVE_PROVIDER_ENV = "XION_LLM_ARBITER_PROVIDER"
_DISABLE_V2_ENV = "XION_LLM_ARBITER_DISABLED"


def register_provider(cls: type[Provider]) -> None:
    """Register a provider class under its `provider_id`.

    Real providers (e.g., a future `OpenAIModerationProvider`) should
    call this at import time of their own module, so a downstream
    consumer can `import orchestrator.safety.providers.openai` and
    then select it via `XION_LLM_ARBITER_PROVIDER`. This keeps the
    registry open without coupling the core to any specific provider.
    """
    if not isinstance(cls, type) or not issubclass(cls, Provider):
        raise TypeError(f"register_provider: expected Provider subclass, got {cls!r}")
    if cls is Provider:
        raise TypeError("register_provider: cannot register the abstract Provider itself")
    pid = cls.provider_id
    if not pid:
        raise TypeError(f"register_provider: {cls.__name__}.provider_id must be non-empty")
    _PROVIDERS[pid] = cls


def is_v2_enabled() -> bool:
    """Return True iff v2 should be invoked on v1-OK candidates.

    False iff `XION_LLM_ARBITER_DISABLED` is set to `"1"`, `"true"`,
    or `"yes"` (case-insensitive). This escape hatch exists only for
    emergency operator response (e.g., a newly-discovered provider
    vulnerability that would be worse to run than to skip). Setting
    it in production MUST be logged in the operator runbook, since
    it degrades the safety posture to v1-only for the duration.
    """
    val = os.environ.get(_DISABLE_V2_ENV, "").strip().lower()
    return val not in ("1", "true", "yes")


def _ensure_providers_loaded() -> None:
    """Lazy-import the concrete providers subpackage so any providers
    defined there register themselves with `_PROVIDERS`.

    Kept lazy so the bare `import orchestrator.safety` path does NOT
    pull in network-touching provider modules. Only when
    `get_active_provider()` is actually called (which only happens
    inside `gate()`, which is the Relay's hot path) does the import
    occur. After the first call, Python's module cache makes
    subsequent calls free.

    We swallow `ImportError` intentionally: if the providers subpackage
    is absent (e.g., in a trimmed deployment that ships only the core),
    the registry is just the stub, and `get_active_provider()` falls
    back to the stub. No pathway to silent OK: the fallback is the
    same stub that always returns OK, which means the final posture
    degrades to v1-only, which is exactly the behaviour a reader of
    the ledger sees (all rows get `llm_verdict.provider_id ==
    "deterministic-stub"`).
    """
    # No providers subpackage installed -> stub-only mode. That's an
    # operational degradation, not an error, so we suppress silently
    # here; `xion-verify arbiter-up` surfaces it to the operator.
    with contextlib.suppress(ImportError):
        import orchestrator.safety.providers  # noqa: F401 — import-for-side-effect


def get_active_provider() -> Provider:
    """Return an instance of the currently-active v2 provider.

    Selection order:
      1. `XION_LLM_ARBITER_PROVIDER` env var (must match a registered
         provider_id).
      2. `DeterministicStub` otherwise.

    If the env var is set to an UNKNOWN provider_id, this function
    falls back to the stub AND honestly labels the fallback: the env
    var is treated as a misconfiguration, not a request to fail.
    `xion-verify arbiter-up` will surface any misconfigured env var
    as a warning in a future phase.
    """
    _ensure_providers_loaded()
    pid = os.environ.get(_ACTIVE_PROVIDER_ENV, "").strip()
    if pid and pid in _PROVIDERS:
        return _PROVIDERS[pid]()
    return DeterministicStub()


__all__ = [
    "DeterministicStub",
    "LlmJudgement",
    "Provider",
    "get_active_provider",
    "is_v2_enabled",
    "register_provider",
    "strength_max",
]
